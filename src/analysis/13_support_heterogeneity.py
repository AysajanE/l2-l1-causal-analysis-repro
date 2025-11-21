#!/usr/bin/env python3
"""
Positivity Limits & Regime Heterogeneity Analysis (I1)
=====================================================

Implements Revision Item I1:
  * Diagnose treatment support limitations post-Dencun
  * Estimate piecewise-linear (knot=0.80) response of log base fees to L2 adoption
  * Compute Minimum Detectable Effects (MDEs) using effective sample size adjustments
  * Produce partial-residual visualization with LOESS fits by regime

Outputs
-------
  - results/positivity/table_i1_spline.csv / .tex
  - results/positivity/table_i1_mde.csv / .tex
  - figures/positivity/partial_residual_support.pdf
  - figures/positivity/partial_residual_support.png

Notes
-----
  - Uses daily core panel (post-London sample)
  - Controls match confirmatory ITS levels specification (D*, regime, calendar)
  - HAC standard errors with Bartlett kernel, maxlags chosen by regime sample length
  - MDE uses (z_{0.975} + z_{0.80}) ≈ 2.80 multiplier on HAC SE (two-sided α=0.05, power=0.80)
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.nonparametric.smoothers_lowess import lowess

import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from project_A_effects.visualization.utils.provenance import ProvenanceFooter  # noqa: E402
from visualization.utils.theme import (  # noqa: E402
    set_publication_theme,
    get_figure_size,
    save_figure,
    REGIME_COLORS,
)
from src.utils.parquet_loader import load_parquet_with_date_handling  # noqa: E402


DATA_PATH = PROJECT_ROOT / "data" / "core_panel_v1" / "core_panel_v1.parquet"
RESULTS_DIR = PROJECT_ROOT / "results" / "positivity"
FIG_DIR = PROJECT_ROOT / "figures" / "positivity"

KNOT = 0.80
ALPHA_Z = 1.96  # two-sided 5% critical value
POWER_Z = 0.84  # 80% power
MDE_MULTIPLIER = ALPHA_Z + POWER_Z

DENCUN = pd.Timestamp("2024-03-13")
MERGE = pd.Timestamp("2022-09-15")
LONDON = pd.Timestamp("2021-08-05")


def ensure_dirs() -> None:
    """Create output directories if they do not exist."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)


