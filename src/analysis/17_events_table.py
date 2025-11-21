#!/usr/bin/env python3
"""
Generate an appendix table listing targeted events used as controls.

Parses data/l2_events_registry.yaml and compiles a simple table with
event name, date, category, and chain.

Outputs:
  - results/events/table_event_list.tex
"""

from __future__ import annotations

from pathlib import Path
import yaml
import pandas as pd

REG = Path('data/l2_events_registry.yaml')


def collect() -> pd.DataFrame:
    recs = []
    if not REG.exists():
        return pd.DataFrame(columns=['Category', 'Event', 'Date', 'Chains'])
    with open(REG, 'r') as f:
        reg = yaml.safe_load(f)

    def add_section(sec: str, cat: str):
        sec_dict = reg.get(sec, {}) or {}
        for k, v in sec_dict.items():
            recs.append({
                'Category': cat,
                'Event': k,
                'Date': v.get('date', ''),
                'Chains': ','.join(v.get('chains', []) or [])
            })

    add_section('major_airdrops', 'Airdrop')
    add_section('major_upgrades', 'Upgrade')
    add_section('major_campaigns', 'Campaign')
    add_section('l2_mainnet_launches', 'Launch')
    add_section('protocol_events', 'Protocol')
    df = pd.DataFrame(recs)
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date.astype(str)
    return df


def render_tex(df: pd.DataFrame, out: Path):
    lines = []
    lines.append('% Auto-generated: Targeted events list for appendix\n')
    lines.append('\\begin{table}[!htbp]\\centering\\small\n')
    lines.append('\\caption{Curated Event List for Targeted Day Dummies}\\label{tab:targeted_events}\n')
    lines.append('\\begin{tabular}{llll}\\toprule\n')
    lines.append('Category & Event & Date & Chains \\\\ \n')
    lines.append('\\midrule\n')
    for _, r in df.iterrows():
        lines.append(f"{r['Category']} & {r['Event']} & {r['Date']} & {r['Chains']} \\\\ \n")
    lines.append('\\bottomrule\\end{tabular}\n')
    lines.append('\\end{table}\n')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(''.join(lines))


def main():
    df = collect()
    out = Path('results/events/table_event_list.tex')
    render_tex(df, out)
    print('Saved', out)


if __name__ == '__main__':
    main()

