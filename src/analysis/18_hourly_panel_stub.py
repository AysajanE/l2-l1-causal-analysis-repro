#!/usr/bin/env python3
"""
Hourly outcome panel (stub)
--------------------------

Construct an hourly outcome panel from block-level data to support
future hourly ECM/LP around blob-fee innovations. This script does not
include hourly adoption (A_t) due to data unavailability in the current
freeze, but establishes the reproducible outcome/instrument scaffold.

Outputs:
  - results/hourly/hourly_outcome_panel.csv (date_hour, base_fee_gwei_median)
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd


def main():
    blocks = Path('data/blocks/ethereum_blocks.parquet')
    outdir = Path('results/hourly')
    outdir.mkdir(parents=True, exist_ok=True)
    if not blocks.exists():
        print('No blocks parquet found; skipping.')
        return
    import pyarrow.parquet as pq
    t = pq.read_table(blocks)
    df = t.to_pandas()
    # Expect columns: timestamp, base_fee_per_gas (wei)
    # Normalize timestamp to UTC datetime
    if 'timestamp' not in df.columns:
        print('Missing timestamp column; skipping.')
        return
    ts = pd.to_datetime(df['timestamp'], unit='s', errors='coerce') if pd.api.types.is_integer_dtype(df['timestamp']) else pd.to_datetime(df['timestamp'], errors='coerce')
    df['ts'] = ts.dt.floor('H')
    # Base fee per gas in Gwei
    if 'base_fee_per_gas' in df.columns:
        base = pd.to_numeric(df['base_fee_per_gas'], errors='coerce') / 1e9
    elif 'base_fee_gwei' in df.columns:
        base = pd.to_numeric(df['base_fee_gwei'], errors='coerce')
    else:
        print('Missing base fee column; expected base_fee_per_gas or base_fee_gwei; skipping.')
        return
    df['base_fee_gwei'] = base
    hourly = df.groupby('ts', as_index=False)['base_fee_gwei'].median().rename(columns={'ts': 'date_hour', 'base_fee_gwei': 'base_fee_gwei_median'})
    hourly.to_csv(outdir / 'hourly_outcome_panel.csv', index=False)
    print('Saved', outdir / 'hourly_outcome_panel.csv')


if __name__ == '__main__':
    main()

