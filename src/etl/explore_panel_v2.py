#!/usr/bin/env python3
"""Explore the core panel data structure."""

import pandas as pd
import numpy as np
from pathlib import Path
import pyarrow.parquet as pq
import pyarrow as pa

# Set working directory
work_dir = Path("/Users/aeziz-local/Research/Projects-05-Ethereum Blockchain Economic Analysis/Causal Influence of L2 Scaling Solutions on Ethereum L1 Mainnet Congestion/L1-L2-causal-influence-analysis/wt/analysis-r")

# Load the core panel data - handle special date types
panel_path = work_dir / "data/core_panel_v1/core_panel_v1.parquet"

# Read with pyarrow and manually convert
table = pq.read_table(panel_path)

# Convert to pandas, handling the date column specially
columns_dict = {}
for i, name in enumerate(table.schema.names):
    column = table.column(i)
    if name == 'date':
        # Date is already in a readable format, just convert to datetime
        columns_dict[name] = pd.to_datetime(column.to_pandas())
    else:
        columns_dict[name] = column.to_pandas()

panel_df = pd.DataFrame(columns_dict)

print("Panel Data Shape:", panel_df.shape)
print("\nPanel Columns:")
for col in panel_df.columns:
    print(f"  - {col}: {panel_df[col].dtype}")

print("\nDate Range:")
print(f"Start: {panel_df['date'].min()}")
print(f"End: {panel_df['date'].max()}")

# Check for gas and fee columns
gas_cols = [col for col in panel_df.columns if 'gas' in col.lower()]
fee_cols = [col for col in panel_df.columns if 'fee' in col.lower() or 'base_fee' in col.lower()]

print("\nGas-related columns:")
for col in gas_cols:
    print(f"  - {col}")

print("\nFee-related columns:")
for col in fee_cols:
    print(f"  - {col}")

# Check sample values for key metrics
print("\nSample values (first 5 rows):")
for col in ['date', 'log_base_fee', 'base_fee_median_gwei', 'u_t', 'A_t_clean', 'D_star']:
    if col in panel_df.columns:
        print(f"{col}: {panel_df[col].head().tolist()}")

# Check for null values in fee columns
print("\nNull counts in fee columns:")
for col in fee_cols:
    null_count = panel_df[col].isna().sum()
    print(f"  {col}: {null_count} nulls ({100*null_count/len(panel_df):.1f}%)")