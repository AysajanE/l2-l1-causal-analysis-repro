#!/usr/bin/env python3
"""
Local Projection IRFs for L2 Adoption → L1 Congestion
=====================================================

Implements Jordà (2005) local projections for horizons h=0..H (default H=56):
  Δ Y_{t+h} = α_h + β_h ΔA_t + Γ_h' Z_t + ε_{t+h}

Where Y is `log_base_fee` (main) or `u_t` (cross-equation check).

Controls Z_t include:
  - ΔD*_t (demand factor change)
  - regime indicators (levels at t)
  - calendar dummies (weekend, month-end at t)
  - targeted external-shock/event dummies when present (e.g., NFT mint, FTX, USDC depeg)

Inference:
  - HAC (Newey–West, Bartlett kernel) with horizon-aware bandwidth
  - Optional Moving-Block Bootstrap (MBB) percentiles for robustness
  - Delta-method CIs for cumulative semi-elasticities using HAC SE aggregation

Outputs:
  - results/irf/irf_summary*.csv (β_h, HAC CI, optional MBB CI)
  - results/irf/irf_h{h}*.csv (row per horizon)
  - results/irf/cumulative_effects*.csv (cum β up to H and semi-elasticities)
  - results/irf/table_c3_cumulative_effects*.tex (LaTeX table for manuscript)
  - results/irf/rebound_event_controls.csv (h=7 comparison with/without events)

Also computes Koyck long-run multiplier using existing ITSLevelsEstimator.

Author: Econometrics Lead (C3 implementation)
Date: 2025-10-21 (updated 2025-10-31: H=56, delta-CIs, event controls, utilization IRFs)
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Dict, Tuple, Optional, List

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.sandwich_covariance import cov_hac


PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Ensure repo root on path for `src` imports when running as script
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Project imports (after sys.path adjustment)
from src.utils.parquet_loader import load_parquet_with_date_handling
from src.utils.events import build_event_dummies_from_registry
from src.models.its_levels import ITSLevelsEstimator
from project_A_effects.visualization.utils.provenance import ProvenanceFooter
DATA_PATH = PROJECT_ROOT / "data" / "core_panel_v1" / "core_panel_v1.parquet"
RESULTS_DIR = PROJECT_ROOT / "results" / "irf"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare analysis frame with needed variables and differences."""
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)

    # Ensure required columns
    assert {"date", "A_t_clean", "log_base_fee", "D_star"}.issubset(df.columns), (
        "Missing required columns in panel"
    )

    # Differences
    df["d_log_base_fee"] = df["log_base_fee"].diff()
    df["d_A_t"] = df["A_t_clean"].diff()
    df["d_D_star"] = df["D_star"].diff()

    # Deterministic controls (levels)
    if "regime_post_merge" in df.columns:
        df["regime_merge"] = df["regime_post_merge"]
        df["regime_dencun"] = df.get("regime_post_dencun", 0)
    else:
        df["regime_merge"] = (df["date"] >= pd.Timestamp("2022-09-15")).astype(int)
        df["regime_dencun"] = (df["date"] >= pd.Timestamp("2024-03-13")).astype(int)

    if "is_weekend" not in df.columns:
        df["is_weekend"] = (df["date"].dt.dayofweek >= 5).astype(int)
    if "is_month_end" not in df.columns:
        df["is_month_end"] = df["date"].dt.is_month_end.astype(int)

    # Merge curated event dummies from YAML registry if available
    try:
        ev = build_event_dummies_from_registry(df["date"])  # returns ['date', 'any_airdrop_d0', ...]
        df = df.merge(ev, on="date", how="left")
    except Exception:
        pass

    return df


