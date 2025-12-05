.PHONY: env fetch smoke verify reproduce-arxiv latex-arxiv clean

ARXIV_DIR := releases/arxiv-2025-12/manuscript

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

reproduce-arxiv: smoke
	@test -d $(ARXIV_DIR) || (echo "Missing $(ARXIV_DIR). Did you clone with submodules or fetch the release bundle?" && exit 1)
	@test -f $(ARXIV_DIR)/main.tex || (echo "Missing arXiv LaTeX sources under $(ARXIV_DIR)" && exit 1)
	@echo "✅ arXiv bundle present (core panel + LaTeX sources)"

latex-arxiv:
	@echo "Building arXiv manuscript PDF (requires latexmk/pdflatex)..."
	cd $(ARXIV_DIR) && (latexmk -pdf main.tex || (pdflatex main && bibtex main && pdflatex main && pdflatex main))
	@echo "✅ arXiv manuscript compiled"

clean:
	rm -rf .pytest_cache
