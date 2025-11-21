#!/usr/bin/env python3
"""
Stationarity, Cointegration, and ECM Analysis (C2)
==================================================

Implements unit-root tests (ADF, KPSS, PP), Engle–Granger cointegration tests
(full sample and by regime), and Error-Correction Model (ECM) estimation as a
confirmatory model when cointegration is detected. Saves CSV summaries and
LaTeX tables for manuscript inclusion.

Outputs:
  - results/cointegration/unit_root_tests.csv
  - results/cointegration/eg_tests.csv
  - results/cointegration/johansen_tests.csv
  - results/cointegration/ecm_results.csv
  - results/cointegration/table_c2_eg_tests.tex
  - results/cointegration/table_c2_johansen.tex
  - results/cointegration/table_c2_ecm.tex

Notes:
  - Uses raw (unwinsorized) series from core_panel_v1
  - Post-London sample only (2021-08-05 onward)
  - Includes calendar controls; regime dummies where specified
  - Optional CLI flag ``--winsor`` applies symmetric winsorization before estimation
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.tsa.vector_ar.vecm import coint_johansen
from statsmodels.regression.linear_model import OLS
from patsy import dmatrices
from statsmodels.stats.diagnostic import acorr_ljungbox

try:
    from arch.unitroot import PhillipsPerron
    HAS_ARCH = True
except Exception:
    HAS_ARCH = False


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


def load_core_panel(winsorized: bool = False, winsor_pct: float = 0.005) -> pd.DataFrame:
    path = Path('data/core_panel_v1/core_panel_v1.parquet')
    if not path.exists():
        raise FileNotFoundError(f"Core panel not found: {path}")
    df = _load_parquet_robust(path)

    # Post-London filter and sorting
    df = df[df['date'] >= LONDON].sort_values('date').reset_index(drop=True)

    # Ensure key variables are present
    if 'log_base_fee' not in df.columns and 'base_fee_median_gwei' in df.columns:
        df['log_base_fee'] = np.log(df['base_fee_median_gwei'] + 1.0)

    # Calendar controls if missing
    if 'is_weekend' not in df.columns:
        df['is_weekend'] = (df['date'].dt.dayofweek >= 5).astype(int)
    if 'is_month_end' not in df.columns:
        df['is_month_end'] = df['date'].dt.is_month_end.astype(int)

    # Regime labels
    def regime_label(d: pd.Timestamp) -> str:
        if d < MERGE:
            return 'London-Merge'
        elif d < DENCUN:
            return 'Merge-Dencun'
        return 'Post-Dencun'

    df['regime_label'] = df['date'].apply(regime_label)

    # Differences
    df['d_log_base_fee'] = df['log_base_fee'].diff()
    df['d_A_t_clean'] = df['A_t_clean'].diff()
    if 'D_star' in df.columns:
        df['d_D_star'] = df['D_star'].diff()
    else:
        df['D_star'] = np.nan
        df['d_D_star'] = np.nan

    if winsorized:
        continuous = ['log_base_fee', 'A_t_clean', 'D_star', 'u_t', 'S_t']
        for col in continuous:
            if col in df.columns:
                lower = df[col].quantile(winsor_pct)
                upper = df[col].quantile(1 - winsor_pct)
                df[col] = df[col].clip(lower, upper)

    return df


def build_targeted_event_dummies(df_dates: pd.Series) -> pd.DataFrame:
    """Construct targeted day dummies for exogenous shocks beyond D*.

    - Airdrops: parse docs/events_calendar/events.csv and flag rows with
      Event Category containing 'Token Airdrop' on the exact date.
    - L2 outages: parse data/external/l2_outages.csv and flag dates with
      hours_down > 0 (any chain).

    Returns a DataFrame with columns:
      ['date', 'airdrop_day', 'outage_day'] (Int64 dummies)
    Missing inputs yield zeros (defensive default).
    """
    # Initialize with all analysis dates
    ev = pd.DataFrame({'date': pd.to_datetime(df_dates).astype('datetime64[ns]')})
    ev = ev.drop_duplicates().sort_values('date').reset_index(drop=True)
    ev['airdrop_day'] = 0
    ev['outage_day'] = 0

    # Airdrops from curated calendar
    try:
        ec_path = Path('docs/events_calendar/events.csv')
        if ec_path.exists():
            ec = pd.read_csv(ec_path)
            # Try robust date parsing (support either 'date' or first column)
            if 'date' in ec.columns:
                ec_dates = pd.to_datetime(ec['date'], errors='coerce')
            else:
                ec_dates = pd.to_datetime(ec.iloc[:, 0], errors='coerce')

            # Identify category column heuristically
            cat_col = None
            for c in ec.columns:
                if 'category' in c.lower():
                    cat_col = c
                    break
            if cat_col is None:
                # Fallback: search full text for token airdrop pattern
                text = ec.apply(lambda r: ' '.join([str(x) for x in r.values]), axis=1)
                is_airdrop = text.str.contains('Token Airdrop', case=False, na=False)
            else:
                is_airdrop = ec[cat_col].astype(str).str.contains('Token Airdrop', case=False, na=False)

            airdrop_dates = pd.to_datetime(ec_dates[is_airdrop]).dropna().dt.normalize().unique()
            if len(airdrop_dates) > 0:
                ev.loc[ev['date'].isin(airdrop_dates), 'airdrop_day'] = 1
    except Exception:
        # Leave zeros if calendar unavailable
        pass

    # L2 outages (bridge/sequencer outages)
    try:
        out_path = Path('data/external/l2_outages.csv')
        if out_path.exists():
            out = pd.read_csv(out_path)
            if 'hours_down' in out.columns:
                out_dates = pd.to_datetime(out['date'], errors='coerce')
                mask = (pd.to_numeric(out['hours_down'], errors='coerce').fillna(0) > 0)
                outage_dates = pd.to_datetime(out_dates[mask]).dropna().dt.normalize().unique()
                if len(outage_dates) > 0:
                    ev.loc[ev['date'].isin(outage_dates), 'outage_day'] = 1
    except Exception:
        # Leave zeros if outages file not available
        pass

    # Ensure integer dtype
    ev['airdrop_day'] = ev['airdrop_day'].astype('Int64')
    ev['outage_day'] = ev['outage_day'].astype('Int64')
    return ev


def unit_root_summary(series: pd.Series, name: str) -> Dict:
    s = series.dropna().astype(float)
    out: Dict[str, float] = {'variable': name, 'n': len(s)}

    # ADF with intercept and trend (GLS detrending left to defaults);
    # select lags by AIC where possible
    try:
        res = adfuller(s, regression='ct', autolag='AIC')
        out.update({'adf_stat': res[0], 'adf_p': res[1]})
    except Exception as e:
        out.update({'adf_stat': np.nan, 'adf_p': np.nan})

    # KPSS with trend (H0: stationarity)
    try:
        kpss_stat, kpss_p, _, _ = kpss(s, regression='ct', nlags='auto')
        out.update({'kpss_stat': kpss_stat, 'kpss_p': kpss_p})
    except Exception:
        out.update({'kpss_stat': np.nan, 'kpss_p': np.nan})

    # Phillips–Perron (if available)
    if HAS_ARCH:
        try:
            pp = PhillipsPerron(s, lags=None, trend='ct')
            out.update({'pp_stat': pp.stat, 'pp_p': pp.pvalue})
        except Exception:
            out.update({'pp_stat': np.nan, 'pp_p': np.nan})
    else:
        out.update({'pp_stat': np.nan, 'pp_p': np.nan})

    return out


def engle_granger(df: pd.DataFrame, y: str, xvars: List[str]) -> Tuple[float, float, pd.Series]:
    """Engle–Granger residual ADF test (regress y on X, ADF on residuals)."""
    # Drop NA rows for all variables
    use = df[[y] + xvars].dropna().copy()
    if use.empty:
        return np.nan, np.nan, pd.Series(dtype=float)

    y_mat, X_mat = dmatrices(f"{y} ~ {' + '.join(xvars)}", data=use, return_type='dataframe')
    model = OLS(y_mat, X_mat).fit()
    resid = model.resid.squeeze()

    # ADF on residuals with intercept only (no trend) per EG; select lags by AIC
    try:
        r = adfuller(resid, regression='c', autolag='AIC')
        stat, pval = r[0], r[1]
    except Exception:
        stat, pval = np.nan, np.nan
    return stat, pval, resid


def estimate_ecm(df: pd.DataFrame, y: str, xvars: List[str], resid: pd.Series,
                 event_controls: List[str] | None = None) -> Dict:
    """Estimate single-equation ECM: Δy_t on ECT_{t-1}, Δx_t, and controls."""
    frame = df.copy().reset_index(drop=True)

    # Align residuals back to frame index (assumes same rows used); reindex safely
    resid = resid.reindex(frame.index)
    frame['ECT'] = resid
    frame['ECT_lag1'] = frame['ECT'].shift(1)

    # Build ΔX terms for selected regressors present in data
    terms = []
    if 'A_t_clean' in frame.columns:
        frame['d_A_t_clean'] = frame['A_t_clean'].diff()
        terms.append('d_A_t_clean')
    if 'D_star' in frame.columns:
        frame['d_D_star'] = frame['D_star'].diff()
        terms.append('d_D_star')

    # Always include calendar dummies in levels (I(0))
    controls = ['is_weekend', 'is_month_end']
    if event_controls:
        controls = controls + [c for c in event_controls if c in frame.columns]
    present_controls = [c for c in controls if c in frame.columns]

    # Include lagged Δy to address serial correlation in ECM residuals
    if 'd_log_base_fee' not in frame.columns:
        frame['d_log_base_fee'] = frame['log_base_fee'].diff()
    frame['d_log_base_fee_lag1'] = frame['d_log_base_fee'].shift(1)

    formula_parts = ['d_log_base_fee ~ ECT_lag1'] + terms + ['d_log_base_fee_lag1'] + present_controls
    formula = ' + '.join(formula_parts)

    use = frame.dropna(subset=['d_log_base_fee', 'ECT_lag1'] + terms)
    if len(use) < 30:
        return {
            'phi': np.nan, 'phi_se': np.nan, 'phi_p': np.nan,
            'psi': np.nan, 'psi_se': np.nan, 'psi_p': np.nan,
            'n': len(use), 'half_life_days': np.nan
        }

    y_mat, X_mat = dmatrices(formula, data=use, return_type='dataframe')
    model = OLS(y_mat, X_mat)

    # HAC SEs with modest bandwidth (weekly horizon)
    n = len(use)
    bw = min(7, max(1, int(4 * (n/100) ** (2/9))))
    res = model.fit(cov_type='HAC', cov_kwds={'maxlags': bw, 'kernel': 'bartlett', 'use_correction': True})

    # Extract key parameters
    phi = res.params.get('ECT_lag1', np.nan)
    phi_se = res.bse.get('ECT_lag1', np.nan)
    phi_p = res.pvalues.get('ECT_lag1', np.nan)

    psi = res.params.get('d_A_t_clean', np.nan)
    psi_se = res.bse.get('d_A_t_clean', np.nan)
    psi_p = res.pvalues.get('d_A_t_clean', np.nan)

    # Speed of adjustment half-life
    # z_t ≈ (1 + phi) z_{t-1} => half-life = ln(0.5)/ln(|1 + phi|)
    half_life = np.nan
    try:
        if not np.isnan(phi) and (1 + phi) > 0:
            half_life = np.log(0.5) / np.log(1 + phi)
    except Exception:
        half_life = np.nan

    return {
        'phi': phi, 'phi_se': phi_se, 'phi_p': phi_p,
        'psi': psi, 'psi_se': psi_se, 'psi_p': psi_p,
        'n': len(use), 'bw': bw, 'half_life_days': half_life
    }


def johansen_tests(df: pd.DataFrame, series: List[str], det_order: int = 1, k_ar_diff: int = 1) -> pd.DataFrame:
    """
    Johansen cointegration tests (trace and max eigenvalue) for given series.
    det_order: 1 includes intercept in cointegration relation; k_ar_diff: lag order in Δ.
    Returns tidy DataFrame with stats and critical values for r<=0 and r<=1.
    """
    results: List[Dict] = []
    sub = df.dropna(subset=series).copy()
    if len(sub) < 50:
        return pd.DataFrame(columns=['sample', 'rank_null', 'stat_type', 'stat', 'crit_90', 'crit_95', 'crit_99'])
    X = sub[series].to_numpy()
    try:
        joh = coint_johansen(X, det_order, k_ar_diff)
        # For ranks 0 and 1 (given 3 variables)
        for r in [0, 1]:
            results.append({
                'sample': 'Full Post-London',
                'rank_null': f'r<={r}',
                'stat_type': 'trace',
                'stat': float(joh.lr1[r]),
                'crit_90': float(joh.cvt[r, 0]),
                'crit_95': float(joh.cvt[r, 1]),
                'crit_99': float(joh.cvt[r, 2]),
            })
            results.append({
                'sample': 'Full Post-London',
                'rank_null': f'r={r}',
                'stat_type': 'max-eig',
                'stat': float(joh.lr2[r]),
                'crit_90': float(joh.cvm[r, 0]),
                'crit_95': float(joh.cvm[r, 1]),
                'crit_99': float(joh.cvm[r, 2]),
            })
    except Exception:
        return pd.DataFrame(columns=['sample', 'rank_null', 'stat_type', 'stat', 'crit_90', 'crit_95', 'crit_99'])
    return pd.DataFrame(results)


def save_latex_johansen(df: pd.DataFrame, out_path: Path) -> None:
    if df.empty:
        out_path.write_text("% Johansen test not available or insufficient data\n")
        return
    lines = []
    lines.append("% Auto-generated: Johansen Cointegration Tests (C2)\n")
    lines.append("\\begin{table}[!htbp]\\centering\\small\n")
    lines.append("\\caption{Johansen Cointegration Tests (Trace and Max-Eigen)}\\label{tab:c2_johansen}\n")
    lines.append("\\begin{tabular}{lcccccc}\\toprule\n")
    lines.append("Null & Stat & 90\\% & 95\\% & 99\\% & Type & Sample \\\\ \n")
    lines.append("\\midrule\n")
    for _, r in df.iterrows():
        lines.append(f"{r['rank_null']} & {r['stat']:.2f} & {r['crit_90']:.2f} & {r['crit_95']:.2f} & {r['crit_99']:.2f} & {r['stat_type']} & {r['sample']} \\\\ \n")
    lines.append("\\bottomrule\\end{tabular}\n\\end{table}\n")
    out_path.write_text(''.join(lines))


def save_latex_eg(df: pd.DataFrame, out_path: Path) -> None:
    rows = []
    for _, r in df.iterrows():
        label = r['sample']
        stat = r['eg_adf_stat']
        pv = r['eg_adf_p']
        rows.append(f"{label} & {stat:.3f} & {pv:.3f} \\\n")

    lines = []
    lines.append("% Auto-generated: Engle--Granger Cointegration Tests (C2)\n")
    lines.append("\\begin{table}[!htbp]\n")
    lines.append("\\centering\n\\small\n")
    lines.append("\\caption{Engle--Granger Cointegration Tests: Residual ADF on Long-Run Relation}\n")
    lines.append("\\label{tab:c2_eg}\n")
    lines.append("\\begin{tabular}{lcc}\n")
    lines.append("\\hline\n")
    lines.append("Sample & Residual ADF $t$ & $p$-value \\\\ \n")
    lines.append("\\hline\n")
    lines.append(''.join(rows))
    lines.append("\\hline\n\\end{tabular}\n")
    lines.append("\\begin{minipage}{0.92\\textwidth}\n")
    lines.append("\\vspace{0.3em}\\footnotesize\\textit{Note:} Long-run regression: $\\log C^{fee}_t$ on $A_t$, $D^*_t$ and calendar dummies; full-sample regression also includes regime dummies. Residual ADF uses intercept (no trend) with lag length selected by AIC. Rejecting the unit-root null ($p<0.05$) indicates cointegration. *** $p<0.001$, ** $p<0.01$, * $p<0.05$.\n")
    lines.append("\\end{minipage}\n\\end{table}\n")
    out_path.write_text(''.join(lines))


def save_latex_ecm(res: Dict, out_path: Path) -> None:
    phi, phi_se, phi_p = res['phi'], res['phi_se'], res['phi_p']
    psi, psi_se, psi_p = res['psi'], res['psi_se'], res['psi_p']
    n, bw, hl = res['n'], res['bw'], res['half_life_days']

    def stars(p):
        return '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else ''))

    phi_str = f"{phi:.3f}{stars(phi_p)} ({phi_se:.3f})" if np.isfinite(phi) else 'N/A'
    psi_str = f"{psi:.3f}{stars(psi_p)} ({psi_se:.3f})" if np.isfinite(psi) else 'N/A'
    hl_str = f"{hl:.1f}" if np.isfinite(hl) else 'N/A'

    template = "% Auto-generated: Error-Correction Model (C2)\n" \
               "\\begin{{table}}[!htbp]\n" \
               "\\centering\n" \
               "\\small\n" \
               "\\caption{{Error--Correction Model: $\\Delta \\log C^{{fee}}_t = \\phi \\cdot ECT_{{t-1}} + \\psi\\,\\Delta A_t + \\kappa\\,\\Delta D^*_t +$ calendar}}\n" \
               "\\label{{tab:c2_ecm}}\n" \
               "\\begin{{tabular}}{{lcc}}\n" \
               "\\toprule\n" \
               "Parameter & Estimate (SE) & Inference \\\\\n" \
               "\\midrule\n" \
               "Speed of adjustment $\\phi$ & {phi} & Half-life (days): {hl} \\\\\n" \
               "Short-run effect $\\psi$ (on $\\Delta A_t$) & {psi} & HAC bw={bw} \\\\\n" \
               "\\midrule\n" \
               "Observations & \\multicolumn{{2}}{{c}}{{{n}}} \\\\\n" \
               "\\bottomrule\n" \
               "\\end{{tabular}}\n" \
               "\\begin{{minipage}}{{0.92\\textwidth}}\n" \
               "\\vspace{{0.3em}}\\footnotesize\\textit{{Note:}} HAC (Bartlett) standard errors with maxlags={bw}. $ECT_{{t-1}}$ is the lagged residual from the long-run relation ($\\log C^{{fee}}_t$ on $A_t$, $D^*_t$, regime and calendar dummies). A significantly negative $\\phi$ indicates correction toward the long-run equilibrium. *** $p<0.001$, ** $p<0.01$, * $p<0.05$.\n" \
               "\\end{{minipage}}\n" \
               "\\end{{table}}\n"

    tex = template.format(phi=phi_str, psi=psi_str, hl=hl_str, bw=bw if np.isfinite(bw) else 'N/A', n=n)
    out_path.write_text(tex)


def save_latex_ecm_compact(res: Dict, out_path: Path) -> None:
    """Backcompat wrapper calling plain compact table generator."""
    save_latex_ecm_compact_plain(res, out_path)


def save_latex_ecm_compact_plain(res: Dict, out_path: Path) -> None:
    """Plain ASCII compact ECM summary for main text (robust to LaTeX alignment issues)."""
    phi, phi_se, phi_p = res['phi'], res['phi_se'], res['phi_p']
    psi, psi_se, psi_p = res['psi'], res['psi_se'], res['psi_p']
    n, hl = res['n'], res['half_life_days']

    def star(p):
        return '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else ''))

    lines = []
    lines.append("% Auto-generated: Compact ECM Summary (Plain)\n")
    lines.append("\\begin{table}[!htbp]\n")
    lines.append("\\centering\\small\n")
    lines.append("\\caption{ECM Summary (Main Text)}\n")
    lines.append("\\label{tab:ecm_main_summary}\n")
    lines.append("\\begin{tabular}{lccc}\n")
    lines.append("\\hline\n")
    lines.append("Parameter & Estimate & (SE) & Half-life (days) \\\\ \n")
    lines.append("\\hline\n")
    if np.isfinite(phi):
        lines.append(f"phi (speed) & {phi:.3f}{star(phi_p)} & ({phi_se:.3f}) & {hl:.1f} \\\\ \n")
    else:
        lines.append("phi (speed) & N/A & N/A & N/A \\\\ \n")
    if np.isfinite(psi):
        lines.append(f"psi (short-run dA) & {psi:.3f}{star(psi_p)} & ({psi_se:.3f}) & --- \\\\ \n")
    else:
        lines.append("psi (short-run dA) & N/A & N/A & --- \\\\ \n")
    lines.append(f"\\hline\n\\multicolumn{{4}}{{r}}{{\\footnotesize N = {n}}}\\\\ \n")
    lines.append("\\hline\n")
    lines.append("\\end{tabular}\n")
    lines.append("\\end{table}\n")
    out_path.write_text(''.join(lines))

def main():
    parser = argparse.ArgumentParser(
        description="Engle–Granger and ECM diagnostics (default: raw series, no winsorization)."
    )
    parser.add_argument(
        "--no-winsor",
        dest="no_winsor",
        action="store_true",
        default=True,
        help="Use raw, unwinsorized series (default)."
    )
    parser.add_argument(
        "--winsor",
        dest="no_winsor",
        action="store_false",
        help="Apply symmetric winsorization to key series before estimation."
    )
    parser.add_argument(
        "--winsor-pct",
        type=float,
        default=0.005,
        help="Tail probability for symmetric winsorization (default 0.5%%)."
    )
    args = parser.parse_args()

    out_dir = Path('results/cointegration')
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_core_panel(winsorized=not args.no_winsor, winsor_pct=args.winsor_pct)
    if args.no_winsor:
        print("Input series: raw (no winsorization).")
    else:
        print(f"Input series: winsorized at {args.winsor_pct * 100:.2f}% tails.")

    # Unit-root tests (levels and first differences) for key variables
    vars_to_test = [
        ('log_base_fee', 'Levels: log_base_fee'),
        ('A_t_clean', 'Levels: A_t_clean'),
        ('D_star', 'Levels: D_star'),
        ('d_log_base_fee', 'Diff: d_log_base_fee'),
        ('d_A_t_clean', 'Diff: d_A_t_clean'),
        ('d_D_star', 'Diff: d_D_star'),
    ]

    unit_rows = []
    for col, label in vars_to_test:
        if col in df.columns:
            unit_rows.append(unit_root_summary(df[col], label))

    unit_df = pd.DataFrame(unit_rows)
    unit_df.to_csv(out_dir / 'unit_root_tests.csv', index=False)

    # Engle–Granger tests: full sample and by regime
    # Long-run set of regressors
    x_full = ['A_t_clean', 'D_star', 'is_weekend', 'is_month_end', 'regime_post_merge', 'regime_post_dencun']
    # Add regime dummies if they exist; else construct
    if 'regime_post_merge' not in df.columns:
        df['regime_post_merge'] = ((df['date'] >= MERGE) & (df['date'] < DENCUN)).astype(int)
    if 'regime_post_dencun' not in df.columns:
        df['regime_post_dencun'] = (df['date'] >= DENCUN).astype(int)

    eg_rows = []

    # Full sample EG
    eg_stat, eg_p, resid = engle_granger(df, y='log_base_fee', xvars=x_full)
    eg_rows.append({'sample': 'Full Post-London', 'eg_adf_stat': eg_stat, 'eg_adf_p': eg_p})

    # By regime (calendar controls only)
    for regime in ['London-Merge', 'Merge-Dencun', 'Post-Dencun']:
        sub = df[df['regime_label'] == regime]
        xvars = ['A_t_clean', 'D_star', 'is_weekend', 'is_month_end']
        stat, pval, _ = engle_granger(sub, y='log_base_fee', xvars=xvars)
        eg_rows.append({'sample': regime, 'eg_adf_stat': stat, 'eg_adf_p': pval})

    eg_df = pd.DataFrame(eg_rows)
    eg_df.to_csv(out_dir / 'eg_tests.csv', index=False)

    # Johansen test on (log_base_fee, A_t_clean, D_star)
    joh = johansen_tests(df, ['log_base_fee', 'A_t_clean', 'D_star'], det_order=1, k_ar_diff=1)
    joh.to_csv(out_dir / 'johansen_tests.csv', index=False)

    # ECM estimation only if full-sample cointegration is detected (p<0.05)
    ecm_summary = {
        'phi': np.nan, 'phi_se': np.nan, 'phi_p': np.nan,
        'psi': np.nan, 'psi_se': np.nan, 'psi_p': np.nan,
        'n': 0, 'bw': np.nan, 'half_life_days': np.nan
    }
    if np.isfinite(eg_p) and eg_p < 0.05:
        ecm_summary = estimate_ecm(df, y='log_base_fee', xvars=x_full, resid=resid)

    pd.DataFrame([ecm_summary]).to_csv(out_dir / 'ecm_results.csv', index=False)

    # ECM residual diagnostics: ADF on residuals of ECM and Ljung-Box
    try:
        # Refit ECM to get residuals using same design
        frame = df.copy().reset_index(drop=True)
        # align residuals and build ECT terms
        resid_aligned = resid.reindex(frame.index)
        frame['ECT_lag1'] = resid_aligned.shift(1)
        frame['d_log_base_fee'] = frame['log_base_fee'].diff()
        frame['d_A_t_clean'] = frame['A_t_clean'].diff()
        frame['d_D_star'] = frame['D_star'].diff()
        frame['d_log_base_fee_lag1'] = frame['d_log_base_fee'].shift(1)
        use = frame.dropna(subset=['d_log_base_fee', 'ECT_lag1', 'd_A_t_clean'])
        base_rhs = 'ECT_lag1 + d_A_t_clean + d_D_star + d_log_base_fee_lag1 + is_weekend + is_month_end'
        # If event controls exist in frame, include them in diagnostics spec
        event_cols = [c for c in ['shock_china_ban','shock_otherside_mint','shock_terra_luna','shock_ftx_collapse','shock_usdc_depeg','airdrop_day','outage_day','shock_any'] if c in frame.columns]
        if event_cols:
            base_rhs = base_rhs + ' + ' + ' + '.join(event_cols)
        y_mat, X_mat = dmatrices(f'd_log_base_fee ~ {base_rhs}', data=use, return_type='dataframe')
        res_ecm = OLS(y_mat, X_mat).fit()
        ecm_resid = res_ecm.resid.squeeze()
        adf_res = adfuller(ecm_resid, regression='c', autolag='AIC')
        lb = acorr_ljungbox(ecm_resid, lags=[10], return_df=True)
        diag = {
            'ecm_resid_adf_t': adf_res[0],
            'ecm_resid_adf_p': adf_res[1],
            'ljung_box_stat_lag10': float(lb['lb_stat'].iloc[0]),
            'ljung_box_p_lag10': float(lb['lb_pvalue'].iloc[0])
        }
    except Exception:
        diag = {'ecm_resid_adf_t': np.nan, 'ecm_resid_adf_p': np.nan, 'ljung_box_stat_lag10': np.nan, 'ljung_box_p_lag10': np.nan}
    pd.DataFrame([diag]).to_csv(out_dir / 'ecm_diagnostics.csv', index=False)

    # Differences check: Δ-spec short-run estimate for comparison
    try:
        df['d_log_base_fee'] = df['log_base_fee'].diff()
        df['d_A_t_clean'] = df['A_t_clean'].diff()
        df['d_D_star'] = df['D_star'].diff()
        use = df.dropna(subset=['d_log_base_fee', 'd_A_t_clean'])
        base_rhs = 'd_A_t_clean + d_D_star + is_weekend + is_month_end'
        event_cols = [c for c in ['shock_china_ban','shock_otherside_mint','shock_terra_luna','shock_ftx_collapse','shock_usdc_depeg','airdrop_day','outage_day','shock_any'] if c in df.columns]
        if event_cols:
            base_rhs = base_rhs + ' + ' + ' + '.join(event_cols)
        y_mat, X_mat = dmatrices(f'd_log_base_fee ~ {base_rhs}', data=use, return_type='dataframe')
        model = OLS(y_mat, X_mat)
        n = len(use)
        bw = min(7, max(1, int(4 * (n/100) ** (2/9))))
        res_diff = model.fit(cov_type='HAC', cov_kwds={'maxlags': bw, 'kernel': 'bartlett', 'use_correction': True})
        diff_row = {
            'beta_diff': res_diff.params.get('d_A_t_clean', np.nan),
            'se_diff': res_diff.bse.get('d_A_t_clean', np.nan),
            'p_diff': res_diff.pvalues.get('d_A_t_clean', np.nan),
            'n': n, 'bw': bw
        }
    except Exception:
        diff_row = {'beta_diff': np.nan, 'se_diff': np.nan, 'p_diff': np.nan, 'n': 0, 'bw': np.nan}
    pd.DataFrame([diff_row]).to_csv(out_dir / 'diff_spec_check.csv', index=False)

    # Save LaTeX tables
    save_latex_eg(eg_df, out_dir / 'table_c2_eg_tests.tex')
    save_latex_johansen(joh, out_dir / 'table_c2_johansen.tex')
    save_latex_ecm(ecm_summary, out_dir / 'table_c2_ecm.tex')
    save_latex_ecm_compact_plain(ecm_summary, out_dir / 'table_ecm_main_compact.tex')

    # Print concise console summary
    print('\n=== C2 Summary ===')
    print('Engle–Granger (full): ADF t = %.3f, p = %.3f' % (eg_stat, eg_p))
    if np.isfinite(ecm_summary.get('phi', np.nan)):
        print('ECM: phi = %.3f (p=%.3f), psi = %.3f (p=%.3f), half-life=%.1f days, N=%d' % (
            ecm_summary['phi'], ecm_summary['phi_p'], ecm_summary['psi'], ecm_summary['psi_p'],
            ecm_summary['half_life_days'] if np.isfinite(ecm_summary['half_life_days']) else np.nan,
            ecm_summary['n']
        ))
    else:
        print('No cointegration detected at 5% (full sample); retain Δ-spec as confirmatory.')

    # --- Targeted events robustness: include explicit day dummies ---
    # Build events from sources and merge into df
    try:
        events_df = build_targeted_event_dummies(df['date'])
        df_ev = df.merge(events_df, on='date', how='left')
        for c in ['airdrop_day', 'outage_day']:
            if c in df_ev.columns:
                df_ev[c] = df_ev[c].fillna(0).astype(int)
    except Exception:
        df_ev = df.copy()

    # Candidate event columns present in panel
    candidate_events = [
        'shock_china_ban', 'shock_otherside_mint', 'shock_terra_luna',
        'shock_ftx_collapse', 'shock_usdc_depeg', 'shock_any', 'airdrop_day', 'outage_day'
    ]
    present_events = [c for c in candidate_events if c in df_ev.columns]

    # Re-run EG and ECM with event controls appended to X
    x_full_ev = x_full + present_events
    eg_stat_ev, eg_p_ev, resid_ev = engle_granger(df_ev, y='log_base_fee', xvars=x_full_ev)

    ecm_ev = {
        'phi': np.nan, 'phi_se': np.nan, 'phi_p': np.nan,
        'psi': np.nan, 'psi_se': np.nan, 'psi_p': np.nan,
        'n': 0, 'bw': np.nan, 'half_life_days': np.nan
    }
    if np.isfinite(eg_p_ev) and eg_p_ev < 0.05:
        ecm_ev = estimate_ecm(df_ev, y='log_base_fee', xvars=x_full_ev, resid=resid_ev, event_controls=present_events)

    # Persist robustness outputs
    pd.DataFrame([{'eg_adf_stat': eg_stat_ev, 'eg_adf_p': eg_p_ev}]).to_csv(out_dir / 'eg_tests_with_events.csv', index=False)
    pd.DataFrame([ecm_ev]).to_csv(out_dir / 'ecm_results_with_events.csv', index=False)

    # Render a compact LaTeX comparison table for manuscript
    try:
        def stars(p):
            return '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else ''))

        baseline_phi = ecm_summary['phi']; baseline_phi_se = ecm_summary['phi_se']; baseline_phi_p = ecm_summary['phi_p']
        baseline_psi = ecm_summary['psi']; baseline_psi_se = ecm_summary['psi_se']; baseline_psi_p = ecm_summary['psi_p']
        baseline_n = ecm_summary['n']

        ev_phi = ecm_ev['phi']; ev_phi_se = ecm_ev['phi_se']; ev_phi_p = ecm_ev['phi_p']
        ev_psi = ecm_ev['psi']; ev_psi_se = ecm_ev['psi_se']; ev_psi_p = ecm_ev['psi_p']
        ev_n = ecm_ev['n']

        lines = []
        lines.append('% Auto-generated: ECM with Targeted Event Controls (Robustness)\n')
        lines.append('\\begin{table}[!htbp]\\centering\\small\n')
        lines.append('\\caption{ECM Short-Run Effect with Targeted Event Controls}\\label{tab:c2_ecm_events}\n')
        lines.append('\\begin{tabular}{lcccc}\\toprule\n')
        lines.append(' & $\\phi$ (ECT) & $\\psi$ (d$A_t$) & N & Notes \\\\ \n')
        lines.append('\\midrule\n')
        if np.isfinite(baseline_phi) and np.isfinite(baseline_psi):
            lines.append(f"Baseline (D$^*$ + cal/regime) & {baseline_phi:.3f}{stars(baseline_phi_p)} ({baseline_phi_se:.3f}) & {baseline_psi:.3f}{stars(baseline_psi_p)} ({baseline_psi_se:.3f}) & {baseline_n} & --- \\\\ \n")
        if np.isfinite(ev_phi) and np.isfinite(ev_psi):
            lines.append(f"+ Targeted events (airdrops, outages, shocks) & {ev_phi:.3f}{stars(ev_phi_p)} ({ev_phi_se:.3f}) & {ev_psi:.3f}{stars(ev_psi_p)} ({ev_psi_se:.3f}) & {ev_n} & Adds day dummies \\\\ \n")
        lines.append('\\bottomrule\\end{tabular}\n')
        lines.append('\\begin{minipage}{0.92\\textwidth}\\footnotesize\\vspace{0.3em}\\textit{Note:} Event controls include available day dummies for major exogenous shocks (Otherside NFT mint, Terra/Luna, FTX collapse, USDC depeg), curated airdrop claim days, and L2 outage days. All I(0) controls included in both long-run relation (for ECT) and short-run equation. HAC (Bartlett) SEs with data-driven bandwidth. \\end{minipage}\n')
        lines.append('\\end{table}\n')
        (out_dir / 'table_c2_ecm_events.tex').write_text(''.join(lines))
    except Exception:
        pass


if __name__ == '__main__':
    main()