def horizon_regression(
    df: pd.DataFrame,
    h: int,
    hac_base_bw: Optional[int] = None,
    outcome: str = "log_base_fee",
    extra_controls: Optional[List[str]] = None,
) -> Dict:
    """Estimate Δ Y_{t+h} on ΔA_t + controls with HAC SEs.

    outcome: column name for level variable Y (e.g., 'log_base_fee' or 'u_t').
    extra_controls: optional list of additional control column names (levels at t).
    """
    # Build dependent variable at horizon h: Δ Y_{t+h} = Y_{t+h} - Y_{t+h-1}
    y = df[outcome].shift(-h) - df[outcome].shift(-h + 1)

    base_cols = [
        "d_A_t", "d_D_star", "regime_merge", "regime_dencun", "is_weekend", "is_month_end"
    ]
    # Keep only extra controls present in df
    if extra_controls:
        present = [c for c in extra_controls if c in df.columns]
    else:
        present = []

    frame = pd.DataFrame({
        "y_h": y,
        **{c: df[c] for c in base_cols},
        **{c: df[c] for c in present},
    }).dropna()

    Xcols = base_cols + present
    X = sm.add_constant(frame[Xcols])

    model = sm.OLS(frame["y_h"], X)
    ols_res = model.fit()

    # Horizon-aware HAC bandwidth
    n = len(frame)
    if hac_base_bw is None:
        hac_base_bw = int(4 * (n / 100) ** (2 / 9))
    bw = min(hac_base_bw + max(h, 1), n - 1)

    hac_res = model.fit(cov_type="HAC", cov_kwds={
        "kernel": "bartlett",
        "use_correction": True,
        "maxlags": bw,
    })

    beta = hac_res.params["d_A_t"]
    se = hac_res.bse["d_A_t"]
    ci_low, ci_high = hac_res.conf_int().loc["d_A_t"]

    return {
        "h": h,
        "n": n,
        "bandwidth": bw,
        "beta": beta,
        "se": se,
        "ci_low_hac": ci_low,
        "ci_high_hac": ci_high,
        "beta_ols": ols_res.params.get("d_A_t", np.nan),
        "r2": ols_res.rsquared,
        "bandwidth": bw,
        "controls": Xcols,
    }


def moving_block_bootstrap_irf(df: pd.DataFrame, h: int, B: int = 300, block_len: Optional[int] = None,
                               random_state: int = 42) -> Tuple[float, float]:
    """Compute MBB percentile CI for β_h via simple block resampling of rows.

    Returns (q2.5, q97.5).
    """
    rng = np.random.default_rng(random_state)
    n = len(df)
    if block_len is None:
        block_len = max(5, int(round(n ** (1 / 3))))  # Rule-of-thumb

    # Precompute dependent variable at horizon h
    y = df["log_base_fee"].shift(-h) - df["log_base_fee"].shift(-h + 1)
    base_frame = pd.DataFrame({
        "y_h": y,
        "d_A_t": df["d_A_t"],
        "d_D_star": df["d_D_star"],
        "regime_merge": df["regime_merge"],
        "regime_dencun": df["regime_dencun"],
        "is_weekend": df["is_weekend"],
        "is_month_end": df["is_month_end"],
    }).dropna()

    base_frame = base_frame.reset_index(drop=True)
    n_eff = len(base_frame)

    betas = np.empty(B)
    for b in range(B):
        # Draw blocks until reaching n_eff length
        indices = []
        while len(indices) < n_eff:
            start = rng.integers(0, n_eff - block_len + 1)
            block_idx = list(range(start, start + block_len))
            indices.extend(block_idx)
        indices = indices[:n_eff]

        sample = base_frame.iloc[indices].copy()
        Xb = sm.add_constant(sample[[
            "d_A_t", "d_D_star", "regime_merge", "regime_dencun", "is_weekend", "is_month_end"
        ]])
        yb = sample["y_h"]
        try:
            res_b = sm.OLS(yb, Xb).fit()
            betas[b] = res_b.params.get("d_A_t", np.nan)
        except Exception:
            betas[b] = np.nan

    betas = betas[~np.isnan(betas)]
    if len(betas) < max(30, int(0.5 * B)):
        # Fallback if too many failures
        return (np.nan, np.nan)

    q_low, q_high = np.percentile(betas, [2.5, 97.5])
    return (float(q_low), float(q_high))


