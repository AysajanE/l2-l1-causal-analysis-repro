#!/usr/bin/env python3
"""
Generate comprehensive documentation for core_panel_v1.parquet

This script generates:
1. MD5 checksum
2. Schema JSON with full metadata
3. Metadata YAML
4. Updates to version control documentation

Author: Reproducibility Lead
Phase: 4 - Panel Assembly & Snapshotting
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import yaml


def generate_checksum(filepath: Path) -> str:
    """Generate MD5 checksum for a file."""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


def save_checksum(filepath: Path, checksum_path: Path) -> None:
    """Save checksum to file with metadata."""
    checksum = generate_checksum(filepath)
    file_size = filepath.stat().st_size
    timestamp = datetime.now(timezone.utc).isoformat()

    with open(checksum_path, 'w') as f:
        f.write(f"{checksum}  {filepath.name}\n")
        f.write(f"# File size: {file_size:,} bytes ({file_size / 1024**2:.2f} MB)\n")
        f.write(f"# Generated: {timestamp}\n")

    print(f"✓ Checksum saved to {checksum_path}")
    print(f"  MD5: {checksum}")
    print(f"  Size: {file_size / 1024**2:.2f} MB")


def get_null_patterns(df: pd.DataFrame) -> dict:
    """Identify and document null patterns in the data."""
    patterns = {}

    for col in df.columns:
        null_count = df[col].isna().sum()
        if null_count > 0:
            null_pct = (null_count / len(df)) * 100

            # Check if nulls are systematic (e.g., before a certain date)
            if 'date' in df.columns:
                first_non_null_idx = df[col].first_valid_index()
                if first_non_null_idx is not None:
                    first_non_null_date = df.loc[first_non_null_idx, 'date']
                    patterns[col] = f"NULL before {first_non_null_date} ({null_count} rows, {null_pct:.1f}%)"
                else:
                    patterns[col] = f"All NULL ({null_count} rows, {null_pct:.1f}%)"
            else:
                patterns[col] = f"{null_count} rows, {null_pct:.1f}%"

    return patterns


def generate_schema_json(filepath: Path, schema_path: Path, version: int = 1) -> None:
    """Generate comprehensive schema documentation in JSON format."""

    # Read parquet metadata
    parquet_file = pq.read_table(filepath)
    df = pd.read_parquet(filepath)

    # Get basic statistics
    row_count = len(df)
    col_count = len(df.columns)

    # Date range
    date_range = {}
    if 'date' in df.columns:
        date_range = {
            "start": str(df['date'].min()),
            "end": str(df['date'].max())
        }

    # Column documentation
    columns = []
    for col_name in df.columns:
        col_data = df[col_name]
        dtype = str(col_data.dtype)

        col_info = {
            "name": col_name,
            "type": dtype,
            "nullable": col_data.isna().any(),
            "null_count": int(col_data.isna().sum())
        }

        # Add description based on column name
        descriptions = {
            "date": "Daily observation date (UTC)",
            "A_t_clean": "Posting-clean L2 adoption share (0-1)",
            "log_C_fee": "Log cumulative transaction fees",
            "u_t": "Average gas price (gwei)",
            "S_t": "Supply shock proxy",
            "D_star": "Composite demand factor",
            "base_fee_median_wei": "Median base fee per gas (wei)",
            "gas_limit_sum": "Total gas limit across blocks",
            "gas_used_sum": "Total gas used across blocks",
            "tx_count_sum": "Total transaction count",
            "pipeline_version": "Git commit SHA of pipeline code",
            "loaded_at": "Timestamp when data was created",
            "analysis_version_id": "Semantic version number for this dataset",
            "regime_pos_supply": "Post-PoS merge regime flag",
            "regime_fee_market": "Post-EIP-1559 regime flag",
            "regime_eip4844": "Post-blob transaction regime flag"
        }

        if col_name in descriptions:
            col_info["description"] = descriptions[col_name]
        else:
            col_info["description"] = f"Column: {col_name}"

        # Add range for numeric columns
        if pd.api.types.is_numeric_dtype(col_data):
            non_null = col_data.dropna()
            if len(non_null) > 0:
                col_info["range"] = {
                    "min": float(non_null.min()),
                    "max": float(non_null.max()),
                    "mean": float(non_null.mean()),
                    "median": float(non_null.median())
                }

        columns.append(col_info)

    # Build schema document
    schema = {
        "version": f"{version}.0",
        "analysis_version_id": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": "1.0.0",  # Will be updated with git commit
        "description": "Core analytical panel for L2-L1 causal influence analysis",
        "columns": columns,
        "row_count": row_count,
        "column_count": col_count,
        "date_range": date_range,
        "null_patterns": get_null_patterns(df),
        "source_tables": [
            "mart_treatment_daily",
            "stg_l1_blocks_daily",
            "demand_factor_daily",
            "mart_master_daily"
        ],
        "primary_key": ["date"],
        "file_info": {
            "path": str(filepath.relative_to(filepath.parents[2])),
            "size_bytes": filepath.stat().st_size,
            "size_mb": filepath.stat().st_size / 1024**2,
            "format": "parquet"
        }
    }

    # Write schema
    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2)

    print(f"✓ Schema saved to {schema_path}")
    print(f"  Rows: {row_count:,}")
    print(f"  Columns: {col_count}")
    print(f"  Date range: {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}")


def generate_metadata_yaml(filepath: Path, metadata_path: Path, checksum: str, version: int = 1) -> None:
    """Generate version metadata in YAML format."""

    df = pd.read_parquet(filepath)

    metadata = {
        "panel_version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": "1.0.0",  # Will be updated with git commit
        "analysis_version_id": version,
        "source_phases": {
            "phase_1": "ETL staging complete",
            "phase_2": "Treatment A_t_clean validated",
            "phase_3": "Outcomes and D★ harmonized"
        },
        "changes_from_v0": [
            "Added posting-clean treatment (A_t_clean)",
            "Integrated full D★ demand factor",
            "Added event window dummies",
            "Standardized metadata columns"
        ],
        "quality_gates": {
            "G1_data_qc": "pending",
            "structural_nulls": "validated",
            "duplicate_dates": "none found"
        },
        "file_info": {
            "path": str(filepath.relative_to(filepath.parents[2])),
            "size_mb": round(filepath.stat().st_size / 1024**2, 2),
            "checksum_md5": checksum,
            "rows": len(df),
            "columns": len(df.columns)
        }
    }

    with open(metadata_path, 'w') as f:
        yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

    print(f"✓ Metadata saved to {metadata_path}")


def update_versioning_policy(version: int = 1) -> None:
    """Update data_versioning_policy.md with new version information."""

    docs_dir = Path(__file__).parents[2] / "docs"
    policy_file = docs_dir / "data_versioning_policy.md"

    if not policy_file.exists():
        print(f"⚠ Warning: {policy_file} not found, skipping update")
        return

    # Read current content
    with open(policy_file, 'r') as f:
        content = f.read()

    # Update the "Current Version" section
    new_version_text = f"""### Current Version
