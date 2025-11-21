# L1–L2 Causal Influence Analysis (Reproducibility Package)

This repository contains the minimal, outlet-agnostic materials to reproduce the main results of the study on how Layer-2 scaling affects Ethereum Layer-1 congestion.

## What’s included
- Small derived datasets (core panel, processed master panels, gas-weighted fee summaries, ETH prices).
- Key figures and result tables for the paper.
- Fetch script wired to Zenodo v1.0.2 for heavier/raw assets.
- Data and release documentation.

## Quick start
```bash
# 1) Create environment (example; adjust as needed)
conda env create -f environment.yml  # or: pip install -r requirements.txt

# 2) Fetch raw/heavy inputs from Zenodo (with checksum verification)
bash scripts/fetch_raw_data.sh

# 3) Run your analysis/figures pipeline (if provided) or inspect results in results/
```

## Data availability
- Concept DOI (all versions): 10.5281/zenodo.17665906
- Latest version (v1.0.2): 10.5281/zenodo.17665980
  - Contains: `core_panel_v1.parquet`, BSTS artifacts, raw chain parquet files, Dune batches bundle, Nansen bundle.
- See `docs/DATA_AVAILABILITY.md` for the full inclusion/exclusion plan.

## Citation
If you use this package, please cite the concept DOI:
```
Aysajan Eziz. (2025). L1–L2 Causal Influence Analysis (Reproducibility Package). Zenodo. https://doi.org/10.5281/zenodo.17665906
```

## License
- Code: MIT
- Documentation & figures: CC BY 4.0

## Run orchestration
- `make env`   – create/update conda environment
- `make fetch` – download raw/heavy bundles from Zenodo v1.0.2 (with checksums)
- `make smoke` – run minimal smoke tests (core panel shape/columns and key result files)
- `make verify` – same as smoke alias

## Tests
`pytest -q tests/smoke`

## Checksum verification
`python scripts/verify_checksums.py`
