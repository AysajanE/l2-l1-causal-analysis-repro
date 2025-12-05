# Phase 8 Submission Checklist -- arXiv Package

## Files to Upload
- `main.tex`, `references.bib`, `sections/` (all `.tex`), and `figures/` (all `.pdf`) -- packaged via tarball below (no ToC/LoF/LoT files included).
- Generated PDF (`main.pdf`) for internal QA only; arXiv will rebuild from TeX sources.

## Pre-Submission QA
- [x] Clean LaTeX build (`latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex`).
- [x] No LaTeX warnings/errors (checked `main.log`).
- [x] Confirm abstract length via `texcount -sum -inc main.tex` (167 words).
- [x] Main-text page target 28--34 pages (Sections 1--7 now span pp.~2--29 = 28 pages).
- [x] Appendix page target <=20 pages (Appendices A--H now span pp.~30--42 = 13 pages; formerly 59 pages).
- [x] Figures limited to 4 in the main text; BSTS panel labeled exploratory.
- [x] Verify bibliography compiles (`cd manuscript && bibtex main`).
- [x] Margin badges render (spot-check Sections 4 & Appendix B) without introducing hyperref warnings.
- [x] Cross-reference/hyperlink audit filed (`manuscript/PHASE8_CROSS_REFERENCE_AUDIT.md`).

## Metadata Prep
- Title: "Do Layer-2s Decongest Ethereum? Regime-Aware Causal Evidence 2021--2024".
- Authors: Aysajan Eziz (Ivey Business School, Western University).
- Abstract: use `sections/abstract.tex` content (167 words).
- Categories: cs.CY, econ.EM, stat.AP (per audit).
- Comments field: "Main text 28 pages (pp.~2--29) + appendices 13 pages (pp.~30--42); 4 main-text figures, 2 main-text tables; additional diagnostics in appendices." 
- DOI placeholder: `10.5281/zenodo.XXXXXX` (final Zenodo DOI to be inserted after archive minting; this step is tracked outside Phase~8 QA), and OSF prereg (`10.17605/OSF.IO/7D4XN`).

## Submission Steps
1. Create clean tarball: `cd manuscript && tar --exclude='*.aux' --exclude='*.log' --exclude='figures/*.png' --exclude='figures/*/*.png' --exclude='figures/.DS_Store' --exclude='figures/.gitkeep' -czf ../arxiv_submission.tar.gz main.tex sections figures references.bib Makefile` (**DONE 2025-11-16 21:15 ET; SHA256 42dd1d9207d722bf6bafc2c4e25c8b303ce972173fc21609af5c63965174607f**).
2. Upload tarball to arXiv submission portal; verify auto-generated PDF matches `main.pdf`.
3. Fill metadata (title, abstract, authors, categories, comments, DOIs, keywords).
4. Attach ancillary files if desired (e.g., `README.md`).
5. Final review before hitting "Submit"; save confirmation email and submission ID.
