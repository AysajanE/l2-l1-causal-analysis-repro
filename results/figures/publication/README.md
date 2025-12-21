# Publication-Ready Figures Directory
## L1-L2 Causal Influence Analysis

**Purpose:** Centralized repository of all manuscript figures in publication-ready formats
**Created:** 2025-10-11 (Phase 12: Reproducibility & Release Packaging)
**Maintainer:** Visualization Lead
**Status:** ✅ READY FOR JOURNAL SUBMISSION

---

## Directory Contents

This directory contains all 10 figures for the manuscript "Do Layer-2s Decongest Ethereum? A Regime-Aware Causal Study" in multiple formats optimized for different use cases.

### Figure Inventory

| Figure | Title | Formats Available | Primary Format |
|--------|-------|-------------------|----------------|
| Figure 1 | DAG - Causal Structure | PDF, TEX | PDF (vector) |
| Figure 2 | Time Series Panel | PDF, PNG (300 DPI) | PDF (vector) |
| Figure 3 | Treatment Support | PDF, PNG (300 DPI) | PDF (vector) |
| Figure 4 | Seasonality Patterns | PDF, PNG (300 DPI) | PDF (vector) |
| Figure 5 | Correlation Structure | PDF, PNG (300 DPI) | PDF (vector) |
| Figure 6 | Demand Factor PCA | PDF, PNG (300 DPI) | PDF (vector) |
| Figure 7 | Residual Diagnostics | PDF, PNG (300 DPI) | PDF (vector) |
| Figure 8 | Event Study | PDF, PNG (300 DPI) | PDF (vector) |
| Figure 9 | BSTS Counterfactual | PDF, PNG, SVG | PDF (vector) |
| Figure 10 | Robustness Tornado | PDF, PNG, SVG | PDF (vector) |

**Total Files:** 22 (10 PDF + 9 PNG + 2 SVG + 1 TEX)

---

## File Naming Convention

All files follow consistent naming:

```
fig[NN]_[descriptive_name].[ext]
```

Where:
- `[NN]` = Two-digit figure number (01-10)
- `[descriptive_name]` = Lowercase with underscores, describes content
- `[ext]` = File extension (pdf, png, svg, tex)

**Examples:**
- `fig01_dag_causal_structure.pdf`
- `fig09_bsts_counterfactual.png`
- `fig10_robustness_tornado.svg`

---

## Format Guidelines

### PDF (Primary Publication Format)

**Purpose:** Journal submission, print publication, LaTeX manuscripts
**Properties:**
- Vector graphics (infinite resolution)
- Small file sizes (30-80 KB typical)
- Professional typography
- Suitable for scaling to any size

**Usage in LaTeX:**
```latex
\begin{figure}[htbp]
  \centering
  \includegraphics[width=\textwidth]{figures/fig01_dag_causal_structure.pdf}
  \caption{See captions.md for full caption text}
  \label{fig:dag_causal_structure}
\end{figure}
```

### PNG (Presentation & Web Format)

**Purpose:** Presentations, web display, non-LaTeX documents
**Properties:**
- Raster graphics at 300 DPI (print quality)
- Larger file sizes (200-600 KB typical)
- Universally compatible
- Suitable for PowerPoint, Google Slides, Word

**Resolution Verified:**
- All PNG files at 300 DPI or equivalent
- Suitable for printing at journal column width
- No pixelation at standard viewing sizes

### SVG (Editable Vector Format)

**Purpose:** Web display, editing, interactive visualizations
**Availability:** Figures 9 and 10 only
**Properties:**
- Editable vector graphics
- XML-based format
- Suitable for web embedding
- Can be edited in Inkscape, Illustrator, etc.

### TEX (LaTeX Source)

**Purpose:** Reproducible editing of DAG figure
**Availability:** Figure 1 only
**Properties:**
- TikZ/PGF source code
- Fully reproducible
- Can be modified for revisions
- Requires LaTeX with TikZ package

---

## Quality Assurance

All figures in this directory have been verified for:

### Technical Quality
- ✅ Resolution: 300 DPI minimum for rasters, vector for PDFs
- ✅ File integrity: All files open correctly without errors
- ✅ Color depth: 8-bit RGBA for rasters, full color for vectors
- ✅ Aspect ratios: Appropriate for journal layouts

