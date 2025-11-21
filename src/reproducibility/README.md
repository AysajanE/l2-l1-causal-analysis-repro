# Reproducibility Tools

This directory contains scripts and tools for ensuring reproducibility, versioning, and documentation of analytical datasets.

## Scripts

### `generate_panel_docs.py`
**Purpose**: Generate comprehensive documentation for core analytical panels

**Generates**:
- MD5 checksum with metadata
- JSON schema with column specifications
- YAML version metadata
- Updates to versioning policy and changelog

**Usage**:
```bash
python generate_panel_docs.py --panel-path data/core_panel_v1/core_panel_v1.parquet --version 1
```

**Options**:
- `--panel-path`: Path to panel Parquet file (default: `data/core_panel_v1/core_panel_v1.parquet`)
- `--version`: Version number (default: 1)

**Dependencies**:
- pandas
- pyarrow
- pyyaml

### `wait_and_document.sh`
**Purpose**: Monitor for panel creation and auto-generate documentation

**Features**:
- Waits for panel file with configurable timeout
- Automatically triggers documentation generation
- Validates completion and reports artifacts

**Usage**:
```bash
./wait_and_document.sh
```

**Configuration** (edit script):
- `WAIT_INTERVAL`: Check interval in seconds (default: 5)
- `MAX_WAIT`: Maximum wait time in seconds (default: 600)

## Integration with Makefile

These tools are integrated into the main Makefile:

```bash
# Run panel assembly with auto-documentation
make panel

# Generate documentation only (panel must exist)
make panel-docs

# Verify panel checksum
make panel-verify
```

## Workflow

### Automatic (Recommended)
1. Start monitoring: `./src/reproducibility/wait_and_document.sh`
2. Data Engineer creates panel
3. Documentation auto-generates

### Manual
1. Data Engineer creates panel
2. Run: `python src/reproducibility/generate_panel_docs.py --version 1`
3. Verify: `make panel-verify`

### Via Makefile
1. Data Engineer creates panel
2. Run: `make panel-docs`
3. Verify: `make panel-verify`

## Generated Artifacts

For `core_panel_v1.parquet`, generates:

```
data/analytical/
├── core_panel_v1.md5              # Checksum with metadata
├── core_panel_v1_schema.json      # Full schema documentation
└── core_panel_v1_metadata.yaml    # Version metadata

docs/
├── data_version_changelog.md      # Version history
└── data_versioning_policy.md      # Updated current version
```

## Verification

### Checksum (macOS)
```bash
md5 data/core_panel_v1/core_panel_v1.parquet
# Compare with first line in .md5 file
```

### Checksum (Linux)
```bash
md5sum -c data/core_panel_v1/core_panel_v1.md5
```

### Schema Validation
```python
import json
import pandas as pd

with open('data/core_panel_v1/core_panel_v1_schema.json') as f:
    schema = json.load(f)

df = pd.read_parquet('data/core_panel_v1/core_panel_v1.parquet')

# Validate
assert {col['name'] for col in schema['columns']} == set(df.columns)
assert len(df) == schema['row_count']
```

## Versioning Policy

See `docs/data_versioning_policy.md` for:
- When to increment version numbers
- Required metadata columns
- Schema documentation standards
- Snapshot creation workflow

## Troubleshooting

**Q: Script fails with "Panel file not found"**
A: Ensure Data Engineer has created the panel file first

**Q: Checksum verification fails**
A: File may be corrupted - restore from backup or regenerate

**Q: Schema generation error**
A: Check that PyArrow can read the Parquet file correctly

**Q: Permission denied on scripts**
A: Run `chmod +x *.sh` and `chmod +x *.py`

## Contact

**Reproducibility Lead**: Owns this infrastructure
**Data Engineer**: Creates panel files
**QA Lead**: Uses artifacts for validation

See `docs/RACI_matrix.md` for responsibilities.
