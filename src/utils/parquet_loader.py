"""
Utility to load parquet files with special date handling for BigQuery exports.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta


def load_parquet_with_date_handling(file_path):
    """
    Load a parquet file with special handling for date32/dbdate types.

    Parameters
    ----------
    file_path : str or Path
        Path to the parquet file

    Returns
    -------
    pd.DataFrame
        Loaded dataframe with dates properly converted
    """
    # Read the parquet file structure
    parquet_file = pq.ParquetFile(file_path)

    # Get metadata
    schema = parquet_file.schema_arrow

    # Process column by column
    data = {}

    for i in range(len(schema)):
        field = schema[i]
        col_name = field.name

        # Read column
        col_data = parquet_file.read([col_name]).column(0)

        # Handle date types specially
        if pa.types.is_date(field.type) or 'date' in str(field.type).lower():
            # Convert to Python list first
            col_values = col_data.to_pylist()

            # Convert to pandas datetime
            if col_values and col_values[0] is not None:
                # These are already date objects from Arrow
                data[col_name] = pd.to_datetime(col_values)
            else:
                data[col_name] = col_values
        else:
            # Regular column - convert to Python list
            data[col_name] = col_data.to_pylist()

    # Create DataFrame
    df = pd.DataFrame(data)

    return df


def load_core_panel_v1():
    """
    Load the core_panel_v1.parquet file specifically.

    Returns
    -------
    pd.DataFrame
        Core panel dataframe with all columns properly typed
    """
    repo_root = Path(__file__).resolve().parents[2]
    file_path = repo_root / "data/core_panel_v1/core_panel_v1.parquet"

    # Load the data
    df = load_parquet_with_date_handling(file_path)

    # Ensure specific columns are in the right format
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])

    # Convert boolean columns
    bool_cols = [col for col in df.columns if df[col].dtype == 'object' and
                 all(pd.isna(v) or v in [True, False] for v in df[col].dropna().unique())]
    for col in bool_cols:
        df[col] = df[col].astype('bool')

    # Convert integer columns
    int_cols = ['year', 'month', 'regime_post_london', 'regime_post_merge',
                'regime_post_dencun', 'weekday', 'is_weekend', 'is_month_end']
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # Convert float columns
    float_cols = ['log_base_fee', 'base_fee_median_gwei', 'u_t', 'S_t',
                  'A_t_clean', 'D_star', 'D_star_original', 'eth_return_1d_log',
                  'cex_volume_log']
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


if __name__ == "__main__":
    # Test the loader
    df = load_core_panel_v1()
    print("Data loaded successfully!")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"A_t_clean range: [{df['A_t_clean'].min():.4f}, {df['A_t_clean'].max():.4f}]")
