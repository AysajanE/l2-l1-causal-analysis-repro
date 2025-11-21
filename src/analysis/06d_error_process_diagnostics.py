#!/usr/bin/env python3
"""
CORE ITEM 12: Error-process and inference transparency

Compute and export residual diagnostics for confirmatory estimators:
- Levels OLS (naive)
- FGLS with AR(1) (Cochrane–Orcutt / Prais–Winsten)
- ECM residuals (from C2 pipeline)

Outputs:
- results/its_diagnostics/error_process_summary.csv
- results/its_diagnostics/table_c12_error_process.tex
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.stats.stattools import durbin_watson
from patsy import dmatrices
import statsmodels.api as sm

# Local imports
from src.utils.parquet_loader import load_parquet_with_date_handling
from src.models.its_levels import ITSLevelsEstimator


ROOT = Path(".")
PANEL = ROOT / "data" / "core_panel_v1" / "core_panel_v1.parquet"
OUT_DIR = ROOT / "results" / "its_diagnostics"
COINTEGRATION_DIR = ROOT / "results" / "cointegration"


def ljung_box_p(resid: np.ndarray, lags: list[int]) -> dict[int, float]:
    lb = acorr_ljungbox(resid, lags=lags, return_df=True)
    return {int(l): float(p) for l, p in zip(lb.index, lb["lb_pvalue"]) }


def fit_levels_ols(df: pd.DataFrame) -> tuple[sm.regression.linear_model.RegressionResultsWrapper, dict]:
    formula = (
        "log_base_fee ~ A_t_clean + D_star + "
        "regime_post_merge + regime_post_dencun + is_weekend + is_month_end"
    )
    y, X = dmatrices(formula, data=df, return_type="dataframe")
    res = sm.OLS(y, X).fit()
    resid = res.resid.squeeze().values
    return res, {
        "dw": float(durbin_watson(resid)),
        "lb_p_10": ljung_box_p(resid, [10])[10],
        "lb_p_20": ljung_box_p(resid, [20]).get(20, np.nan),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load panel
    df = load_parquet_with_date_handling(PANEL)
    df = df[df["date"] >= pd.Timestamp("2021-08-05")].copy()

    # Diagnostics: OLS levels
    ols_res, ols_diag = fit_levels_ols(df.dropna(subset=["log_base_fee", "A_t_clean", "D_star"]))

    # Diagnostics: FGLS AR(1)
    est = ITSLevelsEstimator(df)
    est.estimate_fgls()
    fgls_resid = est.results["fgls"]["model"].resid
    fgls_diag = {
        "dw": float(est.results["fgls"]["durbin_watson"]),
        "lb_p_10": ljung_box_p(fgls_resid, [10])[10],
        "lb_p_20": ljung_box_p(fgls_resid, [20]).get(20, np.nan),
    }

    # Diagnostics: ECM residuals (if available)
    ecm_diag_csv = COINTEGRATION_DIR / "ecm_diagnostics.csv"
    ecm_diag = {"dw": np.nan, "lb_p_10": np.nan, "lb_p_20": np.nan}
    if ecm_diag_csv.exists():
        ed = pd.read_csv(ecm_diag_csv)
        # Ljung-Box lag 10 available
        ecm_diag["lb_p_10"] = float(ed.get("ljung_box_p_lag10", pd.Series([np.nan])).iloc[0])
        # DW for ECM residuals (compute quickly by refitting without HAC)
        try:
            # Rebuild ECM regression to get residuals
            # ECT constructed in 11_ecm.py; for now, compute DW from residuals used in lb
            # Without original residual series, skip DW
            ecm_diag["dw"] = np.nan
        except Exception:
            pass

    # Summarize
    rows = [
        {"model": "Levels OLS", **ols_diag},
        {"model": "FGLS AR(1)", **fgls_diag},
        {"model": "ECM (Δ spec)", **ecm_diag},
    ]
    summ = pd.DataFrame(rows)
    csv_path = OUT_DIR / "error_process_summary.csv"
    summ.to_csv(csv_path, index=False)

    # TeX table
    def ok(p):
        return (not np.isnan(p)) and (p >= 0.05)

    decisions = []
    for _, r in summ.iterrows():
        if ok(r["lb_p_10"]) and (np.isnan(r["lb_p_20"]) or ok(r["lb_p_20"])):
            decisions.append("No autocorrelation at tested lags")
        else:
            decisions.append("Residual autocorrelation detected")
    summ["Decision"] = decisions

    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\small",
        "\\caption{Residual diagnostics for confirmatory estimators (CORE ITEM 12)}",
        "\\label{tab:c12_error_process}",
        "\\begin{tabular}{lcccc}",
        "Model & Durbin--Watson & Ljung--Box $p$ (lag 10) & Ljung--Box $p$ (lag 20) & Decision \\",
    ]
    for _, r in summ.iterrows():
        lines.append(
            f"{r['model']} & {'' if np.isnan(r['dw']) else f'{r['dw']:.2f}'} & "
            f"{'' if np.isnan(r['lb_p_10']) else f'{r['lb_p_10']:.3f}'} & "
            f"{'' if np.isnan(r['lb_p_20']) else f'{r['lb_p_20']:.3f}'} & {r['Decision']} \\"
        )
    lines += [
        "\\multicolumn{5}{l}{\\textit{Note:} Levels OLS reports strong autocorrelation. FGLS applies Prais--Winsten; ECM is estimated in differences.}\\\\",
        "\\multicolumn{5}{r}{\\footnotesize\\textcolor{gray}{Data: core\_panel\_v1 | Code: src/analysis/06d_error_process_diagnostics.py}}\\\\[-0.3ex]",
        "\\end{tabular}",
        "\\end{table}",
        "",
    ]
    (OUT_DIR / "table_c12_error_process.tex").write_text("\n".join(lines))
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {OUT_DIR / 'table_c12_error_process.tex'}")


if __name__ == "__main__":
    import pandas as pd
    main()