def compute_irfs(
    df: pd.DataFrame,
    H: int = 56,
    with_mbb: bool = True,
    outcome: str = "log_base_fee",
    use_event_controls: bool = True,
) -> pd.DataFrame:
    """Compute IRFs across horizons and save per-h CSVs and summary.

    outcome: 'log_base_fee' (default) or 'u_t' for cross-equation LP.
    use_event_controls: include targeted event dummies if present in panel.
    """
    df_prep = prepare_frame(df)

    # Detect optional event controls
    candidate_events = [
        "shock_china_ban",
        "shock_otherside_mint",
        "shock_terra_luna",
        "shock_ftx_collapse",
        "shock_usdc_depeg",
        "any_airdrop_d0",
        "any_outage_d0",
        "base_onchain_summer_d0",
    ]
    extra = [c for c in candidate_events if use_event_controls and c in df_prep.columns]

    # HAC base bandwidth from h=0 frame length
    tmp = horizon_regression(df_prep, h=0, outcome=outcome, extra_controls=extra)
    hac_base = tmp["bandwidth"]

    rows = []
    for h in range(0, H + 1):
        res = horizon_regression(
            df_prep, h=h, hac_base_bw=hac_base, outcome=outcome, extra_controls=extra
        )

        # Optional MBB CI (per-h)
        if with_mbb and outcome == "log_base_fee":
            mbb_lo, mbb_hi = moving_block_bootstrap_irf(df_prep, h=h)
            res["ci_low_mbb"] = mbb_lo
            res["ci_high_mbb"] = mbb_hi

        rows.append(res)

        # Save per-h CSV
        suffix = "" if outcome == "log_base_fee" else f"_{outcome}"
        pd.DataFrame([res]).to_csv(RESULTS_DIR / f"irf_h{h}{suffix}.csv", index=False)

    summary = pd.DataFrame(rows)
    suffix = "" if outcome == "log_base_fee" else f"_{outcome}"
    summary.to_csv(RESULTS_DIR / f"irf_summary{suffix}.csv", index=False)
    return summary


def compute_cumulative(
    summary: pd.DataFrame,
    horizons: Tuple[int, ...] = (1, 7, 14, 28, 56),
    outcome: str = "log_base_fee",
) -> pd.DataFrame:
    """Compute cumulative sum of β_h and map to semi-elasticity (log outcome) or levels (u_t).

    Also compute delta-method CIs using aggregated HAC SEs (ignoring cross-horizon covariance)
    and fall back to per-h bound summation if MBB not available.
    """
    out_rows = []
    for H in horizons:
        sub = summary[summary["h"] <= H]
        beta_cum = sub["beta"].sum()

        if outcome == "log_base_fee":
            # Semi-elasticity mapping for 10pp ΔA
            semi = (np.exp(0.10 * beta_cum) - 1) * 100.0
            # Delta-method on β_cum (approximate): Var ≈ ∑ Var_h (ignoring covariances)
            # Aggregate HAC variances across horizons (approximate; ignores covariances)
            se_col = "se_hac" if "se_hac" in sub.columns else "se"
            var_cum = np.nansum(np.square(sub[se_col]))
            se_cum = np.sqrt(var_cum)
            # 95% CI on β_cum, then map via exp
            beta_low = beta_cum - 1.96 * se_cum
            beta_high = beta_cum + 1.96 * se_cum
            semi_low_dm = (np.exp(0.10 * beta_low) - 1) * 100.0
            semi_high_dm = (np.exp(0.10 * beta_high) - 1) * 100.0

            # Conservative bound-sum (as before) for reference
            if {"ci_low_mbb", "ci_high_mbb"}.issubset(sub.columns) and not sub["ci_low_mbb"].isna().any():
                beta_cum_low = sub["ci_low_mbb"].sum()
                beta_cum_high = sub["ci_high_mbb"].sum()
            else:
                beta_cum_low = sub["ci_low_hac"].sum()
                beta_cum_high = sub["ci_high_hac"].sum()
            semi_low_cons = (np.exp(0.10 * beta_cum_low) - 1) * 100.0
            semi_high_cons = (np.exp(0.10 * beta_cum_high) - 1) * 100.0

            out_rows.append({
                "H": H,
                "beta_cum": beta_cum,
                "semi_elasticity_10pp": semi,
                "semi_ci_low_delta": semi_low_dm,
                "semi_ci_high_delta": semi_high_dm,
                "semi_ci_low_cons": semi_low_cons,
                "semi_ci_high_cons": semi_high_cons,
            })
        else:
            # For u_t (level), cumulative effect on level at H for ΔA=0.10 is 0.10 * ∑β_h
            level_change = 0.10 * beta_cum
            se_col = "se_hac" if "se_hac" in sub.columns else "se"
            var_cum = np.nansum(np.square(sub[se_col]))
            se_cum = np.sqrt(var_cum)
            level_se = 0.10 * se_cum
            out_rows.append({
                "H": H,
                "beta_cum": beta_cum,
                "level_change_10pp": level_change,
                "level_ci_low_delta": level_change - 1.96 * level_se,
                "level_ci_high_delta": level_change + 1.96 * level_se,
            })

    cum = pd.DataFrame(out_rows)
    suffix = "" if outcome == "log_base_fee" else f"_{outcome}"
    cum.to_csv(RESULTS_DIR / f"cumulative_effects{suffix}.csv", index=False)
    return cum


