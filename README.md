# L1–L2 Causal Influence Analysis (Reproducibility Package)

This repository contains the minimal, outlet-agnostic materials to reproduce the main results of the study on how Layer-2 scaling affects Ethereum Layer-1 congestion. Outlet-specific bundles are tracked via Git tags/releases.

## Outlet map
- **arXiv (Dec 2025)**: tag `v1.1.0-arxiv` (candidate). Sources live in `releases/arxiv-2025-12/` (full LaTeX + figures) and reuse the shipped `data/core_panel_v1/` panel.
- **Management Science submission (Oct 2025)**: tag `v1.0.2-ms` (existing). Shares the same data; manuscript itself is in the sister MS outlet repo.

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
- Latest version (arXiv bundle): v1.1.1-arxiv — 10.5281/zenodo.17832785 (includes the arXiv LaTeX bundle and the shipped core panel; points to the heavy assets below).
- Prior data-heavy bundle: v1.0.2 — 10.5281/zenodo.17665980 (raw blocks/tx, Dune/Nansen bundles, BSTS model objects, `core_panel_v1.parquet`).
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
- `make reproduce-arxiv` – validate arXiv bundle (smoke tests + LaTeX presence)
- `make latex-arxiv` – compile the arXiv manuscript from `releases/arxiv-2025-12/manuscript` (requires TeX toolchain)

## Tests
`pytest -q tests/smoke`

## Checksum verification
`python scripts/verify_checksums.py`