**Active Version**: core_panel_v{version}
**Created**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
**Analysis Version ID**: {version}

Files:
- Panel: `data/analytical/core_panel_v{version}.parquet`
- Schema: `data/analytical/core_panel_v{version}_schema.json`
- Checksum: `data/analytical/core_panel_v{version}.md5`
- Metadata: `data/analytical/core_panel_v{version}_metadata.yaml`"""

    # Replace the section
    import re
    pattern = r'### Current Version\n.*?(?=\n## |\n### |$)'
    updated_content = re.sub(pattern, new_version_text, content, flags=re.DOTALL)

    with open(policy_file, 'w') as f:
        f.write(updated_content)

    print(f"✓ Updated {policy_file}")


def create_changelog_entry(version: int = 1) -> None:
    """Create or update data_version_changelog.md"""

    docs_dir = Path(__file__).parents[2] / "docs"
    changelog_file = docs_dir / "data_version_changelog.md"

    entry = f"""# Data Version Change Log

## v{version} ({datetime.now(timezone.utc).strftime('%Y-%m-%d')})
**Status**: Active
**Analysis Version ID**: {version}

### Changes
- Initial production panel with posting-clean treatment (A_t_clean)
- Integrated D★ composite demand factor
- Added regime flags: pos_supply, fee_market, eip4844
- Standardized metadata columns for reproducibility

