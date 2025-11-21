#!/usr/bin/env python3
"""
OVB Robustness Quantification (Cinelli–Hazlett RV)
==================================================

Compute a simple Cinelli–Hazlett robustness value (RV) for the ECM short-run
effect (psi on ΔA_t) to assess how strong unobserved confounding would need
to be to reduce the estimate to zero. RV ≈ t^2 / (t^2 + df).

Outputs:
  - results/ovb/rv_ecm_delta.csv
  - results/ovb/table_ovb_rv.tex
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

import pyarrow.parquet as pq

LONDON = pd.Timestamp('2021-08-05')
MERGE = pd.Timestamp('2022-09-15')
DENCUN = pd.Timestamp('2024-03-13')


def _load_parquet_robust(path: Path) -> pd.DataFrame:
    table = pq.read_table(path)
    df_dict = {}
    for col in table.column_names:
        col_data = table[col]
        if col == 'date' or 'date' in str(col_data.type).lower():
            df_dict[col] = pd.to_datetime([str(x) for x in col_data.to_pylist()])
        else:
            try:
                df_dict[col] = col_data.to_pandas()
            except Exception:
                df_dict[col] = [str(x) for x in col_data.to_pylist()]
    return pd.DataFrame(df_dict)


def load_core_panel() -> pd.DataFrame:
    path = Path('data/core_panel_v1/core_panel_v1.parquet')
    df = _load_parquet_robust(path)
    df = df[df['date'] >= LONDON].sort_values('date').reset_index(drop=True)
    # Ensure basic columns
    if 'log_base_fee' not in df.columns and 'base_fee_median_gwei' in df.columns:
        df['log_base_fee'] = np.log(df['base_fee_median_gwei'] + 1.0)
    if 'is_weekend' not in df.columns:
        df['is_weekend'] = (df['date'].dt.dayofweek >= 5).astype(int)
    if 'is_month_end' not in df.columns:
        df['is_month_end'] = df['date'].dt.is_month_end.astype(int)
    return df


def build_ecm_short_run(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy().sort_values('date').reset_index(drop=True)
    # Lagged levels cointegration residual proxy: residual of log_base_fee ~ A_t + D* + regimes + calendar
    y = d['log_base_fee']
    X = sm.add_constant(d[['A_t_clean', 'D_star', 'regime_post_merge', 'regime_post_dencun', 'is_weekend', 'is_month_end']].fillna(0))
    ols = sm.OLS(y, X, missing='drop').fit()
    d['ecm_resid_lag'] = ols.resid.shift(1)
    # Short-run differences
    d['d_log_base_fee'] = d['log_base_fee'].diff()
    d['d_A_t'] = d['A_t_clean'].diff()
    d['d_D_star'] = d['D_star'].diff()
    d = d.dropna(subset=['d_log_base_fee', 'd_A_t', 'd_D_star', 'ecm_resid_lag']).copy()
    return d


def fit_short_run(d: pd.DataFrame):
    y = d['d_log_base_fee']
    X = sm.add_constant(d[['d_A_t', 'd_D_star', 'regime_post_merge', 'regime_post_dencun', 'is_weekend', 'is_month_end', 'ecm_resid_lag']].fillna(0))
    res = sm.OLS(y, X, missing='drop').fit(cov_type='HAC', cov_kwds={'maxlags': 7, 'use_correction': True})
    return res


def robustness_value_tipping_to_zero(t_stat: float, df: int) -> float:
    # Cinelli–Hazlett (2020) robustness value RV ≈ t^2 / (t^2 + df)
    return float((t_stat**2) / (t_stat**2 + df))


def main():
    outdir = Path('results/ovb')
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_core_panel()
    # Confirmatory window: pre-Dencun
    df_pre = df[(df['date'] >= LONDON) & (df['date'] < DENCUN)].copy()
    design = build_ecm_short_run(df_pre)
    res = fit_short_run(design)
    # Extract t-stat and df for d_A_t
    try:
        t = float(res.tvalues['d_A_t'])
    except Exception:
        t = float(res.tvalues[1])
    df_resid = int(res.df_resid)
    rv = robustness_value_tipping_to_zero(t, df_resid)

    pd.DataFrame([{
        'window': 'Pre-Dencun',
        't_stat_dA': t,
        'df_resid': df_resid,
        'rv_tipping_zero': rv
    }]).to_csv(outdir / 'rv_ecm_delta.csv', index=False)

    # Render a compact LaTeX table
    lines = []
    lines.append('% Auto-generated: OVB robustness (Cinelli–Hazlett RV)\n')
    lines.append('\\begin{table}[!htbp]\\centering\\small\n')
    lines.append('\\caption{OVB Robustness for ECM Short-Run Effect (Cinelli–Hazlett RV)}\\label{tab:ovb_rv}\n')
    lines.append('\\begin{tabular}{lccc}\\toprule\n')
    lines.append('Window & $t(\\Delta A_t)$ & df & Robustness Value (to zero) \\\\ \n')
    lines.append('\\midrule\n')
    lines.append(f"Pre-Dencun & {t:.2f} & {df_resid} & {rv:.3f} \\\\ \n")
    lines.append('\\bottomrule\\end{tabular}\n')
    lines.append('\\end{table}\n')
    (outdir / 'table_ovb_rv.tex').write_text(''.join(lines))

    print('Saved OVB robustness outputs to', str(outdir))


if __name__ == '__main__':
    main()
