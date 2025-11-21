# ETL (Extract, Transform, Load)

## Purpose
This directory contains scripts for data extraction, transformation, and loading operations (Phase 1 of the pipeline).

## Responsibilities
- Extract data from Dune Analytics API
- Transform raw data into standardized formats
- Load data into intermediate storage
- Handle data validation and quality checks during ingestion

## Key Modules
- Data extraction from external APIs (Dune, BigQuery)
- Schema validation and type enforcement
- Data normalization and cleaning
- Batch processing and incremental updates

## Integration with Legacy
This directory complements the existing `src/ingest` module:
- `src/ingest`: Legacy data ingestion for historical reconciliation
- `src/etl`: Production ETL pipeline for ongoing data collection

## Expected Outputs
Data written to: `data/raw/` and `data/intermediate/`

## Usage
Typically invoked via:
```bash
make etl
```

## Dependencies
- Dune Analytics API credentials (DUNE_API_KEY)
- BigQuery credentials (GCP_PROJECT_ID, credentials.json)
- Network access to external data sources