def render_cumulative_table(cum: pd.DataFrame, output_tex: Path) -> None:
    """Render LaTeX table for cumulative effects with provenance footer."""
    df = cum.copy()
    df["H (days)"] = df["H"]
    df["Cum. Semi-Elasticity (10pp)"] = df["semi_elasticity_10pp"].map(lambda x: f"{x:.2f}\\%")
    # Prefer delta-method bands; fall back to conservative if missing
    lo = df.get("semi_ci_low_delta", df.get("semi_ci_low_cons"))
    hi = df.get("semi_ci_high_delta", df.get("semi_ci_high_cons"))
    df["95% CI"] = [f"[{l:.2f}\\%, {h:.2f}\\%]" for l, h in zip(lo, hi)]
    table_df = df[["H (days)", "Cum. Semi-Elasticity (10pp)", "95% CI"]]

    # Manually compose LaTeX table (align with working IV table style)
    lines = [
        r"\begin{center}",
        r"\begin{tabular}{lcc}",
        r"\hline",
        "H (days) & Cum. Semi-Elasticity (10pp) & 95% CI \\\\",
        r"\hline",
    ]

    for _, r in table_df.iterrows():
        lines.append(f"{int(r['H (days)'])} & {r['Cum. Semi-Elasticity (10pp)']} & {r['95% CI']} \\\\"
        )

    lines.extend([
        r"\hline",
        r"\end{tabular}",
        r"\end{center}",
    ])

    latex = "\n".join(lines)

    output_tex.parent.mkdir(parents=True, exist_ok=True)
    with open(output_tex, 'w') as f:
        f.write(latex)


def render_cumulative_table_full(cum: pd.DataFrame, output_tex: Path) -> None:
    """Render LaTeX table for cumulative effects with caption and label (robust formatting)."""
    df = cum.copy()
    df["H (days)"] = df["H"]
    df["Cum. Semi-Elasticity (10pp)"] = df["semi_elasticity_10pp"].map(lambda x: f"{x:.2f}\\%")
    # Prefer delta-method bands; fall back to conservative if missing
    lo = df.get("semi_ci_low_delta", df.get("semi_ci_low_cons"))
    hi = df.get("semi_ci_high_delta", df.get("semi_ci_high_cons"))
    # Use parentheses to avoid bracket optional-argument parsing
    df["95% CI"] = [f"({l:.2f}\\%, {h:.2f}\\%)" for l, h in zip(lo, hi)]
    table_df = df[["H (days)", "Cum. Semi-Elasticity (10pp)", "95% CI"]]

    lines = []
    lines.append("% Auto-generated: C3 cumulative effects table\n")
    lines.append("\\begin{table}[!htbp]\n")
    lines.append("\\centering\\small\n")
    lines.append("\\caption{Cumulative Effects from Local Projections (10pp Step)}\n")
    lines.append("\\label{tab:c3_cumulative_irf}\n")
    lines.append("\\begin{tabular}{lcc}\n")
    lines.append("\\toprule\n")
    lines.append("H (days) & Cum. Semi-Elasticity (10pp) & 95\\% CI \\\\ \n")
    lines.append("\\midrule\n")
    for _, r in table_df.iterrows():
        lines.append(f"{int(r['H (days)'])} & {r['Cum. Semi-Elasticity (10pp)']} & {r['95% CI']} \\\\ \n")
    lines.append("\\bottomrule\n")
    lines.append("\\end{tabular}\n")
    lines.append("\\end{table}\n")

    output_tex.parent.mkdir(parents=True, exist_ok=True)
    with open(output_tex, 'w') as f:
        f.write("".join(lines))


def compute_koyck_long_run(df: pd.DataFrame) -> Dict:
    """Use existing ITSLevelsEstimator to compute Koyck long-run multiplier."""
    est = ITSLevelsEstimator(data=df, outcome='log_base_fee', treatment='A_t_clean')
    # Use baseline Koyck (no time trend) to match manuscript reporting
    res = est.estimate_koyck_lag()
    return {
        "rho": res.get("rho"),
        "short_run": res.get("short_run_effect"),
        "long_run": res.get("long_run_effect"),
        "long_run_semi": res.get("long_run_semi_elasticity"),
        "n": res.get("n_obs"),
    }