### Content Quality
- ✅ Regime boundaries: Correctly dated (London, Merge, Dencun)
- ✅ Axis labels: Present with units specified
- ✅ Legends: Positioned non-overlapping
- ✅ Typography: Readable at journal column width (3.5-7.5 inches)
- ✅ Statistical annotations: Accurate and clear

### Consistency
- ✅ Regime colors: Consistent across all time-series figures
  - Pre-London: Light gray (#E8E8E8)
  - London-Merge: Light blue (#B3D9FF)
  - Merge-Dencun: Light green (#B3FFB3)
  - Post-Dencun: Light orange (#FFD9B3)
- ✅ Font families: Sans-serif throughout
- ✅ Font sizes: 9-12pt effective range
- ✅ Line styles: Solid/dashed consistently applied

### Accessibility
- ✅ Color-blind friendly palettes (Okabe-Ito for categorical)
- ✅ Sufficient contrast for print
- ✅ Alternative encodings (patterns, labels) where needed
- ✅ Clear legends and annotations

---

## Captions

Full captions for all figures are provided in:

**File:** `../captions.md`

Each caption includes:
- Descriptive title
- Full caption text (manuscript-ready)
- Technical notes and data sources
- LaTeX label for cross-referencing
- File location references

Captions can be exported to LaTeX using:
```python
from src.visualization.captions import export_all_captions
export_all_captions('figures_captions.tex', format='latex')
```

---

## Source and Reproduction

All figures in this directory are copies/exports from original analysis outputs.

### Original Source Locations

| Figure | Original Location | Generation Script |
|--------|------------------|-------------------|
| Fig 1 | `project_A_effects/manuscript/figures/` | Manual (TikZ) |
| Figs 2-7 | `figures/phase5_eda/` | `src/visualization/generate_all_phase5.py` |
| Fig 8 | `figures/phase7/` | `src/visualization/generate_phase7_figure8.py` |
| Fig 9 | `results/figures/` | `src/visualization/figure9_bsts_counterfactual.py` |
| Fig 10 | `results/figures/` | `src/visualization/fig10_robustness_tornado.py` |

### Regeneration

To regenerate all figures from source data:

```bash
# From project root
cd /path/to/L1-L2-causal-influence-analysis/wt/release

# Regenerate Phase 5 EDA figures (Figures 2-7)
python src/visualization/generate_all_phase5.py

# Regenerate Phase 7 Event Study (Figure 8)
python src/visualization/generate_phase7_figure8.py

# Regenerate Phase 8 BSTS (Figure 9)
Rscript src/analysis/08_bsts.R  # Generate data
python src/visualization/figure9_bsts_counterfactual.py  # Create figure

# Regenerate Phase 10 Robustness (Figure 10)
python src/visualization/fig10_robustness_tornado.py

# Copy updated figures to publication directory
make organize-figures  # (if implemented in Makefile)
```

**Note:** Figure regeneration requires:
- Input data: `data/core_panel_v1/core_panel_v1.parquet`
- Analysis results: `results/tables/`, `results/bsts/`
- Python 3.9+ with dependencies from `requirements.txt`
- R 4.0+ with packages from `renv.lock` (for Figure 9 only)

---

## Journal Submission Checklist

When preparing figures for journal submission, verify:

### Pre-Submission Checks

- [ ] All 10 figures present in publication directory
- [ ] PDF versions open correctly in Adobe Reader
- [ ] PNG versions display correctly at 100% zoom
- [ ] File names follow journal requirements (if specified)
- [ ] Resolution meets journal minimum (typically 300 DPI)
- [ ] File sizes within journal limits (typically <10MB per figure)
- [ ] Color mode appropriate (RGB for screen, CMYK for print if required)
- [ ] Figures match captions in manuscript
- [ ] Figure numbers consistent with manuscript text
- [ ] All \ref{fig:*} commands in LaTeX point to correct figures

### Format-Specific Checks

**For LaTeX Submissions:**
- [ ] All PDF files included in submission archive
- [ ] `\includegraphics` paths correct relative to main.tex
- [ ] Figure labels match \ref{} commands in text
- [ ] Captions formatted according to journal style

**For Word/Other Submissions:**
- [ ] PNG versions at appropriate resolution
- [ ] Figures embedded (not linked) in document
- [ ] Figure captions styled consistently
- [ ] Figure numbering matches text references

### Supplementary Files

**Include with submission:**
1. This README.md (document figure organization)
2. `../captions.md` (consolidated captions)
3. Source scripts (optional, for reproducibility)

---

## Revision Management

### Version Control

Current figure version: **1.0** (2025-10-11)

When figures are revised:
1. Update source figure in original location
2. Regenerate using appropriate script
3. Copy updated version to publication directory
4. Increment version number in this README
5. Document changes in version log below
6. Update metadata files if applicable

### Version Log

| Version | Date | Figures Updated | Changes | Author |
|---------|------|-----------------|---------|--------|
| 1.0 | 2025-10-11 | All (1-10) | Initial publication-ready set | Viz Lead |

### Backup Protocol

**Original figures preserved in:**
- Phase-specific directories (`figures/phase5_eda/`, `figures/phase7/`, etc.)
- Results directory (`results/figures/`)
- Manuscript figures (`project_A_effects/manuscript/figures/`)

**Do not delete original source files** - publication directory contains copies

---

## Metadata Directory

The `metadata/` subdirectory contains YAML files with figure generation metadata:

```
metadata/
├── fig01_metadata.yaml
├── fig02_metadata.yaml
...
└── fig10_metadata.yaml
```

Each metadata file includes:
- Data sources and versions
- Generation timestamp
- Script used
- Key parameters
- Checksums (for verification)

**Note:** Metadata files for Figures 9 and 10 already exist in parent directory:
- `../fig10_tornado_metadata.yaml`
- Metadata embedded in `../FIGURE9_DOCUMENTATION.md`

---

## Troubleshooting

### Common Issues

**Q: PDF figure won't open or displays incorrectly**
A: Ensure using PDF viewer that supports PDF 1.5+ (Adobe Reader, Preview on Mac, evince on Linux)

**Q: PNG figure looks pixelated**
A: Verify you're viewing at 100% zoom or less. These are 300 DPI images suitable for print at journal size.

**Q: LaTeX cannot find figure file**
A: Check `\includegraphics` path is relative to main.tex location. May need `\graphicspath{{figures/publication/}}` in preamble.

**Q: Figure colors look washed out**
A: PDF viewers may apply color management. Check "Simulate Overprint" is OFF in Adobe preferences.

**Q: SVG doesn't render properly**
A: Not all applications support SVG fully. Use PDF version for print; SVG is for web/editing only.

### Contact

For figure-related issues:
- **Technical quality:** Visualization Lead
- **Statistical content:** Causal Modeler, Bayesian Modeler
- **Manuscript integration:** Manuscript Editor
- **Reproduction:** Data Engineer, QA Lead

---

## Citation and Attribution

When using these figures in presentations or derivative works:

**Manuscript Citation:**
```
[Authors]. (2025). Do Layer-2s Decongest Ethereum? A Regime-Aware Causal Study.
[Journal Name], [Volume]([Issue]), [Pages]. https://doi.org/[DOI]
```

**Data/Code Repository:**
```
[Authors]. (2025). Replication Package for "Do Layer-2s Decongest Ethereum?"
Zenodo. https://doi.org/[Zenodo DOI]
```

All figures © 2025 [Authors]. Released under [LICENSE] for replication purposes.

---

## Integration with Manuscript

### Manuscript Structure

Figures appear in the manuscript as follows:

- **Section 3.2 (Identification):** Figure 1 (DAG)
- **Section 4.1 (Descriptive Statistics):** Figures 2-7 (EDA)
- **Section 4.4 (Dynamic Effects):** Figure 8 (Event Study)
- **Section 4.5 (Counterfactuals):** Figure 9 (BSTS)
- **Section 4.7 (Robustness):** Figure 10 (Tornado)

### Cross-References in LaTeX

Recommended label scheme (matches captions.md):

```latex
\ref{fig:dag_causal_structure}     % Figure 1
\ref{fig:timeseries_regimes}       % Figure 2
\ref{fig:treatment_support}        % Figure 3
\ref{fig:seasonality}              % Figure 4
\ref{fig:correlation_structure}    % Figure 5
\ref{fig:demand_factor_pca}        % Figure 6
\ref{fig:residual_diagnostics}     % Figure 7
\ref{fig:event_study}              % Figure 8
\ref{fig:bsts_counterfactual}      % Figure 9
\ref{fig:robustness_tornado}       % Figure 10
```

---

**Directory Status:** ✅ COMPLETE AND READY FOR SUBMISSION

**Last Updated:** 2025-10-11
**Next Review:** After any figure revisions or journal feedback