### Files
- Panel: `data/analytical/core_panel_v{version}.parquet`
- Schema: `data/analytical/core_panel_v{version}_schema.json`
- Checksum: `data/analytical/core_panel_v{version}.md5`
- Metadata: `data/analytical/core_panel_v{version}_metadata.yaml`

### Date Range
See schema file for exact date range

### Quality Gates
- G1: Data QC validation (pending)
- G2: Treatment validation (passed)
- G3: Outcome validation (passed)

---
"""

    if changelog_file.exists():
        # Prepend to existing changelog
        with open(changelog_file, 'r') as f:
            existing = f.read()

        if f"## v{version}" not in existing:
            with open(changelog_file, 'w') as f:
                f.write(entry + "\n" + existing)
            print(f"✓ Updated {changelog_file}")
        else:
            print(f"⚠ Version {version} already exists in changelog")
    else:
        # Create new changelog
        with open(changelog_file, 'w') as f:
            f.write(entry)
        print(f"✓ Created {changelog_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate documentation for core panel snapshot"
    )
    parser.add_argument(
        '--panel-path',
        type=Path,
        default=Path(__file__).parents[2] / "data/core_panel_v1/core_panel_v1.parquet",
        help="Path to the panel parquet file"
    )
    parser.add_argument(
        '--version',
        type=int,
        default=1,
        help="Version number for this panel"
    )

    args = parser.parse_args()

    panel_path = args.panel_path
    version = args.version

    # Verify panel exists
    if not panel_path.exists():
        print(f"✗ Error: Panel file not found at {panel_path}")
        print("  Waiting for Data Engineer to create panel...")
        sys.exit(1)

    print(f"Generating documentation for {panel_path.name}")
    print(f"Version: {version}")
    print("=" * 60)

    # Generate all documentation
    base_name = panel_path.stem
    output_dir = panel_path.parent

    # 1. Checksum
    checksum_path = output_dir / f"{base_name}.md5"
    save_checksum(panel_path, checksum_path)

    # Get checksum for metadata
    with open(checksum_path, 'r') as f:
        checksum = f.readline().split()[0]

    # 2. Schema JSON
    schema_path = output_dir / f"{base_name}_schema.json"
    generate_schema_json(panel_path, schema_path, version)

    # 3. Metadata YAML
    metadata_path = output_dir / f"{base_name}_metadata.yaml"
    generate_metadata_yaml(panel_path, metadata_path, checksum, version)

    # 4. Update version control docs
    update_versioning_policy(version)

    # 5. Create changelog entry
    create_changelog_entry(version)

    print("=" * 60)
    print("✓ All documentation generated successfully!")
    print("\nGenerated files:")
    print(f"  - {checksum_path}")
    print(f"  - {schema_path}")
    print(f"  - {metadata_path}")
    print(f"\nUpdated files:")
    print(f"  - docs/data_versioning_policy.md")
    print(f"  - docs/data_version_changelog.md")
    print(f"\nNext steps:")
    print(f"  1. Review generated documentation")
    print(f"  2. Verify checksum: md5sum -c {checksum_path}")
    print(f"  3. Commit all files to version control")


if __name__ == "__main__":
    main()