def rebound_event_controls_test(df: pd.DataFrame) -> pd.DataFrame:
    """Compare h=7 LP with and without targeted event controls and test joint significance.

    Returns a one-row dataframe with β_7, SE, and joint Wald test p-value for event controls.
    """
    df_prep = prepare_frame(df)
    candidate_events = [
        "shock_china_ban",
        "shock_otherside_mint",
        "shock_terra_luna",
        "shock_ftx_collapse",
        "shock_usdc_depeg",
        "any_airdrop_d0",
        "any_ecosystem_event_d0",
    ]
    extra = [c for c in candidate_events if c in df_prep.columns]

    # No-event-controls model
    res_no = horizon_regression(df_prep, h=7, outcome="log_base_fee")

    # With-event-controls model
    res_ev = horizon_regression(df_prep, h=7, outcome="log_base_fee", extra_controls=extra)

    # Build robust Wald test for joint significance of event controls
    # Using OLS fit with HAC covariance to compute W = R b, Var = R V R'
    # Refit OLS to get param vector and robust cov
    # Construct frame consistent with horizon_regression internals
    y = df_prep["log_base_fee"].shift(-7) - df_prep["log_base_fee"].shift(-6)
    base_cols = [
        "d_A_t", "d_D_star", "regime_merge", "regime_dencun", "is_weekend", "is_month_end"
    ]
    Xcols = base_cols + extra
    frame = pd.DataFrame({
        "y_h": y,
        **{c: df_prep[c] for c in Xcols},
    }).dropna()
    X = sm.add_constant(frame[Xcols])
    ols = sm.OLS(frame["y_h"], X).fit()
    # HAC covariance with the same bandwidth as res_ev
    bw = int(res_ev.get("bandwidth", max(5, int(round(len(frame) ** (1/3))))))
    hac = ols.get_robustcov_results(cov_type="HAC", maxlags=bw, use_correction=True)
    b = np.asarray(hac.params)
    V = np.asarray(hac.cov_params())
    names = list(X.columns)

    # Build R matrix to pick event control coefficients
    ev_idx = [i for i, name in enumerate(names) if name in extra]
    if len(ev_idx) == 0:
        pval = np.nan
        wald_stat = np.nan
        df_dof = 0
    else:
        R = np.zeros((len(ev_idx), len(b)))
        for row_i, col_j in enumerate(ev_idx):
            R[row_i, col_j] = 1.0
        diff = R @ b  # R b - 0
        RVRT = R @ V @ R.T
        # Pseudo-inverse in case of singularity
        try:
            from scipy.stats import chi2
            inv = np.linalg.pinv(RVRT)
            wald_stat = float(diff.T @ inv @ diff)
            df_dof = len(ev_idx)
            pval = float(1.0 - chi2.cdf(wald_stat, df_dof))
        except Exception:
            wald_stat, pval, df_dof = np.nan, np.nan, len(ev_idx)

    out = pd.DataFrame([
        {
            "h": 7,
            "beta_no_events": res_no["beta"],
            "se_no_events": res_no.get("se_hac", res_no.get("se")),
            "beta_with_events": res_ev["beta"],
            "se_with_events": res_ev.get("se_hac", res_ev.get("se")),
            "wald_chi2": wald_stat,
            "wald_df": df_dof,
            "wald_p_value": pval,
            "n": res_ev["n"],
            "controls_included": ",".join(res_ev.get("controls", [])),
        }
    ])
    out.to_csv(RESULTS_DIR / "rebound_event_controls.csv", index=False)
    return out


