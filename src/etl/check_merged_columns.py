#!/usr/bin/env python3
"""Check merged columns."""

import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

work_dir = Path("/Users/aeziz-local/Research/Projects-05-Ethereum Blockchain Economic Analysis/Causal Influence of L2 Scaling Solutions on Ethereum L1 Mainnet Congestion/L1-L2-causal-influence-analysis/wt/analysis-r")

# Load converted panel
panel_path = work_dir / "data/core_panel_v1/core_panel_v1_converted.parquet"
table = pq.read_table(panel_path)
columns_dict = {}
for i, name in enumerate(table.schema.names):
    column = table.column(i)
    if name == 'date':
        columns_dict[name] = pd.to_datetime(column.to_pandas())
    else:
        columns_dict[name] = column.to_pandas()
panel_df = pd.DataFrame(columns_dict)

# Load ETH prices
eth_prices = pd.read_parquet(work_dir / "data/analytical/eth_price_series.parquet")

print("Panel columns with 'eth' or 'price':")
for col in panel_df.columns:
    if 'eth' in col.lower() or 'price' in col.lower():
        print(f"  - {col}")

print("\nETH price columns:")
for col in eth_prices.columns:
    print(f"  - {col}")

# Test merge
df = panel_df.merge(eth_prices, on='date', how='left', suffixes=('', '_price'))
print("\nColumns after merge with 'eth' or 'price':")
for col in df.columns:
    if 'eth' in col.lower() or 'price' in col.lower():
        print(f"  - {col}")