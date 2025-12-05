# Project A Manuscript: Do Layer-2s Decongest Ethereum?

## Overview

This directory contains the LaTeX source for the manuscript **"Do Layer-2s Decongest Ethereum? A Regime-Aware Causal Study of L2 Adoption's Total Effect on L1 Congestion (2021–2024)"**.

**Key Documentation:**
- **Figure/Table Registry:** [`docs/manuscript/figure_table_registry.md`](../../docs/manuscript/figure_table_registry.md) - Complete registry of all 7 tables and 10 figures
- **Integration Guide:** [`docs/manuscript/integration_guide.md`](../../docs/manuscript/integration_guide.md) - Workflow for integrating analysis outputs into manuscript

## Structure

```
manuscript/
├── main.tex                 # Main LaTeX file
├── sections/                # Individual section files
│   ├── abstract.tex
│   ├── 01_introduction.tex
│   ├── 02_literature.tex
│   ├── 03_methodology.tex
│   ├── 04_results.tex
│   ├── 05_discussion.tex
│   ├── 06_conclusion.tex
│   ├── 07_data_availability.tex
│   └── appendix_technical.tex
├── figures/                 # Figure files (PDF/PNG) - 10 figures expected
│   ├── fig_01_timeseries_regimes.pdf
│   ├── fig_02_scatterplot_matrix.pdf
│   └── ... (see figure_table_registry.md)
├── tables/                  # Table LaTeX files - 7 tables expected
│   ├── table_01_descriptive_stats.tex
│   ├── table_03_its_main_effects.tex
│   └── ... (see figure_table_registry.md)
├── references.bib           # BibTeX bibliography
├── Makefile                 # Build automation
└── README.md                # This file
```

## Compilation

### Prerequisites

- LaTeX distribution (TeX Live, MiKTeX, or MacTeX)
- BibTeX for bibliography management
- Required LaTeX packages (see `main.tex` preamble)

### Using Make

```bash
# Compile the full manuscript (LaTeX + BibTeX + LaTeX x2)
make

# Clean auxiliary files
make clean

# Clean all generated files including PDF
make distclean
```

### Manual Compilation

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

## Sections

### Current Status

All section files contain:
- **Structure**: Subsections matching the manuscript outline
- **Placeholders**: `[Content to be written: ...]` markers for content
- **Tables/Figures**: Placeholder environments with proper captions and labels
- **Math**: Properly formatted equations and notation

### Writing Workflow

1. Navigate to the appropriate section file (e.g., `sections/03_methodology.tex`)
2. Replace placeholder text with actual content
3. Add figures to `figures/` directory (use PDF format for vector graphics)
4. Update table placeholders with actual results (`[TBD]` entries)
5. Add references to `references.bib` and cite using `\cite{key}`
6. Compile to check formatting

## Figures and Tables

**See [`docs/manuscript/figure_table_registry.md`](../../docs/manuscript/figure_table_registry.md) for complete specifications.**

### Figures (10 total)

- **Storage:** `figures/` directory
- **Format:** PDF for vector graphics (plots, diagrams), PNG at 300 DPI for raster
- **Naming:** `fig_[NN]_[descriptive_name].pdf` (e.g., `fig_01_timeseries_regimes.pdf`)
- **Reference:** Use `\ref{fig:label}` in text (e.g., `Figure~\ref{fig:timeseries_regimes}`)

**Key Figures:**
1. Regime-Aware Time Series Panel (Section 4.1)
2. Scatterplot Matrix with Regime Coloring (Section 4.1)
3. ACF/PACF Diagnostic Plots (Appendix)
4. PCA Scree Plot (Appendix)
5. Elasticity Forest Plot (Section 4.2)
6. Regime Interaction Coefficients (Section 4.3)
7. Event Study Lead/Lag Path (Section 4.4)
8. BSTS Counterfactual (Section 4.5)
9. BSTS Diagnostics (Appendix)
10. Sensitivity Tornado Plot (Section 4.7)

### Tables (7 total)

- **Storage:** `tables/` directory (LaTeX `.tex` files)
- **Naming:** `table_[NN]_[descriptive_name].tex` (e.g., `table_03_its_main_effects.tex`)
- **Inclusion:** Use `\input{tables/table_name.tex}` within `\begin{table}...\end{table}` environment
- **Style:** `booktabs` package (`\toprule`, `\midrule`, `\bottomrule`); no vertical lines

