#!/usr/bin/env python3
"""Check the converted panel for gas_used columns."""

import pandas as pd
import numpy as np
from pathlib import Path
import pyarrow.parquet as pq

# Set working directory
work_dir = Path(__file__).resolve().parents[2]

# Check the converted panel
panel_path = work_dir / "data/core_panel_v1/core_panel_v1_converted.parquet"

# Read with pyarrow and manually convert
table = pq.read_table(panel_path)

# Convert to pandas
columns_dict = {}
for i, name in enumerate(table.schema.names):
    column = table.column(i)
    if name == 'date':
        columns_dict[name] = pd.to_datetime(column.to_pandas())
    else:
        columns_dict[name] = column.to_pandas()

panel_df = pd.DataFrame(columns_dict)

print("Converted Panel Shape:", panel_df.shape)
print("\nAll columns:")
for col in sorted(panel_df.columns):
    print(f"  - {col}")

# Check for gas columns
gas_cols = [col for col in panel_df.columns if 'gas' in col.lower()]
print(f"\nGas-related columns ({len(gas_cols)}):")
for col in gas_cols:
    print(f"  - {col}: {panel_df[col].dtype}")
    # Sample values
    non_null = panel_df[col].dropna()
    if len(non_null) > 0:
        print(f"    Sample: {non_null.head(3).tolist()}")
        print(f"    Range: [{non_null.min():.2f}, {non_null.max():.2f}]")
        print(f"    Nulls: {panel_df[col].isna().sum()}/{len(panel_df)}")
    else:
        print("    All null")
    print()
