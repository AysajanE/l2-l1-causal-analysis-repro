#!/usr/bin/env python3
"""
Phase 11B: Demand Factor Adequacy & Timing (I2)
==============================================

Construct and evaluate alternative demand-factor controls to verify that the
confirmatory ITS / ECM results are robust to (i) the original three-component
``D*_lite`` factor, (ii) an expanded five-component ``D*_full`` factor, and
(iii) a lagged ``D*_lite`` control that mitigates same-day "bad control"
concerns.  Outputs feed Table I2 in the manuscript.

This script:
    * Merges the core analysis panel with demand-factor components
    * Automatically aligns factor orientation (positive correlation with CEX volume)
    * Augments the panel with sequencer outage controls (any_outage_t)
    * Computes PCA loadings and leave-one-out diagnostics for each factor
    * Estimates ECM specifications per factor variant with HAC standard errors
    * Records Engle–Granger residual ADF p-values and half-life diagnostics
    * Exports VIF checks, coefficient tables (CSV + LaTeX), and metadata

Outputs (under ``results/demand_factor/``):
    - d_star_variant_results.csv
    - d_star_variant_vif.csv
    - d_star_leave_one_out.csv
    - table_i2_demand_factor_variants.csv
    - table_i2_demand_factor_variants.tex
    - diagnostics.yaml (summary metadata)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import statsmodels.api as sm
from patsy import dmatrices
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tsa.stattools import adfuller


LONDON = pd.Timestamp("2021-08-05")
MERGE = pd.Timestamp("2022-09-15")
DENCUN = pd.Timestamp("2024-03-13")

# File locations
CORE_PANEL = Path("data/core_panel_v1/core_panel_v1.parquet")
MASTER_PANEL = Path("data/processed/master_panel/master_panel_v2_with_d_star_full.parquet")
OUTAGE_CSV = Path("data/external/l2_outages.csv")

OUT_DIR = Path("results/demand_factor")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _read_parquet_datesafe(path: Path) -> pd.DataFrame:
    """Robust parquet reader that coerces date-like columns to Timestamp."""
    table = pq.read_table(path)
    data = {}
    for name in table.column_names:
        col = table[name]
        if "date" in name.lower():
            data[name] = pd.to_datetime([str(x) for x in col.to_pylist()])
        else:
            try:
                data[name] = col.to_numpy()
            except NotImplementedError:
                data[name] = np.array(col.to_pylist())
    return pd.DataFrame(data)


def load_core_panel() -> pd.DataFrame:
    if not CORE_PANEL.exists():
        raise FileNotFoundError(f"Missing core panel at {CORE_PANEL}")
    df = _read_parquet_datesafe(CORE_PANEL)
    df = df[df["date"] >= LONDON].copy()
    df.sort_values("date", inplace=True)

    if "log_base_fee" not in df.columns and "base_fee_median_gwei" in df.columns:
        df["log_base_fee"] = np.log(df["base_fee_median_gwei"] + 1.0)

    df["is_weekend"] = df["is_weekend"].astype(int)
    df["is_month_end"] = df["is_month_end"].astype(int)
    return df


def load_master_panel() -> pd.DataFrame:
    if not MASTER_PANEL.exists():
        raise FileNotFoundError(f"Missing master panel at {MASTER_PANEL}")
    df = _read_parquet_datesafe(MASTER_PANEL)
    df = df[df["date"] >= LONDON].copy()
    df.sort_values("date", inplace=True)
    return df


def load_outages() -> pd.DataFrame:
    if not OUTAGE_CSV.exists():
        return pd.DataFrame({"date": [], "any_outage_t": []})
    outages = pd.read_csv(OUTAGE_CSV, parse_dates=["date"])
    outages["has_outage"] = (outages["hours_down"].fillna(0) > 0).astype(int)
    daily = (
        outages.groupby("date")["has_outage"]
        .max()
        .reset_index()
        .rename(columns={"has_outage": "any_outage_t"})
    )
    return daily


def orient_factor(series: pd.Series, reference: pd.Series) -> pd.Series:
    """Ensure the PCA factor has positive correlation with reference proxy."""
    aligned = series.copy()
    corr = np.corrcoef(aligned.dropna(), reference.loc[aligned.index].dropna())[0, 1]
    if np.isnan(corr):
        return aligned
    if corr < 0:
        aligned *= -1
    return aligned


def compute_pca_scores(df: pd.DataFrame, columns: List[str], ref_series: pd.Series) -> Dict[str, np.ndarray]:
    """Run PCA on specified columns and return scores/loadings."""
    complete = df[columns].dropna()
    scaler = StandardScaler()
    scaled = scaler.fit_transform(complete)
    pca = PCA(n_components=1)
    scores = pca.fit_transform(scaled).ravel()
    loadings = pca.components_[0]

    # Align orientation with reference proxy
    aligned_scores = orient_factor(pd.Series(scores, index=complete.index), ref_series).values
    return {
        "scores": aligned_scores,
        "indices": complete.index,
        "loadings": loadings if np.corrcoef(scores, aligned_scores)[0, 1] > 0 else -loadings,
        "explained_variance": pca.explained_variance_ratio_[0],
    }


def leave_one_out_loadings(df: pd.DataFrame, columns: List[str], ref: pd.Series, variant: str) -> pd.DataFrame:
    """Compute PCA loadings with each component removed."""
    records = []
    # Baseline
    baseline = compute_pca_scores(df, columns, ref)
    base_df = pd.DataFrame({
        "variant": variant,
        "dropped_component": "None",
        "component": columns,
        "loading": baseline["loadings"],
        "explained_variance": baseline["explained_variance"],
    })
    records.append(base_df)

    # Leave-one-out
    for col in columns:
        remaining = [c for c in columns if c != col]
        if not remaining:
            continue
        pca_result = compute_pca_scores(df, remaining, ref)
        row = pd.DataFrame({
            "variant": variant,
            "dropped_component": col,
            "component": remaining,
            "loading": pca_result["loadings"],
            "explained_variance": pca_result["explained_variance"],
        })
        records.append(row)

    return pd.concat(records, ignore_index=True)


@dataclass
class VariantSpec:
    name: str
    label: str
    dstar_level: str
    dstar_diff: str


def estimate_ecm(df: pd.DataFrame, spec: VariantSpec) -> Dict[str, float]:
    """Estimate ECM for a given D* variant and return diagnostics."""
    cols_needed = [
        "log_base_fee",
        "A_t_clean",
        spec.dstar_level,
        "is_weekend",
        "is_month_end",
        "regime_post_merge",
        "regime_post_dencun",
        "any_outage_t",
    ]
    data = df.dropna(subset=cols_needed).copy()

    # Long-run regression
    formula_lr = (
        f"log_base_fee ~ A_t_clean + {spec.dstar_level} + is_weekend + "
        "is_month_end + regime_post_merge + regime_post_dencun + any_outage_t"
    )
    y_lr, X_lr = dmatrices(formula_lr, data=data, return_type="dataframe")
    lr_model = OLS(y_lr, X_lr).fit()
    resid = lr_model.resid.squeeze()

    # Engle--Granger residual ADF
    try:
        eg_stat, eg_p, *_ = adfuller(resid, regression="c", autolag="AIC")
    except Exception:
        eg_stat, eg_p = np.nan, np.nan

    data["ECT_lag1"] = resid.shift(1)
    data["d_log_base_fee"] = data["log_base_fee"].diff()
    data["d_A_t_clean"] = data["A_t_clean"].diff()
    data["d_log_base_fee_lag1"] = data["d_log_base_fee"].shift(1)
    data["d_any_outage_t"] = data["any_outage_t"].diff().fillna(0)

    if spec.dstar_diff not in data.columns:
        raise KeyError(f"Missing differenced column {spec.dstar_diff} for variant {spec.name}")

    cols_ecm = [
        "d_log_base_fee",
        "ECT_lag1",
        "d_A_t_clean",
        spec.dstar_diff,
        "d_log_base_fee_lag1",
        "is_weekend",
        "is_month_end",
        "d_any_outage_t",
    ]
    ecm_data = data.dropna(subset=cols_ecm)

    if len(ecm_data) < 50:
        raise ValueError(f"Insufficient observations for ECM variant {spec.name}")

    y_ecm = ecm_data["d_log_base_fee"]
    X_cols = ["ECT_lag1", "d_A_t_clean", spec.dstar_diff, "d_log_base_fee_lag1", "is_weekend", "is_month_end", "d_any_outage_t"]
    X_ecm = sm.add_constant(ecm_data[X_cols])
    ecm_model = sm.OLS(y_ecm, X_ecm)
    bw = min(7, max(1, int(4 * (len(ecm_data) / 100) ** (2 / 9))))
    ecm_res = ecm_model.fit(
        cov_type="HAC",
        cov_kwds={"maxlags": bw, "kernel": "bartlett", "use_correction": True},
    )

    psi = ecm_res.params["d_A_t_clean"]
    psi_se = ecm_res.bse["d_A_t_clean"]
    psi_p = ecm_res.pvalues["d_A_t_clean"]
    phi = ecm_res.params["ECT_lag1"]
    phi_se = ecm_res.bse["ECT_lag1"]
    phi_p = ecm_res.pvalues["ECT_lag1"]

    # Half-life calculation
    half_life = np.nan
    try:
        if (1 + phi) > 0:
            half_life = np.log(0.5) / np.log(1 + phi)
    except Exception:
        half_life = np.nan

    # VIF diagnostics for long-run regression (exclude intercept)
    X_lr_no_const = X_lr.drop(columns=["Intercept"]) if "Intercept" in X_lr.columns else X_lr
    vif_records = []
    for idx, col in enumerate(X_lr_no_const.columns):
        vif_val = variance_inflation_factor(X_lr_no_const.values, idx)
        vif_records.append({"variant": spec.name, "variable": col, "vif": float(vif_val)})

    # Residual diagnostics
    try:
        lb = acorr_ljungbox(ecm_res.resid, lags=[10], return_df=True)
        lb_p = float(lb["lb_pvalue"].iloc[0])
    except Exception:
        lb_p = np.nan

    results = {
        "variant": spec.name,
        "label": spec.label,
        "n_long_run": int(len(data)),
        "n_ecm": int(len(ecm_data)),
        "bw": int(bw),
        "psi": float(psi),
        "psi_se": float(psi_se),
        "psi_p": float(psi_p),
        "phi": float(phi),
        "phi_se": float(phi_se),
        "phi_p": float(phi_p),
        "half_life_days": float(half_life),
        "eg_stat": float(eg_stat) if np.isfinite(eg_stat) else np.nan,
        "eg_p": float(eg_p) if np.isfinite(eg_p) else np.nan,
        "r_squared": float(ecm_res.rsquared),
        "adj_r_squared": float(ecm_res.rsquared_adj),
        "ljung_box_p_lag10": lb_p,
    }

    return results, pd.DataFrame(vif_records)


def main() -> None:
    core = load_core_panel()
    drop_cols = [
        "D_star",
        "D_star_original",
        "D_star_lite",
        "D_star_full",
        "eth_return_1d_log",
        "cex_volume_log",
        "trends_ethereum",
        "realized_volatility",
        "stablecoin_net_usd",
    ]
    core = core.drop(columns=[c for c in drop_cols if c in core.columns])
    master = load_master_panel()
    outages = load_outages()

    df = core.merge(master[["date", "D_star_lite", "D_star", "realized_volatility", "stablecoin_net_usd",
                            "eth_return_1d_log", "cex_volume_log", "trends_ethereum"]], on="date", how="left")

    # Stablecoin flows may be decimal -> convert to float
    if "stablecoin_net_usd" in df.columns:
        df["stablecoin_net_usd"] = pd.to_numeric(df["stablecoin_net_usd"], errors="coerce")

    # Align factor orientation
    df["D_star_full"] = orient_factor(df["D_star"], df["cex_volume_log"])
    df["D_star_lite_aligned"] = orient_factor(df["D_star_lite"], df["cex_volume_log"])

    df["D_star_lite_lag1"] = df["D_star_lite_aligned"].shift(1)
    df["D_star_full_diff"] = df["D_star_full"].diff()
    df["D_star_lite_diff"] = df["D_star_lite_aligned"].diff()
    df["D_star_lite_lag1_diff"] = df["D_star_lite_lag1"].diff()

    df = df.merge(outages, on="date", how="left")
    df["any_outage_t"] = df["any_outage_t"].fillna(0)

    variants = [
        VariantSpec("lite_same_day", "D★-lite (same-day)", "D_star_lite_aligned", "D_star_lite_diff"),
        VariantSpec("full_same_day", "D★-full (same-day)", "D_star_full", "D_star_full_diff"),
        VariantSpec("lite_lag1", "D★-lite (t-1)", "D_star_lite_lag1", "D_star_lite_lag1_diff"),
    ]

    results: List[Dict[str, float]] = []
    vif_frames: List[pd.DataFrame] = []

    for spec in variants:
        res, vif_df = estimate_ecm(df, spec)
        results.append(res)
        vif_frames.append(vif_df)

    results_df = pd.DataFrame(results)
    results_df.to_csv(OUT_DIR / "d_star_variant_results.csv", index=False)

    vif_df = pd.concat(vif_frames, ignore_index=True)
    vif_df.to_csv(OUT_DIR / "d_star_variant_vif.csv", index=False)

    # Leave-one-out loadings
    comp_lite = ["eth_return_1d_log", "cex_volume_log", "trends_ethereum"]
    comp_full = comp_lite + ["realized_volatility", "stablecoin_net_usd"]
    loo_lite = leave_one_out_loadings(df, comp_lite, df["cex_volume_log"], "D★-lite")
    loo_full = leave_one_out_loadings(df, comp_full, df["cex_volume_log"], "D★-full")
    loo_df = pd.concat([loo_lite, loo_full], ignore_index=True)
    loo_df.to_csv(OUT_DIR / "d_star_leave_one_out.csv", index=False)

    # Table I2 (CSV + LaTeX)
    table_cols = [
        "label",
        "psi",
        "psi_se",
        "psi_p",
        "phi",
        "phi_se",
        "phi_p",
        "half_life_days",
        "eg_p",
        "adj_r_squared",
        "n_ecm",
    ]
    table_df = results_df[["variant"] + table_cols].copy()
    table_df.rename(columns={
        "psi": "psi_coef",
        "psi_se": "psi_se",
        "psi_p": "psi_p",
        "phi": "phi_coef",
        "phi_se": "phi_se",
        "phi_p": "phi_p",
        "eg_p": "eg_pvalue",
        "adj_r_squared": "adj_r2",
        "n_ecm": "N",
    }, inplace=True)
    table_df.to_csv(OUT_DIR / "table_i2_demand_factor_variants.csv", index=False)

    lines = [
        "% Auto-generated: Demand Factor Timing Variants (I2)\n",
        "\\begin{table}[!htbp]\n",
        "\\centering\n",
        "\\small\n",
        "\\caption{Demand Factor Variants and Timing Diagnostics}\n",
        "\\label{tab:i2_demand_factor}\n",
        "\\begin{tabular}{lcccccc}\n",
        "\\toprule\n",
        "Demand factor & $\\psi$ (10pp) & SE & $p$-value & EG $p$ & Adj.~$R^2$ & $N$ \\\\\n",
        "\\midrule\n",
    ]

    for _, row in table_df.iterrows():
        label_tex = row['label'].replace("D★", "$D^{\\star}$")
        psi = row["psi_coef"]
        se = row["psi_se"]
        pval = row["psi_p"]
        eg_p = row["eg_pvalue"]
        adj_r2 = row["adj_r2"]
        n_obs = int(row["N"])
        psi_str = f"{psi:.3f}"
        se_str = f"({se:.3f})"
        p_str = f"{pval:.3f}"
        eg_str = f"{eg_p:.3f}" if np.isfinite(eg_p) else "N/A"
        adj_str = f"{adj_r2:.3f}"
        lines.append(f"{label_tex} & {psi_str} & {se_str} & {p_str} & {eg_str} & {adj_str} & {n_obs} \\\\\n")

    lines.extend([
        "\\bottomrule\n",
        "\\end{tabular}\n",
        "\\begin{minipage}{0.92\\textwidth}\n",
        "\\vspace{0.3em}\\footnotesize\\textit{Note:} $\\psi$ is the short-run semi-elasticity from the ECM (10pp increase in L2 adoption). All specifications include regime dummies, calendar effects, and an indicator for any sequencer outage. HAC (Bartlett) standard errors use the Andrews bandwidth capped at 7. Engle--Granger $p$-values test residual unit roots (rejecting implies cointegration).\\end{minipage}\n",
        "\\end{table}\n",
    ])
    (OUT_DIR / "table_i2_demand_factor_variants.tex").write_text("".join(lines))

    metadata = {
        "variants": results_df.to_dict(orient="records"),
        "vif_path": str((OUT_DIR / "d_star_variant_vif.csv").resolve()),
        "leave_one_out_path": str((OUT_DIR / "d_star_leave_one_out.csv").resolve()),
    }
    (OUT_DIR / "diagnostics.json").write_text(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
