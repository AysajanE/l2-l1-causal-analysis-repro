#!/usr/bin/env python3
"""
Regime Heterogeneity Table (clarity fix)
---------------------------------------

Computes pre-Dencun and post-Dencun treatment coefficients for key outcomes
with HAC SEs, plus a pooled interaction test for equality. Outputs a clear
LaTeX table with unambiguous labeling and harmonized units.

Outcomes:
 - log_base_fee (log points)
 - u_t (level)
 - S_t (harmonized scarcity; log scale if present as log_S_t)

Columns:
 - Outcome
 - Pre-Dencun β [SE] (log points)
 - Post-Dencun β [SE] (log points)
 - Diff (Post-Pre) p-value
 - Semi-elasticity 10pp (Pre)
 - Semi-elasticity 10pp (Post)
 - N (Pre/Post)

Saves: results/regimes/table_regime_heterogeneity.tex
"""

from __future__ import annotations

from pathlib import Path
import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.parquet_loader import load_parquet_with_date_handling


def fit_hac(df: pd.DataFrame, ycol: str, hac_lags: int = 7):
    X = sm.add_constant(df[["A_t_clean", "D_star", "is_weekend", "is_month_end"]])
    y = df[ycol]
    model = sm.OLS(y, X, missing="drop")
    res = model.fit()
    hac = res.get_robustcov_results(cov_type="HAC", maxlags=hac_lags)
    # Robust results return arrays; recover param by column index
    try:
        idx = list(res.params.index).index("A_t_clean")
    except Exception:
        idx = 1  # const then A_t_clean as typical order
    b = float(hac.params[idx])
    se = float(hac.bse[idx])
    return b, se, int(hac.nobs)


def pooled_interaction_p(df: pd.DataFrame, ycol: str, hac_lags: int = 7) -> float:
    df = df.copy()
    df["post_dencun"] = (df["date"] >= pd.Timestamp("2024-03-13")).astype(int)
    df["A_post"] = df["A_t_clean"] * df["post_dencun"]
    X = sm.add_constant(df[["A_t_clean", "A_post", "D_star", "is_weekend", "is_month_end"]])
    y = df[ycol]
    model = sm.OLS(y, X, missing="drop")
    res = model.fit()
    hac = res.get_robustcov_results(cov_type="HAC", maxlags=hac_lags)
    try:
        idx = list(res.params.index).index("A_post")
        pval = float(np.atleast_1d(hac.pvalues)[idx])
    except Exception:
        pval = np.nan
    return pval


def semi_elasticity_10pp(beta: float) -> float:
    # Map log-point coefficient to 10pp semi-elasticity (%). For non-log outcomes, treat as N/A.
    return (np.exp(0.10 * beta) - 1.0) * 100.0


def main():
    data_path = PROJECT_ROOT / "data" / "core_panel_v1" / "core_panel_v1.parquet"
    outdir = PROJECT_ROOT / "results" / "regimes"
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_parquet_with_date_handling(data_path)
    df["date"] = pd.to_datetime(df["date"])  # ensure datetime
    # Basic controls if missing
    if "is_weekend" not in df.columns:
        df["is_weekend"] = (df["date"].dt.dayofweek >= 5).astype(int)
    if "is_month_end" not in df.columns:
        df["is_month_end"] = df["date"].dt.is_month_end.astype(int)

    # Pre/Post splits
    pre = df[df["date"] < pd.Timestamp("2024-03-13")].copy()
    post = df[df["date"] >= pd.Timestamp("2024-03-13")].copy()

    # Outcomes mapping
    outcomes = [
        ("log_base_fee", "Log Base Fee", True),
        ("u_t", "Utilization", False),
        ("S_t", "Scarcity", False),
    ]

    rows = []
    for ycol, yname, is_log in outcomes:
        if ycol not in df.columns:
            continue
        b_pre, se_pre, npre = fit_hac(pre, ycol)
        b_post, se_post, npost = fit_hac(post, ycol)
        p_diff = pooled_interaction_p(df, ycol)
        semi_pre = semi_elasticity_10pp(b_pre) if is_log else np.nan
        semi_post = semi_elasticity_10pp(b_post) if is_log else np.nan
        rows.append({
            "Outcome": yname,
            "Pre β": b_pre,
            "Pre SE": se_pre,
            "Post β": b_post,
            "Post SE": se_post,
            "Diff p": p_diff,
            "Semi 10pp (Pre)": semi_pre,
            "Semi 10pp (Post)": semi_post,
            "N (Pre/Post)": f"{npre} / {npost}"
        })

    tbl = pd.DataFrame(rows)

    # Render LaTeX with clear labels and units
    lines = []
    lines.append("% Auto-generated: Regime heterogeneity (clarity)\n")
    lines.append("\\begin{table}[!htbp]\\centering\\small\n")
    lines.append("\\caption{Regime Heterogeneity: Pre-Dencun vs Post-Dencun Treatment Effects (log-point coefficients)}\\label{tab:regime_heterogeneity}\n")
    lines.append("\\begin{tabular}{lrrrrrcr}\\toprule\n")
    lines.append("Outcome & Pre $\\beta$ & [SE] & Post $\\beta$ & [SE] & Diff $p$ & Semi (Pre, 10pp) & N (Pre/Post) \\\\ \n")
    lines.append("\\midrule\n")
    for _, r in tbl.iterrows():
        semi_pre = (f"{r['Semi 10pp (Pre)']:.2f}\\%" if not np.isnan(r['Semi 10pp (Pre)']) else "--")
        lines.append(
            f"{r['Outcome']} & {r['Pre β']:.4f} & ({r['Pre SE']:.4f}) & {r['Post β']:.4f} & ({r['Post SE']:.4f}) & "
            f"{r['Diff p']:.3f} & {semi_pre} & {r['N (Pre/Post)']} \\\\ \n"
        )
    lines.append("\\bottomrule\\end{tabular}\n")
    lines.append("\\begin{minipage}{\\textwidth}\\small\n")
    lines.append("\\textit{Note:} Coefficients are log-point units for log outcomes and level units for utilization. Brackets report HAC SEs (Bartlett, 7 lags). Diff $p$ is from a pooled interaction test ($A_t \\times$ Post-Dencun). Semi (Pre, 10pp) maps Pre $\\beta$ to $100[\\exp(0.10\\,\\beta)-1]$ for log outcomes; N/A for utilization.\n")
    lines.append("\\end{minipage}\n")
    lines.append("\\end{table}\n")

    outpath = outdir / "table_regime_heterogeneity.tex"
    with open(outpath, "w") as f:
        f.write("".join(lines))

    print(f"Saved {outpath}")


if __name__ == "__main__":
    main()
