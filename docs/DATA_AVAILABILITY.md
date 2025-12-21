# Data Availability and Reproduction Assets

Last updated: 2025-11-20

This document specifies what will be bundled in the public reproducibility packages, what will be hosted on Zenodo, and what must be fetched on demand.

---

## Included in public repos (small, essential)
- Core panel + metadata (all <1 MB total):  
  - `data/core_panel_v1/core_panel_v1.parquet`  
  - `core_panel_v1_converted.parquet`  
  - `core_panel_v1_teview.parquet`  
  - `core_panel_v1_schema.json`, `core_panel_v1_metadata.yaml`, checksums (`.md5`, `.sha256`)  
  - `eth_price_series.parquet`, `eth_price_series_metadata.yaml`
- Processed panels:  
  - `data/processed/master_panel/master_panel_v0.parquet`  
  - `master_panel_v1_with_demand_factor.parquet`  
  - `master_panel_v2_with_d_star_full.parquet`  
  - Preview CSVs and stats YAMLs
- Processed fee/price summaries: `data/processed/gas_weighted_fees/*`, `data/processed/eth_prices/*`
- Key results and tables (all ≤~300 KB):  
  - `results/power/fig_power_post_dencun.{pdf,png}`, `table_i5_power_precision.{csv,tex}`  
  - `results/bsts` CSV/Parquet summary files (not the full model RDS)  
  - `results/its_diagnostics/*`, `results/figures/*`, `results/hourly/hourly_outcome_panel.csv`
- Manuscript figures: `project_A_effects/manuscript/figures/*` (all sub-1 MB)
- Metadata/config: `data/l2_events_registry.yaml`, `data/external/*.csv`

---

## Hosted on Zenodo (referenced from README)
- `results/bsts/bsts_natural_scale_model.rds` (~24 MB) – published in Zenodo release v1.0.1 (DOI: 10.5281/zenodo.17665949)  
- `results/bsts/bsts_natural_scale_draws.parquet` (~4.6 MB) – published in Zenodo release v1.0.1 (DOI: 10.5281/zenodo.17665949)  
- Any other medium/heavy, immutable artifacts the paper cites but that would bloat the Git repo.

---

## Fetch on demand (not redistributed)
- Raw chain data (size/licensing considerations):  
  - `data/blocks/ethereum_blocks.parquet` (~25 MB)  
  - `data/transactions/ethereum_transactions.parquet` (~56 MB)
- Project B upstream collections (licensed/refreshable):  
  - `data/project_B/dune_batches/*` (~26 MB)  
  - `data/nansen/*` (various CSVs)  
- Any additional licensed or embargoed raw sources: fetched via scripts with pinned URLs and SHA256 checks.

Use `scripts/fetch_raw_data.sh` as the entry point; it fetches and verifies hashes for the above raw assets (Zenodo v1.0.2 download links with pinned SHA256).

---

## Checksums and integrity
- Small bundled artifacts keep their existing `.md5`/`.sha256` files in `data/core_panel_v1/`.  
- For fetched assets, `scripts/fetch_raw_data.sh` validates SHA256 against values in the script; update the hashes if sources refresh, and bump the release tag.
- Generated logs that can embed see-your-machine paths (e.g., provenance logs) are intentionally excluded from the public repo.

---

## Citation and provenance
- Record the root source tag (e.g., `v1.0.0-repro`) and commit SHA in each public repo’s `README` and `CITATION.cff`.  
- Reference the Zenodo DOI badge in `README` once minted; cite the concept DOI in the manuscript.