def main():
    print("=" * 70)
    print("Local Projection IRFs (C3) - Dynamics Reconciliation")
    print("=" * 70)
    print(f"Loading panel: {DATA_PATH}")
    df = load_parquet_with_date_handling(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])

    # Compute IRFs (log base fee)
    print("\nComputing horizon-by-horizon IRFs (h=0..56) with HAC + MBB + event controls...")
    summary = compute_irfs(df, H=56, with_mbb=True, outcome="log_base_fee", use_event_controls=True)
    print(f"Saved: {RESULTS_DIR / 'irf_summary.csv'}")

    # Compute cumulative effects and render table (include H=56, delta-method CIs)
    cum = compute_cumulative(summary, horizons=(1, 7, 14, 28, 56), outcome="log_base_fee")
    output_tex = RESULTS_DIR / "table_c3_cumulative_effects.tex"
    render_cumulative_table_full(cum, output_tex)
    print(f"Saved cumulative table: {output_tex}")

    # Koyck multiplier
    print("\nEstimating Koyck long-run multiplier...")
    koyck = compute_koyck_long_run(df)
    pd.DataFrame([koyck]).to_csv(RESULTS_DIR / "koyck_long_run.csv", index=False)
    print("Koyck results:")
    for k, v in koyck.items():
        print(f"  {k}: {v}")

    # Robustness: Exclude ±7-day windows around major upgrades and recompute IRFs
    print("\nRobustness: Excluding ±7-day windows around London/Merge/Dencun...")
    excl_df = df.copy()
    windows = [
        (pd.Timestamp('2021-08-05') - pd.Timedelta(days=7), pd.Timestamp('2021-08-05') + pd.Timedelta(days=7)),
        (pd.Timestamp('2022-09-15') - pd.Timedelta(days=7), pd.Timestamp('2022-09-15') + pd.Timedelta(days=7)),
        (pd.Timestamp('2024-03-13') - pd.Timedelta(days=7), pd.Timestamp('2024-03-13') + pd.Timedelta(days=7)),
    ]
    for (start, end) in windows:
        excl_df = excl_df[(excl_df['date'] < start) | (excl_df['date'] > end)]
    summary_ex = compute_irfs(excl_df, H=56, with_mbb=True, outcome="log_base_fee", use_event_controls=True)
    cum_ex = compute_cumulative(summary_ex, horizons=(1, 7, 14, 28, 56), outcome="log_base_fee")
    summary_ex.to_csv(RESULTS_DIR / 'irf_summary_excl_upgrades.csv', index=False)
    cum_ex.to_csv(RESULTS_DIR / 'cumulative_effects_excl_upgrades.csv', index=False)
    render_cumulative_table_full(cum_ex, RESULTS_DIR / 'table_c3_cumulative_effects_excl_upgrades.tex')
    print("Saved robustness IRF summaries and cumulative table (excl. upgrades).")

    # Rebound-day test with targeted event controls (h=7)
    print("\nTesting rebound coincidence with major events (h=7)...")
    _ = rebound_event_controls_test(df)
    print(f"Saved: {RESULTS_DIR / 'rebound_event_controls.csv'}")

    # Cross-equation check: utilization IRFs (no MBB to save time)
    print("\nComputing utilization IRFs for cross-equation consistency (h=0..56)...")
    util_summary = compute_irfs(df, H=56, with_mbb=False, outcome="u_t", use_event_controls=True)
    util_cum = compute_cumulative(util_summary, horizons=(1, 7, 14, 28, 56), outcome="u_t")
    util_summary.to_csv(RESULTS_DIR / 'irf_summary_u_t.csv', index=False)
    util_cum.to_csv(RESULTS_DIR / 'cumulative_effects_u_t.csv', index=False)

    # Render utilization cumulative table (pp change in u_t for 10pp ΔA)
    # Compose LaTeX table manually
    df_ut = util_cum.copy()
    lines = []
    lines.append("% Auto-generated: C3 utilization cumulative effects table\n")
    lines.append("\\begin{table}[!htbp]\\centering\\small\n")
    lines.append("\\caption{Cumulative Effects on Utilization from Local Projections (10pp Step)}\\label{tab:c3_cumulative_irf_util}\n")
    lines.append("\\begin{tabular}{lcc}\\toprule\n")
    lines.append("H (days) & Cum. $\\Delta u$ (pp for 10pp $\\Delta A$) & 95\\% CI \\\\ \n")
    lines.append("\\midrule\n")
    for _, r in df_ut.iterrows():
        Hh = int(r["H"])
        est = 100 * r["level_change_10pp"]  # convert to percentage points
        lo = 100 * r["level_ci_low_delta"]
        hi = 100 * r["level_ci_high_delta"]
        lines.append(f"{Hh} & {est:.3f} & ({lo:.3f}, {hi:.3f}) \\\\ \n")
    lines.append("\\bottomrule\\end{tabular}\n")
    lines.append("\\end{table}\n")
    with open(RESULTS_DIR / 'table_c3_cumulative_irf_utilization.tex', 'w') as f:
        f.write("".join(lines))
    print("Saved utilization cumulative table.")


if __name__ == "__main__":
    main()