**Key Tables:**
1. Descriptive Statistics by Regime (Section 4.1)
2. PCA Demand Factor Loadings (Section 4.1)
3. Main Total Effect Estimates - ITS (Section 4.2)
4. Regime Heterogeneity Tests (Section 4.3)
5. BSTS Counterfactual Effects (Section 4.5)
6. RDiT Estimates at Protocol Boundaries (Section 4.6)
7. Robustness and Sensitivity Grid (Section 4.7)

## Bibliography

### Adding References

Edit `references.bib`:

```bibtex
@article{author2024,
  author = {Last, First and Last, Second},
  title = {{Title of the Article}},
  journal = {Journal Name},
  volume = {XX},
  number = {X},
  pages = {XXX--XXX},
  year = {2024},
  doi = {10.XXXX/XXXXX}
}
```

### Citation Styles

- Cite using `\cite{key}` for (Author, Year)
- Use `\citet{key}` for Author (Year) [requires natbib]
- Current style: `apalike` (can be changed in `main.tex`)

## Customization

### Author Information

Update in `main.tex`:

```latex
\title{Your Title}
\author{
    Your Name\thanks{Affiliation and contact.}\\
    \textit{Your Institution}
}
```

### Formatting

- Line spacing: Currently `\onehalfspacing` (change to `\doublespacing` or `\singlespacing` as needed)
- Margins: Currently 1 inch all around (change in `\usepackage[margin=1in]{geometry}`)
- Font: Default Computer Modern (change to `\usepackage{times}` for Times New Roman)

## Version Control

- Track all `.tex`, `.bib`, and `.md` files
- **Do not** track generated files: `.aux`, `.bbl`, `.blg`, `.log`, `.out`, `.toc`, `.pdf` (optional)
- Consider a `.gitignore` for LaTeX:

```
*.aux
*.bbl
*.blg
*.log
*.out
*.toc
*.lof
*.lot
*.synctex.gz
*.fls
*.fdb_latexmk
```

## Notes

- **Placeholders**: All `[TBD]` and `[Content to be written: ...]` markers must be replaced before submission
- **Cross-references**: Use `\label{}` and `\ref{}` for internal references (sections, figures, tables, equations)
- **Hyperlinks**: Enabled via `hyperref` package; links are colored blue
- **TODO tracking**: Search for `[TBD]` or `[Placeholder]` to find incomplete sections

## Manuscript Integration Workflow

This manuscript is part of a larger analysis pipeline. For details on how analysis outputs flow into the manuscript:

1. **Figure/Table Registry:** [`docs/manuscript/figure_table_registry.md`](../../docs/manuscript/figure_table_registry.md)
   - Complete specifications for all 7 tables and 10 figures
   - Source scripts, responsible team members, status tracking
   - Naming conventions, format requirements, integration timeline

2. **Integration Guide:** [`docs/manuscript/integration_guide.md`](../../docs/manuscript/integration_guide.md)
   - Pipeline stages: Data → Analysis → Manuscript
   - Phase-by-phase integration workflow (Phases 5-12)
   - LaTeX compilation best practices
   - Figure/table inclusion patterns
   - Bibliography management
   - Submission preparation checklist
   - Troubleshooting common issues

### Quick Start for Contributors

**To add a new figure:**
1. Generate figure from analysis script (save to `results/figures/`)
2. Copy to `manuscript/figures/` with proper naming (`fig_NN_name.pdf`)
3. Include in appropriate section file using `\includegraphics{}`
4. Add entry to figure registry with status update

**To add a new table:**
1. Generate LaTeX table from analysis (save to `results/tables/`)
2. Copy to `manuscript/tables/` with proper naming (`table_NN_name.tex`)
3. Include in appropriate section using `\input{tables/...}` within `\begin{table}...\end{table}`
4. Add entry to table registry with status update

**To add a citation:**
1. Add BibTeX entry to `references.bib`
2. Cite in text using `\cite{key}` or `\citet{key}`
3. Recompile: `pdflatex → bibtex → pdflatex → pdflatex`

## Support

For issues with LaTeX compilation:
1. Check log file (`main.log`) for error messages
2. Ensure all required packages are installed
3. Verify all `\input{}` files exist and paths are correct
4. Confirm all `\includegraphics{}` references point to existing files
5. Consult troubleshooting section in integration guide

For questions about manuscript integration:
- **Manuscript Editor:** Primary contact for LaTeX and integration issues
- **Visualization Lead:** Figure quality and formatting
- **Causal/Bayesian Modeler:** Table specifications and content
- **See:** `docs/manuscript/integration_guide.md` for team coordination details

## License

[Specify manuscript license, e.g., CC-BY 4.0 for preprints]
