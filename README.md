# L1–L2 Causal Influence Analysis (Reproducibility Package)

Public reproducibility package for a study of how Layer-2 adoption affects Ethereum Layer-1 congestion.

This repository is intentionally narrower than the full research workspace. It packages the minimum public materials needed to inspect the claims, reproduce released outputs, and trace versioned research bundles across outlets.

## What this package contains

- small derived datasets, including the shipped core panel and processed summaries
- key figures and result tables
- fetch scripts for heavier external bundles hosted on Zenodo
- release, checksum, and data-availability documentation

## Release map

- **arXiv (Dec 2025)**: tag `v1.1.0-arxiv` (candidate). Sources live in `releases/arxiv-2025-12/` and reuse the shipped `data/core_panel_v1/` panel.
- **Management Science submission (Oct 2025)**: tag `v1.0.2-ms`. Shares the same data backbone; manuscript lives in the sister outlet repo.

## Quick start

```bash
conda env create -f environment.yml
bash scripts/fetch_raw_data.sh
pytest -q tests/smoke
```

Or, if you prefer pip:

```bash
pip install -r requirements.txt
```

## Reproducibility commands

- `make env`: create or update the local environment
- `make fetch`: download raw / heavy bundles from Zenodo with checksum verification
- `make smoke`: run minimal validation on the shipped package
- `make verify`: alias for the smoke validation flow
- `make reproduce-arxiv`: validate the arXiv bundle
- `make latex-arxiv`: compile the arXiv manuscript bundle when TeX is available

Checksum verification can also be run directly:

```bash
python scripts/verify_checksums.py
```

## Data availability

- Concept DOI (all versions): `10.5281/zenodo.17665906`
- Latest arXiv bundle: `10.5281/zenodo.17832785`
- Prior data-heavy bundle: `10.5281/zenodo.17665980`

See `docs/DATA_AVAILABILITY.md` for the complete inclusion / exclusion plan.

## Why this repo matters

This package signals:

- serious reproducibility discipline around empirical crypto research
- clean separation between public package, heavier data bundles, and outlet-specific manuscript artifacts
- versioned release management rather than one-off paper code dumps

## Citation

```text
Aysajan Eziz. (2025). L1–L2 Causal Influence Analysis (Reproducibility Package). Zenodo. https://doi.org/10.5281/zenodo.17665906
```

## License

- Code: MIT
- Documentation and figures: CC BY 4.0
