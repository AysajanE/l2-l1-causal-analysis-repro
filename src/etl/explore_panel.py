#!/usr/bin/env python3
"""Explore the core panel data structure."""

import pandas as pd
import numpy as np
from pathlib import Path
import pyarrow.parquet as pq

# Set working directory
work_dir = Path(__file__).resolve().parents[2]

# Load the core panel data - handle special date types
panel_path = work_dir / "data/core_panel_v1/core_panel_v1.parquet"

# First check the schema
parquet_file = pq.ParquetFile(panel_path)
print("Parquet Schema:")
print(parquet_file.schema)
print("\n" + "="*50 + "\n")

# Load with pyarrow and convert
table = pq.read_table(panel_path)
panel_df = table.to_pandas(date_as_object=False)

print("Panel Data Shape:", panel_df.shape)
print("\nPanel Columns:")
for col in panel_df.columns:
    print(f"  - {col}")

print("\nDate Range:")
print(f"Start: {panel_df['date'].min()}")
print(f"End: {panel_df['date'].max()}")

# Check for gas and fee columns
gas_cols = [col for col in panel_df.columns if 'gas' in col.lower()]
fee_cols = [col for col in panel_df.columns if 'fee' in col.lower()]

print("\nGas-related columns:")
for col in gas_cols:
    print(f"  - {col}")

print("\nFee-related columns:")
for col in fee_cols:
    print(f"  - {col}")

# Check sample values for key metrics
print("\nSample values (first 5 rows):")
if 'base_fee_per_gas_median' in panel_df.columns:
    print("base_fee_per_gas_median:", panel_df['base_fee_per_gas_median'].head().tolist())
if 'gas_used_median' in panel_df.columns:
    print("gas_used_median:", panel_df['gas_used_median'].head().tolist())
if 'gas_used_total' in panel_df.columns:
    print("gas_used_total:", panel_df['gas_used_total'].head().tolist())
