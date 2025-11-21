import json
from pathlib import Path

import pandas as pd
import yaml

DATA_DIR = Path("data/core_panel_v1")
SCHEMA_PATH = DATA_DIR / "core_panel_v1_schema.json"
META_PATH = DATA_DIR / "core_panel_v1_metadata.yaml"
PANEL_PATH = DATA_DIR / "core_panel_v1.parquet"


def test_core_panel_exists():
    assert PANEL_PATH.exists(), "core_panel_v1.parquet missing"


def test_core_panel_columns_and_rows():
    with SCHEMA_PATH.open() as f:
        schema = json.load(f)
    expected_cols = [c["name"] for c in schema]

    df = pd.read_parquet(PANEL_PATH)

    # sanity: columns present
    missing = [c for c in expected_cols if c not in df.columns]
    assert not missing, f"Missing columns: {missing}"

    # sanity: row count
    assert len(df) >= 1000, "Core panel unexpectedly small"

    # critical fields should be mostly non-null
    critical = [
        "log_base_fee",
        "u_t",
        "S_t",
        "A_t_clean",
        "D_star",
    ]
    for col in critical:
        null_rate = df[col].isna().mean()
        assert null_rate < 0.05, f"Too many nulls in {col}: {null_rate:.2%}"


def test_core_panel_temporal_coverage():
    meta = yaml.safe_load(META_PATH.read_text())
    df = pd.read_parquet(PANEL_PATH)
    assert str(df["date"].min().date()) == meta["temporal_coverage"]["start_date"], "start_date mismatch"
    assert str(df["date"].max().date()) == meta["temporal_coverage"]["end_date"], "end_date mismatch"
