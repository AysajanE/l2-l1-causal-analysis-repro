.PHONY: env fetch smoke verify clean

env:
	@echo "Creating/Updating conda env from environment.yml"
	conda env update -f environment.yml --prune || conda env create -f environment.yml

fetch:
	@echo "Fetching raw/heavy inputs from Zenodo (v1.0.2) with checksum verification"
	bash scripts/fetch_raw_data.sh

smoke:
	@echo "Running smoke tests"
	pytest -q tests/smoke

verify: smoke
	@echo "✅ Smoke suite passed"

clean:
	rm -rf .pytest_cache
