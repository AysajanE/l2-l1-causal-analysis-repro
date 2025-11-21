#!/usr/bin/env python3
"""
Residual Dependence Diagnostics and ARMA Error Selection
=======================================================

Purpose:
- Diagnose residual autocorrelation in the levels specification and mitigate it
  by selecting an ARMA(p,q) error model via AIC, reporting Ljung–Box p-values.
- Save a compact table with OLS-HAC and the best ARMA error model, including
  Durbin–Watson and Ljung–Box diagnostics.

Outputs (under results/diagnostics):
- arma_grid.csv               (full grid search over p=0..3, q=0..2)
- table_resid_arma_levels.tex (LaTeX table with OLS vs best-ARMA diagnostics)

Notes:
- Confirmatory emphasis remains on the ECM (short-run Δ model with HAC). This
  ARMA specification is a supportive robustness for levels with serially
  correlated errors.
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
from src.models.its_levels import ITSLevelsEstimator


def main():
    data_path = PROJECT_ROOT / 'data' / 'core_panel_v1' / 'core_panel_v1.parquet'
    outdir = PROJECT_ROOT / 'results' / 'diagnostics'
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_parquet_with_date_handling(data_path)
    df['date'] = pd.to_datetime(df['date'])

    est = ITSLevelsEstimator(df, outcome='log_base_fee', treatment='A_t_clean')
    # Fit OLS-HAC main spec to summarize DW and LBQ for baseline
    main = est.estimate_main_spec(use_time_trend=False)

    # Compute DW and LBQ for OLS baseline residuals
    ols_res = est.results['main_hac']
    import numpy as np
    from statsmodels.stats.diagnostic import acorr_ljungbox
    from statsmodels.stats.stattools import durbin_watson
    resid = ols_res.resid
    dw = float(durbin_watson(resid))
    lb = acorr_ljungbox(resid, lags=10, return_df=True)
    lb_p_at_10 = float(lb['lb_pvalue'].iloc[-1])

    # Grid select ARMA(p,q) error model
    sel = est.estimate_arma_grid(max_p=3, max_q=2, lb_lags=10)
    est.results['arma_grid'].to_csv(outdir / 'arma_grid.csv', index=False)

    best = sel['best']
    # Compose a compact comparison table
    rows = []
    rows.append({
        'Specification': 'OLS-HAC (levels)',
        'Beta (A_t)': main['beta'],
        'SE': main['se'],
        'DW': dw,
        'LB p@10': lb_p_at_10,
        'AIC': np.nan,
        'N': est.results['main_effect']['n_obs']
    })
    rows.append({
        'Specification': f"ARMA({int(best['p'])},{int(best['q'])}) errors",
        'Beta (A_t)': best['beta'],
        'SE': best['se'],
        'DW': best['dw'],
        'LB p@10': best['lb_p_at_maxlag'],
        'AIC': best['aic'],
        'N': best['n']
    })
    tbl = pd.DataFrame(rows)

    # Render LaTeX
    lines = []
    lines.append('% Auto-generated: Residual dependence diagnostics (levels)\n')
    lines.append('\\begin{table}[!htbp]\\centering\\small\n')
    lines.append('\\caption{Residual Dependence and ARMA Error Selection (Levels Specification)}\\label{tab:resid_arma_levels}\n')
    lines.append('\\begin{tabular}{lrrrrrr}\\toprule\n')
    lines.append('Specification & $\\hat{\\beta}$ & SE & DW & LB p@10 & AIC & N \\\\ \n')
    lines.append('\\midrule\n')
    for _, r in tbl.iterrows():
        lines.append(f"{r['Specification']} & {r['Beta (A_t)']:.4f} & {r['SE']:.4f} & {r['DW']:.3f} & {r['LB p@10']:.3f} & {r['AIC'] if not np.isnan(r['AIC']) else '--'} & {int(r['N'])} \\\\ \n")
    lines.append('\\bottomrule\\end{tabular}\n')
    lines.append('\\end{table}\n')

    with open(outdir / 'table_resid_arma_levels.tex', 'w') as f:
        f.write(''.join(lines))

    print('Saved:')
    print(f"  - {outdir / 'arma_grid.csv'}")
    print(f"  - {outdir / 'table_resid_arma_levels.tex'}")


if __name__ == '__main__':
    main()

