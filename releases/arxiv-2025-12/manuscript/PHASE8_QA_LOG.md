# Phase 8 QA Log -- 2025-11-16 (updated 21:40 ET)

## Build Status
- `cd manuscript && latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex` -> **PASS**; `main.pdf` currently rebuilds as of 2025-11-16 21:05 ET (42 pages, 899 KB) with zero LaTeX warnings/errors (`rg "Warning" main.log` returns no matches).
- Overfull/underfull boxes: none reported; float placement warnings absent in the final build.

## Word Count & Abstract Compliance
- `cd manuscript && texcount -sum -inc main.tex` -> Abstract 167 words (within the 150--200 range). Updated section word counts (text only): Intro 635, Related 615, Data 462, Methods 1 897, Results 3 034, Discussion 1 089, Conclusion 577. Appendices contribute ~1 660 words. Total main-text words (Sections 1--7) are now ~8 300.

## Structure, Page Counts, and Margin Badges
- Front matter remains trimmed: `\tableofcontents`, `\listoftables`, and `\listoffigures` are omitted from `main.tex`, so readers dive directly into Section 1.
- Page audit via `python` (parsing `main.aux` labels) now shows Sections 1--7 span pp.~2--29 (main-text length = 28 pages, satisfying the 28--34-page target) and Appendices A--H span pp.~30--42 (13 pages, within the 12--20-page appendix budget). Total PDF length is 42 pages vs. ~90 in the original draft.
- Margin badge audit: `\confirmatorybadge`/`\exploratorybadge` macros still drive both inline text and a `marginnote`; spot-checks on pp.~4 (Data), 13 (Methods), 21 (Results), 31 (Appendix~A), and 42 (Appendix~H) confirm badges render and bookmarks remain clean via `\pdfstringdefDisableCommands`.

## Cross-Reference & Hyperlink QA
- Crosswalk expanded: `manuscript/PHASE8_CROSS_REFERENCE_AUDIT.md` now tracks nine canonical claims (C1--C9) covering Data, Methods, Results, Discussion, and transparency; each claim maps to exactly one main-text figure/table plus, where appropriate, a single appendix exhibit.
- Crosswalk versioning: SHA256 for `PHASE8_CROSS_REFERENCE_AUDIT.md` at this build is `62c0e40736c05c5334249d2760e82c4c0c1f393aaca2481ace9453695f361f15`, so future reviewers can confirm alignment between this QA log and the claim inventory.
- Hyperlink integrity: the Python audit script (PyPDF2) on `main.pdf` reports `{'pages_with_annotations': 36, 'total_annotations': 201, 'total_pages': 42}`, confirming that hyperlink annotations cover the majority of pages in the final 42-page PDF. Manual spot checks of `main.out` confirmed every section/subsection bookmark, including appendix sections, survived the badge and appendix rewrites.

## Figures, Tables, and Typography
- Manual audit of `main.tex` and the compiled PDF confirms that only four figures live in the main text (regime overview, DAG, LP IRF, BSTS) and two tables (merged ECM estimates and regime heterogeneity); all additional diagnostics and exploratory visuals are confined to Appendices B--F.
- Caption formatting and typography: all figure and table captions use the global `\captionsetup{font=small,labelfont=bf}` style; body text and math rely on the `lmodern` font family, and axis labels within figures were generated using the same publication-style settings as the main plots, yielding consistent font families and relative sizes across the document. No mixed serif/sans-serif anomalies or oversized captions were observed in the final PDF.

## Packaging & Submission Artifacts
- Clean tarball regenerated: `cd manuscript && tar --exclude='*.aux' --exclude='*.log' --exclude='figures/*.png' --exclude='figures/*/*.png' --exclude='figures/.DS_Store' --exclude='figures/.gitkeep' -czf ../arxiv_submission.tar.gz main.tex sections figures references.bib Makefile` -> `arxiv_submission.tar.gz` (current SHA256 `42dd1d9207d722bf6bafc2c4e25c8b303ce972173fc21609af5c63965174607f`). The bundle now contains TeX sources plus only the PDF figures actually used (including appendix figures); no `.aux/.log/.png/.DS_Store` artifacts remain.
- Final PDF for sanity checks: `manuscript/main.pdf` (42 pages, SHA256 `47304177df5daac93f795c95fb48be8dfc1b9edd8aedacb680f91b47be1827c2`) is the reference artifact; arXiv will regenerate from the tarball.

## Outstanding Follow-Ups
1. **Main-text length (MT-LEN-01):** Resolved. Sections 1--7 now span pp.~2--29 (28 pages), satisfying the 28--34-page target without reintroducing appendix material.
2. **Zenodo DOI finalization (post-Phase-8 task):** Placeholder `10.5281/zenodo.XXXXXX` remains in Appendix~A. Archive submission is scheduled for 2025-11-20; the final DOI will be inserted into Appendix~\ref{sec:availability}, the submission metadata, and this log as part of the release phase \emph{after} Phase~8 QA, so the current Phase~8 artifacts intentionally record this as a pending external step.
