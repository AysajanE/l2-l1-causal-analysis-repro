#!/usr/bin/env python3
"""
Power & Precision Diagnostics for Post-Dencun Interactions (I5)
================================================================

Implements revision item I5:
  * Quantify the precision limits for the post-Dencun interaction slope
  * Compute minimum detectable effects (MDEs) using observed variance and HAC SEs
  * Replicate the post-Dencun specification with weekly aggregation to show
    how reduced serial correlation improves precision
  * Export a manuscript-ready table for Section 4.3
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import statsmodels.api as sm
from patsy import dmatrices

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "core_panel_v1" / "core_panel_v1.parquet"
RESULTS_DIR = PROJECT_ROOT / "results" / "power"


if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from project_A_effects.visualization.utils.provenance import ProvenanceFooter  # noqa: E402
from src.utils.parquet_loader import load_parquet_with_date_handling  # noqa: E402


LONDON = pd.Timestamp("2021-08-05")
MERGE = pd.Timestamp("2022-09-15")
DENCUN = pd.Timestamp("2024-03-13")

ALPHA_Z = 1.96  # two-sided 5% critical value
POWER_Z = 0.84  # 80% power
MDE_MULTIPLIER = ALPHA_Z + POWER_Z  # ≈ 2.80


@dataclass
class SpecResult:
    specification: str
    frequency: str
    beta: float
    semi_10pp: float
    se: float
    n: int
    n_eff: float
    sd_a: float
    adoption_range: str
    mde_beta: float
    mde_10pp: float


def ensure_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_data() -> pd.DataFrame:
    df = load_parquet_with_date_handling(DATA_PATH)
    df = df[df["date"] >= LONDON].sort_values("date").reset_index(drop=True)

    for col in ["is_weekend", "is_month_end", "regime_post_merge", "regime_post_dencun"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Guard against missing controls
    for col in ["D_star", "log_base_fee", "A_t_clean"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["post_dencun"] = df["regime_post_dencun"]
    df["post_merge"] = df["regime_post_merge"]

    return df.dropna(subset=["log_base_fee", "A_t_clean", "D_star"])


def effective_sample_size(series: pd.Series, max_lag: int = 7) -> float:
    """Bartlett-adjusted effective sample size under autocorrelation."""
    series = pd.Series(series).dropna()
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


def _format_range(series: pd.Series) -> str:
    low, high = series.min(), series.max()
    return f"[{low:.3f}, {high:.3f}]"


def _semi_elasticity(beta: float, delta: float = 0.10) -> float:
    return (np.exp(delta * beta) - 1.0) * 100.0


def _fit_model(design: str, data: pd.DataFrame, maxlags: int) -> sm.regression.linear_model.RegressionResultsWrapper:
    y, X = dmatrices(design, data=data, return_type="dataframe")
    model = sm.OLS(y, X)
    res = model.fit(
        cov_type="HAC",
        cov_kwds={"kernel": "bartlett", "use_correction": True, "maxlags": maxlags},
    )
    return res


def interaction_spec(df: pd.DataFrame) -> SpecResult:
    """Full-sample interaction specification: β_post = β_base + β_interaction."""
    design = """
        log_base_fee ~ A_t_clean + post_dencun:A_t_clean + D_star
        + post_merge + post_dencun + is_weekend + is_month_end
    """
    res = _fit_model(design, df, maxlags=7)

    beta = res.params["post_dencun:A_t_clean"]
    se = res.bse["post_dencun:A_t_clean"]

    post_mask = df["post_dencun"] == 1
    resid_post = pd.Series(res.resid.squeeze()).loc[post_mask.values]
    n_eff = effective_sample_size(resid_post, max_lag=7)

    sd_a = df.loc[post_mask, "A_t_clean"].std(ddof=1)
    adoption_range = _format_range(df.loc[post_mask, "A_t_clean"])

    mde_beta = MDE_MULTIPLIER * se
    mde_10pp = _semi_elasticity(mde_beta)

    return SpecResult(
        specification="Interaction Δβ (post vs. pre)",
        frequency="Daily",
        beta=beta,
        semi_10pp=_semi_elasticity(beta),
        se=se,
        n=int(df.shape[0]),
        n_eff=float(n_eff),
        sd_a=float(sd_a),
        adoption_range=adoption_range,
        mde_beta=float(mde_beta),
        mde_10pp=float(mde_10pp),
    )


def post_dencun_daily(df: pd.DataFrame) -> SpecResult:
    """Daily post-Dencun slope."""
    post = df[df["post_dencun"] == 1].copy()
    design = """
        log_base_fee ~ A_t_clean + D_star + is_weekend + is_month_end
    """
    res = _fit_model(design, post, maxlags=7)

    beta = res.params["A_t_clean"]
    se = res.bse["A_t_clean"]

    n_eff = effective_sample_size(res.resid.squeeze(), max_lag=7)
    sd_a = post["A_t_clean"].std(ddof=1)
    adoption_range = _format_range(post["A_t_clean"])

    mde_beta = MDE_MULTIPLIER * se
    mde_10pp = _semi_elasticity(mde_beta)

    return SpecResult(
        specification="Post-Dencun slope",
        frequency="Daily",
        beta=beta,
        semi_10pp=_semi_elasticity(beta),
        se=se,
        n=int(post.shape[0]),
        n_eff=float(n_eff),
        sd_a=float(sd_a),
        adoption_range=adoption_range,
        mde_beta=float(mde_beta),
        mde_10pp=float(mde_10pp),
    )


def post_dencun_weekly(df: pd.DataFrame) -> SpecResult:
    """Weekly-averaged post-Dencun slope."""
    post = df[df["post_dencun"] == 1].copy()
    post = (
        post.set_index("date")
        .resample("W-SUN", label="right", closed="right")
        .agg(
            {
                "log_base_fee": "mean",
                "A_t_clean": "mean",
                "D_star": "mean",
                "is_weekend": "mean",
                "is_month_end": "max",
            }
        )
        .dropna(subset=["log_base_fee", "A_t_clean", "D_star"])
        .reset_index(drop=True)
    )

    if post.empty:
        raise ValueError("Weekly aggregation produced an empty frame.")

    design = "log_base_fee ~ A_t_clean + D_star + is_weekend + is_month_end"
    res = _fit_model(design, post, maxlags=3)

    beta = res.params["A_t_clean"]
    se = res.bse["A_t_clean"]

    n_eff = effective_sample_size(res.resid.squeeze(), max_lag=3)
    sd_a = post["A_t_clean"].std(ddof=1)
    adoption_range = _format_range(post["A_t_clean"])

    mde_beta = MDE_MULTIPLIER * se
    mde_10pp = _semi_elasticity(mde_beta)

    return SpecResult(
        specification="Post-Dencun slope",
        frequency="Weekly",
        beta=beta,
        semi_10pp=_semi_elasticity(beta),
        se=se,
        n=int(post.shape[0]),
        n_eff=float(n_eff),
        sd_a=float(sd_a),
        adoption_range=adoption_range,
        mde_beta=float(mde_beta),
        mde_10pp=float(mde_10pp),
    )


def save_table(rows: List[SpecResult]) -> None:
    df = pd.DataFrame([row.__dict__ for row in rows])
    df = df[
        [
            "specification",
            "frequency",
            "n",
            "n_eff",
            "sd_a",
            "adoption_range",
            "beta",
            "semi_10pp",
            "se",
            "mde_beta",
            "mde_10pp",
        ]
    ]
    df.rename(
        columns={
            "specification": "Specification",
            "frequency": "Frequency",
            "n": "N",
            "n_eff": r"$N_{\text{eff}}$",
            "sd_a": r"$\mathrm{sd}(A_t)$",
            "adoption_range": "Adoption Range",
            "beta": r"$\hat{\beta}$",
            "semi_10pp": "Semi-elasticity (10pp)",
            "se": "HAC SE",
            "mde_beta": "MDE (beta units)",
            "mde_10pp": "MDE (10pp %)",
        },
        inplace=True,
    )

    footer = ProvenanceFooter()
    csv_path = RESULTS_DIR / "table_i5_power_precision.csv"
    tex_path = RESULTS_DIR / "table_i5_power_precision.tex"

    df.to_csv(csv_path, index=False)

    latex = footer.add_to_dataframe_latex(
        df,
        index=False,
        caption="Power diagnostics for post-Dencun interaction and slope specifications.",
        label="tab:i5_power_precision",
        float_format="%.4f",
        escape=False,
    )
    # Replace booktabs rules with \hline to avoid alignment issues in some builds
    latex = latex.replace('\\toprule', '\\hline').replace('\\midrule', '\\hline').replace('\\bottomrule', '\\hline')
    with open(tex_path, "w") as f:
        f.write(latex)


def main() -> None:
    ensure_dirs()
    df = load_data()

    rows: List[SpecResult] = [
        interaction_spec(df),
        post_dencun_daily(df),
        post_dencun_weekly(df),
    ]

    save_table(rows)

    print("✓ Generated power diagnostics table for post-Dencun interactions.")
    for row in rows:
        print(
            f"{row.specification} ({row.frequency}): "
            f"SE={row.se:.3f}, MDE(β)={row.mde_beta:.3f}, MDE(10pp)={row.mde_10pp:.1f}%"
        )


if __name__ == "__main__":
    main()
