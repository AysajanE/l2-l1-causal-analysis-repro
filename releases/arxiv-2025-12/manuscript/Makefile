# Makefile for LaTeX manuscript compilation
# Project A: Do Layer-2s Decongest Ethereum?

# Main document name (without .tex extension)
MAIN = main

# LaTeX compiler
LATEX = pdflatex
BIBTEX = bibtex

# Compiler flags
LATEXFLAGS = -interaction=nonstopmode -halt-on-error

# Target: Default build
all: pdf

# Target: Compile PDF with bibliography
pdf: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex sections/*.tex references.bib figures/*.pdf
	@echo "First LaTeX pass..."
	$(LATEX) $(LATEXFLAGS) $(MAIN).tex
	@echo "Running BibTeX..."
	$(BIBTEX) $(MAIN)
	@echo "Second LaTeX pass..."
	$(LATEX) $(LATEXFLAGS) $(MAIN).tex
	@echo "Third LaTeX pass..."
	$(LATEX) $(LATEXFLAGS) $(MAIN).tex
	@echo "PDF compilation complete: $(MAIN).pdf"

# Target: Quick compile (no bibliography update)
quick:
	@echo "Quick compile (no BibTeX)..."
	$(LATEX) $(LATEXFLAGS) $(MAIN).tex

# Target: Clean auxiliary files
clean:
	@echo "Cleaning auxiliary files..."
	rm -f *.aux *.bbl *.blg *.log *.out *.toc *.lof *.lot *.synctex.gz *.fls *.fdb_latexmk
	rm -f sections/*.aux
	@echo "Clean complete."

# Target: Deep clean (including PDF)
distclean: clean
	@echo "Removing PDF output..."
	rm -f $(MAIN).pdf
	@echo "Deep clean complete."

# Target: View PDF (macOS)
view: $(MAIN).pdf
	open $(MAIN).pdf

# Target: Watch and recompile on changes (requires entr)
# Usage: make watch
watch:
	@echo "Watching for changes... (Ctrl-C to stop)"
	@echo "Requires 'entr' tool: brew install entr"
	ls $(MAIN).tex sections/*.tex references.bib | entr make quick

# Target: Count words in manuscript
wordcount:
	@echo "Approximate word count (excluding LaTeX commands):"
	@detex sections/*.tex | wc -w
	@echo "(Note: This is an approximation)"

# Target: Check for TODO/TBD markers
todos:
	@echo "Searching for TODO/TBD markers:"
	@grep -rn "TBD\|TODO\|Placeholder\|Content to be written" sections/*.tex abstract.tex || echo "No TODOs found!"

# Target: Help
help:
	@echo "Available targets:"
	@echo "  make          - Compile full PDF with bibliography (default)"
	@echo "  make pdf      - Same as 'make'"
	@echo "  make quick    - Quick compile without BibTeX"
	@echo "  make clean    - Remove auxiliary files"
	@echo "  make distclean- Remove all generated files including PDF"
	@echo "  make view     - Open PDF in default viewer (macOS)"
	@echo "  make watch    - Watch for changes and recompile (requires entr)"
	@echo "  make wordcount- Estimate word count"
	@echo "  make todos    - Find TODO/TBD markers"
	@echo "  make help     - Show this help message"

.PHONY: all pdf quick clean distclean view watch wordcount todos help