def prepare_frame() -> pd.DataFrame:
    """Load and prepare analysis frame."""
    df = load_parquet_with_date_handling(DATA_PATH)
    df = df[df["date"] >= LONDON].sort_values("date").reset_index(drop=True)

    # Ensure numeric columns
    for col in ["log_base_fee", "A_t_clean", "D_star"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["regime_merge"] = (df["date"] >= MERGE).astype(int)
    df["regime_dencun"] = (df["date"] >= DENCUN).astype(int)
    if "is_weekend" not in df:
        df["is_weekend"] = (df["date"].dt.dayofweek >= 5).astype(int)
    if "is_month_end" not in df:
        df["is_month_end"] = df["date"].dt.is_month_end.astype(int)

    df["regime_label"] = np.where(
        df["date"] < DENCUN,
        "Pre-Dencun",
        "Post-Dencun",
    )

    df["A_hinge"] = np.clip(df["A_t_clean"] - KNOT, 0, None)

    return df.dropna(subset=["log_base_fee", "A_t_clean", "D_star"])


def _select_controls(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build design matrix with intercept and controls present with variation.
    Drops columns that are constant to avoid singular matrices.
    """
    controls = ["D_star", "regime_merge", "regime_dencun", "is_weekend", "is_month_end"]
    X = df[["A_t_clean"]].copy()
    for col in controls:
        if col in df.columns and df[col].nunique(dropna=False) > 1:
            X[col] = df[col]
    X = sm.add_constant(X, has_constant="add")
    return X


def fit_piecewise_model(df: pd.DataFrame) -> Tuple[sm.OLS, sm.regression.linear_model.RegressionResultsWrapper]:
    """Fit spline model with hinge at KNOT for entire sample."""
    X = _select_controls(df)
    X["A_hinge"] = df["A_hinge"]
    model = sm.OLS(df["log_base_fee"], X)

    n = len(df)
    maxlags = min(21, max(1, int(round(n ** (1 / 4)))))  # smaller for shorter samples
    res = model.fit(
        cov_type="HAC",
        cov_kwds={"kernel": "bartlett", "use_correction": True, "maxlags": maxlags},
    )
    return model, res


def summarize_piecewise(res: sm.regression.linear_model.RegressionResultsWrapper) -> pd.DataFrame:
    """Summarize slopes for <=KNOT and >KNOT regions with 95% CIs and semi-elasticities."""
    beta_low = res.params["A_t_clean"]
    beta_low_se = res.bse["A_t_clean"]

    beta_delta = res.params.get("A_hinge", 0.0)
    var = res.cov_params()
    cov = var.loc["A_t_clean", "A_hinge"] if "A_hinge" in var.index else 0.0
    var_delta = var.loc["A_hinge", "A_hinge"] if "A_hinge" in var.index else 0.0

    beta_high = beta_low + beta_delta
    beta_high_se = math.sqrt(beta_low_se ** 2 + var_delta + 2 * cov)

    rows = []
    for label, beta, se in [
        (f"$A_t \\leq {KNOT:.2f}$", beta_low, beta_low_se),
        (f"$A_t > {KNOT:.2f}$", beta_high, beta_high_se),
    ]:
        ci_low = beta - 1.96 * se
        ci_high = beta + 1.96 * se
        semi = (np.exp(0.10 * beta) - 1) * 100
        semi_low = (np.exp(0.10 * ci_low) - 1) * 100
        semi_high = (np.exp(0.10 * ci_high) - 1) * 100
        rows.append(
            {
                "Regime Support": label,
                r"$\hat{\beta}$": beta,
                "SE (HAC)": se,
                "95% CI": f"[{ci_low:.3f}, {ci_high:.3f}]",
                "Semi-elasticity (10pp)": semi,
                "Semi-elasticity CI": f"[{semi_low:.2f}\\%, {semi_high:.2f}\\%]",
            }
        )

    df = pd.DataFrame(rows)
    df = df.rename(columns={"95% CI": "95\\% CI"})
    return df


def effective_sample_size(series: pd.Series, max_lag: int = 14) -> float:
    """Compute effective sample size accounting for autocorrelation."""
    series = series - series.mean()
    N = series.shape[0]
    if N == 0:
        return np.nan
    denom = 1.0
    for h in range(1, min(max_lag, N - 1) + 1):
        rho = series.autocorr(lag=h)
        if np.isnan(rho):
            continue
        denom += 2 * rho * (1 - h / N)
    if denom <= 0:
        return float(N)
    return N / denom


def compute_mde(df: pd.DataFrame) -> pd.DataFrame:
    """Compute MDE table by regime with HAC SEs."""
    rows: Dict[str, Dict[str, float]] = {}
    for regime, frame in df.groupby("regime_label"):
        frame = frame.copy()
        X = _select_controls(frame)
        model = sm.OLS(frame["log_base_fee"], X)

        n = len(frame)
        if n < 30:
            continue
        maxlags = min(14, max(1, int(round(n ** (1 / 4)))))
        res = model.fit(
            cov_type="HAC",
            cov_kwds={"kernel": "bartlett", "use_correction": True, "maxlags": maxlags},
        )

        se = res.bse["A_t_clean"]
        mde_beta = MDE_MULTIPLIER * se
        mde_semi = (np.exp(0.10 * mde_beta) - 1) * 100

        n_eff = effective_sample_size(res.resid, max_lag=3)

        rows[regime] = {
            "Regime": regime,
            "N": n,
            "Std(A_t)": frame["A_t_clean"].std(),
            "N_eff": n_eff,
            "HAC SE": se,
            "MDE (beta units)": mde_beta,
            "MDE (10pp \\%)": mde_semi,
            "Max Adoption Range": f"[{frame['A_t_clean'].min():.3f}, {frame['A_t_clean'].max():.3f}]",
        }

    out = pd.DataFrame.from_dict(rows, orient="index").reset_index(drop=True)
    out = out[[
        "Regime",
        "N",
        "N_eff",
        "Std(A_t)",
        "Max Adoption Range",
        "HAC SE",
        "MDE (beta units)",
        "MDE (10pp \\%)",
    ]]
    return out


def partial_residual_plot(df: pd.DataFrame, res: sm.regression.linear_model.RegressionResultsWrapper) -> None:
    """Create partial residual plot with LOESS smoothing by regime."""
    import matplotlib.pyplot as plt

    # Apply publication theme so fonts and styling match other Management Science figures
    set_publication_theme()

    X = _select_controls(df)
    resid = res.resid
    beta = res.params["A_t_clean"]

    partial = resid + beta * df["A_t_clean"]

    fig, ax = plt.subplots(figsize=get_figure_size("single"))

    regime_colors = {
        "Pre-Dencun": REGIME_COLORS.get("merge_dencun", "#1f77b4"),
        "Post-Dencun": REGIME_COLORS.get("post_dencun", "#d62728"),
    }

    for regime in ["Pre-Dencun", "Post-Dencun"]:
        color = regime_colors[regime]
        mask = df["regime_label"] == regime
        ax.scatter(
            df.loc[mask, "A_t_clean"],
            partial.loc[mask],
            alpha=0.35,
            s=18,
            label=f"{regime} ({mask.sum()} days)",
            color=color,
            edgecolor="none",
        )
        if mask.sum() > 20:
            smoothed = lowess(
                partial.loc[mask],
                df.loc[mask, "A_t_clean"],
                frac=0.25,
                return_sorted=True,
            )
            ax.plot(smoothed[:, 0], smoothed[:, 1], color=color, linewidth=2)

    ax.axvline(KNOT, color="gray", linestyle="--", linewidth=1, label=f"Knot = {KNOT:.2f}")
    ax.set_xlabel("L2 adoption share ($A_t$)", fontsize=9)
    ax.set_ylabel("Partial residual of log base fee", fontsize=9)
    ax.set_title("Partial Residuals: Adoption vs. Log Base Fee", fontsize=10)
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.2)

    fig.tight_layout()

    # Save vector PDF and 300 DPI PNG without provenance footer for journal submission
    output_stem = FIG_DIR / "partial_residual_support"
    save_figure(fig, str(output_stem), formats=["pdf", "png"])
    plt.close(fig)


def save_table(df: pd.DataFrame, stem: str, caption: str, label: str, *, escape: bool = True) -> None:
    """Save table to CSV and LaTeX with provenance footer."""
    footer = ProvenanceFooter()
    csv_path = RESULTS_DIR / f"{stem}.csv"
    tex_path = RESULTS_DIR / f"{stem}.tex"

    df.to_csv(csv_path, index=False)

    latex = footer.add_to_dataframe_latex(
        df,
        index=False,
        caption=caption,
        label=label,
        float_format="%.4f",
        escape=escape,
    )
    if not escape:
        # Light touch for math header that is already raw
        latex = latex.replace("\\hat{\\\\beta}", "\\hat{\\beta}")
    with open(tex_path, "w") as f:
        f.write(latex)


def main() -> None:
    ensure_dirs()
    df = prepare_frame()

    model, res = fit_piecewise_model(df)

    spline_df = summarize_piecewise(res)
    save_table(
        spline_df,
        stem="table_i1_spline",
        caption=f"Piecewise Semi-Elasticities for Log Base Fee (Knot at {KNOT:.2f})",
        label="tab:i1_spline",
        escape=False,
    )

    mde_df = compute_mde(df)
    save_table(
        mde_df,
        stem="table_i1_mde",
        caption="Minimum Detectable Effect (MDE) by Regime with Effective Sample Size",
        label="tab:i1_mde",
        escape=True,
    )

    partial_residual_plot(df, res)

    print("✓ Generated spline table, MDE table, and partial residual figures.")


if __name__ == "__main__":
    main()
