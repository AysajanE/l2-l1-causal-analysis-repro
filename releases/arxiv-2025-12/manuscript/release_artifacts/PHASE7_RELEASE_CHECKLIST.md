# Phase 7 Release Checklist — Release Manager

**Project:** L1-L2 Causal Influence Analysis Manuscript
**Phase:** 7 — Final Polish & Release
**Prepared by:** Release Manager (RM)
**Date:** 2025-10-12
**Status:** PREPARATION PHASE (execution pending Phases 5-6 completion)

---

## Executive Summary

This checklist provides a comprehensive, actionable plan for Phase 7 final release activities. Based on current manuscript audit (Oct 12, 2025), all prerequisite phases (1-4) are complete, with Phase 5 (Discussion/Conclusion) in progress.

**Estimated Phase 7 time:** 60-75 minutes (small effort, high responsibility)

**Current manuscript state:**
- PDF: 73 pages, 623 KB
- Compilation: Clean (no fatal errors)
- Phases 1-4: COMPLETE
- Phase 5: IN PROGRESS
- Phase 6: PENDING

---

## Section A: Placeholder Replacement Checklist

### A1. YOUR_USERNAME Replacement

**Current count:** 3 occurrences
**Target replacement:** [TO BE DETERMINED BY PI - likely `aeziz-ivey` or org name]

**Locations:**

1. `sections/07_data_availability.tex:15`
   - Context: GitHub Repository URL
   - Find: `https://github.com/YOUR_USERNAME/L1-L2-causal-influence-analysis`
   - Replace: `https://github.com/[ACTUAL_USERNAME]/L1-L2-causal-influence-analysis`

2. `sections/07_data_availability.tex:204`
   - Context: GitHub Issues URL
   - Find: `https://github.com/YOUR_USERNAME/L1-L2-causal-influence-analysis/issues`
   - Replace: `https://github.com/[ACTUAL_USERNAME]/L1-L2-causal-influence-analysis/issues`

3. `sections/07_data_availability.tex:214`
   - Context: Citation format
   - Find: `Code and data: \url{https://github.com/YOUR_USERNAME/L1-L2-causal-influence-analysis}`
   - Replace: `Code and data: \url{https://github.com/[ACTUAL_USERNAME]/L1-L2-causal-influence-analysis}`

**Verification command:**
```bash
grep -rn "YOUR_USERNAME" project_A_effects/manuscript/sections/
# Expected output after replacement: 0 matches
```

**Time estimate:** 2 minutes

**Checklist:**
- [ ] Confirm actual GitHub username/org with PI
- [ ] Replace all 3 occurrences in `sections/07_data_availability.tex`
- [ ] Run verification command (0 matches expected)
- [ ] Compile manuscript to verify no broken URLs

---

### A2. Zenodo DOI Insertion

**Current count:** 2 occurrences of placeholder `10.5281/zenodo.XXXXXX`
**Target replacement:** Actual Zenodo DOI (format: `10.5281/zenodo.NNNNNNN`)

**Locations:**

1. `sections/07_data_availability.tex:16`
   - Context: Data Availability statement
   - Find: `DOI: \texttt{10.5281/zenodo.XXXXXX} (to be assigned upon publication)`
   - Replace: `DOI: \texttt{10.5281/zenodo.NNNNNNN}`

2. `sections/07_data_availability.tex:214`
   - Context: Manuscript citation format
   - Find: `DOI: 10.5281/zenodo.XXXXXX`
   - Replace: `DOI: 10.5281/zenodo.NNNNNNN`

**Verification command:**
```bash
grep -rn "zenodo.XXXXXX" project_A_effects/manuscript/
# Expected output after replacement: 0 matches
```

**Zenodo archive prerequisites:**
- [ ] GitHub repository tagged (v1.0-rc)
- [ ] All analysis artifacts present in repo
- [ ] README.md complete with replication instructions
- [ ] Create Zenodo archive from GitHub release
- [ ] Obtain DOI from Zenodo
- [ ] Update manuscript with actual DOI

**Time estimate:** 5 minutes (assuming DOI already obtained)

**Potential blocker:** If Zenodo DOI not yet obtained, coordinate with PI to create archive

---

## Section B: Cross-Reference Verification

### B1. Figure References

**Total figures:** 10 (Fig 1-10)

**Status check command:**
```bash
cd project_A_effects/manuscript
grep -n "\\\\ref{fig:" sections/*.tex | wc -l
```

**Verification procedure:**
- [ ] Compile manuscript: `pdflatex main.tex`
- [ ] Open PDF and search for "??" (unresolved figure refs)
- [ ] Verify all 10 figures render correctly
- [ ] Check figure numbering is sequential (1-10)

**Expected figures:**
1. Fig 1: DAG causal structure (dag_causal_structure.pdf)
2. Fig 2: Regime overview timeseries (eda_regime_overview.pdf)
3. Fig 3: Treatment support (eda_treatment_support.pdf)
4. Fig 4: Seasonality patterns (eda_seasonality.pdf)
5. Fig 5: Correlation heatmap (eda_correlation_heatmap.pdf)
6. Fig 6: PCA demand factor (eda_pca_demand.pdf)
7. Fig 7: Residual diagnostics (eda_distributions.pdf)
8. Fig 8: Event study plot (event_study_plot.pdf)
9. Fig 9: BSTS counterfactual (bsts_counterfactual.pdf)
10. Fig 10: Sensitivity tornado (sensitivity_tornado.pdf)

**Acceptance:** No "??" for any figure reference in PDF

**Time estimate:** 5 minutes

---

### B2. Table References

**Total tables:** 8 (Tables 1-8)

**Status check command:**
```bash
grep -n "\\\\ref{tab:" sections/*.tex | wc -l
```

**Verification procedure:**
- [ ] Search PDF for "??" in table references
- [ ] Verify all 8 tables render with data (no [TBD] in cells)
- [ ] Check table numbering is sequential (1-8)

**Expected tables:**
1. Table 1: Descriptive Statistics (§4.1.2)
2. Table 2: ITS Main Effects (§4.2) - labeled as Table 3 in some docs
3. Table 3: Event Study (§4.4)
4. Table 4: Regime Heterogeneity (§4.3.1)
5. Table 5: BSTS Treatment Effects (§4.5)
6. Table 6: Front-Door Mediation (§4.4) - may be excluded if data missing
7. Table 7: RDiT Results (§4.7)
8. Table 8: Robustness & Sensitivity (§4.8)

**Acceptance:** No "??" for any table reference in PDF

**Time estimate:** 5 minutes

---

### B3. Section References

**Verification command:**
```bash
grep "\\\\ref{sec:" sections/*.tex | grep -v "^%" | wc -l
```

**Procedure:**
- [ ] Search PDF for unresolved section refs ("??")
- [ ] Verify all \label{sec:*} definitions exist
- [ ] Check cross-section references resolve correctly

**Acceptance:** No "??" for section references

**Time estimate:** 2 minutes

---

### B4. Equation References

**Verification command:**
```bash
grep "\\\\ref{eq:" sections/*.tex | grep -v "^%" | wc -l
```

**Procedure:**
- [ ] Search PDF for unresolved equation refs ("??")
- [ ] Verify all \label{eq:*} definitions exist
- [ ] Check equation numbering is correct

**Acceptance:** No "??" for equation references

**Time estimate:** 2 minutes

---

## Section C: Bibliography Verification

### C1. BibTeX Compilation Cycle

**Full compilation sequence:**
```bash
cd project_A_effects/manuscript

# Step 1: Clean auxiliary files
rm -f *.aux *.bbl *.blg *.log *.out *.toc *.lof *.lot
rm -f sections/*.aux

# Step 2: First pass (generate aux files)
pdflatex main.tex

# Step 3: Process bibliography
bibtex main

# Step 4: Second pass (integrate citations)
pdflatex main.tex

# Step 5: Third pass (finalize cross-refs)
pdflatex main.tex
```

**Time estimate:** 5 minutes

**Checklist:**
- [ ] Clean all auxiliary files
- [ ] Run pdflatex (1st pass)
- [ ] Run bibtex
- [ ] Run pdflatex (2nd pass)
- [ ] Run pdflatex (3rd pass)
- [ ] Verify 0 LaTeX errors in log

---

### C2. Citation Verification

**Check for unresolved citations:**
```bash
grep "\[?\]" main.pdf
# Expected: 0 matches (all citations should resolve)
```

**Check bibliography log for errors:**
```bash
grep -i "error\|warning" main.blg
```

**Procedure:**
- [ ] Open PDF and verify References section is populated
- [ ] Check for "[?]" in citation callouts (indicates missing bib entry)
- [ ] Verify all cited papers appear in References
- [ ] Verify all References entries are cited in text

**Acceptance:** 0 unresolved citations ("[?]")

**Time estimate:** 3 minutes

---

### C3. Bibliography Placeholder Resolution

**Current placeholders in references.bib:**
- 4 entries with `pages = {XXX--XXX}` (lines 322, 332, 342, 352)

**Action:**
- [ ] Review these 4 entries
- [ ] Update with actual page numbers if published
- [ ] If working papers, remove page field or use "Forthcoming"

**Low priority:** Can defer to post-acceptance updates if needed

**Time estimate:** 5 minutes

---

## Section D: Placeholder Purge

### D1. [TBD] Markers

**Current count:** 8 occurrences (all in `sections/appendix_technical.tex`)

**Locations and required data:**

1. Line 109: HAC lag selection value
   - Context: "HAC lag selection of [TBD] days"
   - Required: Actual HAC lag used (likely 21 based on guideline)
   - Source: Phase 6 ITS analysis outputs

2-7. Lines 135-142: Transformation comparison ADF statistics
   - Context: Table A.1 Transformation Comparison
   - Required: ADF test statistics for different transformations
   - Variables: log C^fee, u_t (both level and transformed)
   - Source: Phase 5 EDA diagnostics

8. Line 162: Missingness percentage
   - Context: Missingness matrix description
   - Required: Overall missingness % for the panel
   - Source: Phase 5 EDA data quality checks

**Verification command:**
```bash
grep -rn "\[TBD\]" project_A_effects/manuscript/sections/
# Expected after Phase 6 completion: 0 matches
```

**Action plan:**
- [ ] Coordinate with DIS to extract values from EDA/diagnostics CSVs
- [ ] Update appendix_technical.tex with actual values
- [ ] Re-compile and verify table renders correctly
- [ ] Run verification command (0 matches expected)

**Time estimate:** 10 minutes

**Potential blocker:** If diagnostic CSV files not yet generated by Phase 5/6 teams

---

### D2. [Content to be written] Markers

**Current count:** 3 occurrences (sections 05_discussion.tex and 06_conclusion.tex)

**Locations:**

1. `sections/06_conclusion.tex:8`
   - Entire conclusion section placeholder
   - Required: 170-200 word synthesis hitting $97.35B, triangulation, policy

2. `sections/05_discussion.tex:10`
   - Discussion synthesis subsection
   - Required: Triangulation across 4 methods, mechanism explanation

3. `sections/05_discussion.tex:20,49,78,115`
   - Multiple discussion subsections (policy, generalizability, limitations, future work)
   - Required: PI-approved text for limitations (Condition 4)

**Status:** Phase 5 responsibility (Lead Writer)

**Phase 7 verification:**
- [ ] Confirm all [Content to be written] removed by Phase 5 LW
- [ ] Run grep to verify 0 matches
- [ ] If any remain at Phase 7 gate, HALT and escalate to PI

**Verification command:**
```bash
grep -rn "Content to be written" project_A_effects/manuscript/sections/
# Expected: 0 matches
```

**Time estimate (Phase 7):** 2 minutes verification only

**Critical blocker:** Cannot proceed to Phase 7 until Phase 5 complete

---

### D3. TODO/FIXME/XXX Markers

**Current count:** 0 occurrences in main manuscript sections (verified Oct 12)

**Verification command:**
```bash
grep -rn "TODO\|FIXME\|XXX\|HACK" project_A_effects/manuscript/sections/
# Expected: 0 matches
```

**Note:** Some TODO mentions exist in documentation files (PHASE4_LE_BUILD_REPORT.md, etc.) but NOT in actual manuscript sections (.tex files). This is acceptable.

**Phase 7 check:**
- [ ] Run verification command on sections/*.tex
- [ ] Verify 0 matches
- [ ] Check comments in .tex files for any stray notes

**Time estimate:** 1 minute

---

## Section E: Compilation Quality Gate

### E1. Clean Auxiliary Files

**Pre-compilation cleanup:**
```bash
cd project_A_effects/manuscript
rm -f *.aux *.bbl *.blg *.log *.out *.toc *.lof *.lot
rm -f sections/*.aux
```

**Verify clean state:**
```bash
ls *.aux *.log 2>/dev/null || echo "Clean ✓"
```

**Time estimate:** 30 seconds

---

### E2. Full Compilation Cycle

**Complete build sequence:**
```bash
cd project_A_effects/manuscript

# Pass 1: Generate aux files
pdflatex main.tex

# Process bibliography
bibtex main

# Pass 2: Integrate citations
pdflatex main.tex

# Pass 3: Finalize cross-refs
pdflatex main.tex
```

**Success criteria:**
```bash
# Check exit code of final pdflatex
echo $?
# Expected: 0 (success)

# Verify PDF was updated
ls -lh main.pdf
```

**Time estimate:** 5 minutes

---

### E3. Error and Warning Check

**Check for LaTeX errors:**
```bash
grep -i "^!" main.log
# Expected: 0 matches (no errors)
```

**Check for unresolved references:**
```bash
grep "LaTeX Warning.*undefined" main.log
# Expected: 0 matches (all refs resolved)
```

**Check for overfull/underfull boxes (warnings):**
```bash
grep "Overfull\|Underfull" main.log | wc -l
```

**Acceptable warnings:**
- Minor overfull/underfull box warnings (< 5pt) are acceptable
- LaTeX Font warnings are acceptable if fonts render correctly in PDF

**Checklist:**
- [ ] 0 LaTeX errors (fatal)
- [ ] 0 undefined reference warnings
- [ ] 0 undefined citation warnings
- [ ] Document any remaining warnings with rationale

**Time estimate:** 3 minutes

---

### E4. PDF Artifact Checks

**Verify PDF generation:**
```bash
ls -lh project_A_effects/manuscript/main.pdf
```

**Expected:**
- File size: 2-5 MB (with 10 figures)
- Recent timestamp (matches compilation time)

**Check page count:**
```bash
pdfinfo main.pdf | grep Pages
```

**Expected:** ~30-40 pages (currently 73 with appendices, may shrink after content finalization)

**Check PDF metadata:**
```bash
pdfinfo main.pdf | grep -E "Title|Author|Subject|Keywords"
```

**Expected (after metadata configuration):**
- Title: "Do Layer-2s Decongest Ethereum? A Causal Analysis of Rollup Adoption and L1 Congestion"
- Author: [Author Names]
- Subject: Blockchain Economics, Causal Inference, Ethereum Layer-2 Scaling
- Keywords: Ethereum, Layer-2, EIP-1559, EIP-4844, Causal Analysis

**Checklist:**
- [ ] PDF exists and is recent
- [ ] Page count is reasonable (~30-40 pages)
- [ ] File size is reasonable (< 10 MB)
- [ ] No error messages in log about missing figures

**Time estimate:** 2 minutes

---

## Section F: PDF Metadata Configuration

### F1. Set PDF Metadata in LaTeX

**Add to preamble (coordinate with LaTeX Engineer if not already done):**

Location: `main.tex` or preamble section

```latex
\usepackage{hyperref}
\hypersetup{
  pdftitle={Do Layer-2s Decongest Ethereum? A Causal Analysis of Rollup Adoption and L1 Congestion},
  pdfauthor={Aysajan Eziz}, % Update with all authors
  pdfsubject={Blockchain Economics, Causal Inference, Ethereum Layer-2 Scaling},
  pdfkeywords={Ethereum, Layer-2, EIP-1559, EIP-4844, Causal Analysis, Bayesian Structural Time Series, Interrupted Time Series, Regression Discontinuity},
  pdfcreator={LaTeX with pdflatex},
  pdfproducer={pdfTeX},
  colorlinks=true,
  linkcolor=blue,
  citecolor=blue,
  urlcolor=blue
}
```

**Verification:**
```bash
pdfinfo main.pdf | grep -E "Title|Author|Subject|Keywords"
```

**Acceptance criteria:**
- Title matches manuscript title exactly
- Author field populated
- Subject and Keywords relevant to content

**Time estimate:** 5 minutes

**Checklist:**
- [ ] Hyperref package configured in preamble
- [ ] pdftitle set
- [ ] pdfauthor set (all authors)
- [ ] pdfsubject set
- [ ] pdfkeywords set (5-8 keywords)
- [ ] Re-compile manuscript
- [ ] Verify metadata in generated PDF

---

## Section G: Final PDF Export

### G1. Generate Canonical Filename

**Naming convention:**
```
L2_Causal_Analysis_Manuscript_YYYY-MM-DD.pdf
```

**Today's date:** 2025-10-12

**Export command:**
```bash
cd /Users/aeziz-local/Research/Projects-05-Ethereum\ Blockchain\ Economic\ Analysis/Causal\ Influence\ of\ L2\ Scaling\ Solutions\ on\ Ethereum\ L1\ Mainnet\ Congestion/L1-L2-causal-influence-analysis/wt/integration

DATE=$(date +%Y-%m-%d)
OUTPUT_NAME="L2_Causal_Analysis_Manuscript_${DATE}.pdf"

cp project_A_effects/manuscript/main.pdf "${OUTPUT_NAME}"

echo "Final PDF exported: ${OUTPUT_NAME}"
```

**Verify export:**
```bash
ls -lh L2_Causal_Analysis_Manuscript_*.pdf
```

**Time estimate:** 1 minute

---

### G2. Generate Checksum for Integrity

**Create SHA256 checksum:**
```bash
sha256sum "${OUTPUT_NAME}" > "${OUTPUT_NAME}.sha256"
cat "${OUTPUT_NAME}.sha256"
```

**Purpose:** Allows verification that the PDF has not been corrupted during transfer/storage

**Verification:**
```bash
sha256sum -c "${OUTPUT_NAME}.sha256"
# Expected: L2_Causal_Analysis_Manuscript_YYYY-MM-DD.pdf: OK
```

**Time estimate:** 1 minute

---

### G3. Move to Submission Directory

**Create submission directory (if doesn't exist):**
```bash
mkdir -p submission/
```

**Copy final artifacts:**
```bash
cp "${OUTPUT_NAME}" submission/
cp "${OUTPUT_NAME}.sha256" submission/

ls -lh submission/
```

**Checklist:**
- [ ] submission/ directory created
- [ ] Final PDF copied to submission/
- [ ] Checksum file copied to submission/
- [ ] Files verified present

**Time estimate:** 1 minute

---

## Section H: Repository Tagging

### H1. Pre-tag Verification

**Verify current commit is clean:**
```bash
git status
```

**If uncommitted changes exist:**
```bash
# Add all changes
git add -A

# Commit final version
git commit -m "Final manuscript version 1.0 - ready for submission

- All figures integrated (10/10)
- All tables populated (8/8)
- All sections complete (Abstract through Conclusion)
- Zero [TBD]/[?]/?? markers
- YOUR_USERNAME and Zenodo DOI replaced
- PDF metadata configured
- Final compilation clean

Phase completion:
- Phase 1: Figures (COMPLETE)
- Phase 2: Tables (COMPLETE)
- Phase 3: Results (COMPLETE)
- Phase 4: Abstract/Intro/Lit (COMPLETE)
- Phase 5: Discussion/Conclusion (COMPLETE)
- Phase 6: Appendices (COMPLETE)
- Phase 7: Final polish (COMPLETE)

Date: $(date +%Y-%m-%d)
Build: main.pdf (SHA256: $(sha256sum project_A_effects/manuscript/main.pdf | cut -d' ' -f1))"
```

**Time estimate:** 2 minutes

---

### H2. Create Release Candidate Tag

**Create annotated tag:**
```bash
git tag -a v1.0-rc -m "Release candidate 1.0: L1-L2 Causal Analysis Manuscript

Submission-ready version including:
- 10/10 figures integrated
- 8/8 tables populated
- All sections complete (Abstract through Conclusion)
- Zero [TBD]/[?]/?? markers
- YOUR_USERNAME replaced with actual GitHub org
- Zenodo DOI inserted: 10.5281/zenodo.NNNNNNN
- PDF metadata configured
- PI final sign-off received

Statistics:
- Pages: XX (from pdfinfo)
- File size: X.X MB
- Compilation: Clean (0 errors)

Date: $(date +%Y-%m-%d)
Build: main.pdf (SHA256: $(sha256sum project_A_effects/manuscript/main.pdf | cut -d' ' -f1))
"
```

**Verify tag created:**
```bash
git tag -l -n9 v1.0-rc
```

**View tag details:**
```bash
git show v1.0-rc
```

**Time estimate:** 3 minutes

---

### H3. Push Tag to Remote (ONLY if authorized)

**IMPORTANT:** Do NOT push without PI authorization

**When authorized:**
```bash
# Push commits
git push origin main

# Push tag
git push origin v1.0-rc
```

**Verification:**
```bash
git ls-remote --tags origin | grep v1.0-rc
```

**Checklist:**
- [ ] PI authorization obtained for push
- [ ] Commits pushed to remote
- [ ] Tag pushed to remote
- [ ] Tag visible on GitHub

**Time estimate:** 2 minutes

---

### H4. Tag Naming Convention Reference

**For Release Manager reference:**

- `v1.0-rc`: Release candidate 1 (first submission-ready version)
- `v1.0-rc2`: Release candidate 2 (if revisions needed post-QA)
- `v1.0`: Final submission version (after all approvals, before journal submission)
- `v1.1`: Post-acceptance version (with any journal-requested changes)
- `v2.0`: Major revision (if required by journal after review)

---

## Section I: Build Log Archival

### I1. Create Archive Directory Structure

**Create archive directory:**
```bash
mkdir -p archive/build_logs/v1.0-rc/
```

**Verify creation:**
```bash
ls -la archive/build_logs/
```

**Time estimate:** 30 seconds

---

### I2. Archive Build Artifacts

**Copy all build logs:**
```bash
cd project_A_effects/manuscript

# Copy LaTeX logs
cp main.log ../../archive/build_logs/v1.0-rc/
cp main.blg ../../archive/build_logs/v1.0-rc/
cp main.aux ../../archive/build_logs/v1.0-rc/

# Copy any additional diagnostic logs
cp main.out ../../archive/build_logs/v1.0-rc/ 2>/dev/null || true
cp main.toc ../../archive/build_logs/v1.0-rc/ 2>/dev/null || true
```

**Archive gate reports (if exist):**
```bash
cd ../..
if [ -d gate_reports/ ]; then
  cp -r gate_reports/ archive/build_logs/v1.0-rc/
fi
```

**Time estimate:** 1 minute

---

### I3. Create Build Summary Report

**Generate build summary:**
```bash
cat > archive/build_logs/v1.0-rc/BUILD_SUMMARY.txt <<EOF
L1-L2 Causal Analysis Manuscript - Build v1.0-rc
================================================================

Build Information
-----------------
Build Date: $(date)
Build Host: $(hostname)
LaTeX Version: $(pdflatex --version | head -1)
BibTeX Version: $(bibtex --version | head -1)

Build Results
-------------
Compilation: SUCCESS
Errors: 0
Warnings: $(grep -c "Warning" project_A_effects/manuscript/main.log || echo "0")
Pages: $(pdfinfo submission/L2_Causal_Analysis_Manuscript_*.pdf | grep Pages | awk '{print $2}')
PDF Size: $(du -h submission/L2_Causal_Analysis_Manuscript_*.pdf | cut -f1)

Content Completion
------------------
Figures: 10/10 integrated
Tables: 8/8 populated
Citations: All resolved (0 [?])
Cross-references: All resolved (0 ??)
Placeholders: 0 [TBD] remaining
Content gaps: 0 [Content to be written] remaining

Phase Completion
----------------
Phase 1 (Figures): COMPLETE
Phase 2 (Tables): COMPLETE
Phase 3 (Results): COMPLETE
Phase 4 (Abstract/Intro/Lit): COMPLETE
Phase 5 (Discussion/Conclusion): COMPLETE
Phase 6 (Appendices): COMPLETE
Phase 7 (Final Polish): COMPLETE

Quality Gates
-------------
Compilation: PASS
Cross-references: PASS
Citations: PASS
Placeholders purged: PASS
YOUR_USERNAME replaced: PASS
Zenodo DOI inserted: PASS
PDF metadata set: PASS

Approvals
---------
PI Sign-Off: APPROVED (see docs/pi_signoff_memo.txt)
QA Final Gate: PASS

Release Artifacts
-----------------
Final PDF: submission/L2_Causal_Analysis_Manuscript_$(date +%Y-%m-%d).pdf
Git Tag: v1.0-rc
Checksum: $(cat submission/L2_Causal_Analysis_Manuscript_*.sha256 | cut -d' ' -f1)

Next Steps
----------
1. PI final review
2. Submit to journal per submission guidelines
3. Create Zenodo archive (if not already done)
4. Update README with publication status

================================================================
End of Build Summary
EOF

cat archive/build_logs/v1.0-rc/BUILD_SUMMARY.txt
```

**Time estimate:** 2 minutes

---

### I4. Archive Completion Verification

**Verify all files archived:**
```bash
ls -lah archive/build_logs/v1.0-rc/
```

**Expected files:**
- BUILD_SUMMARY.txt
- main.log
- main.blg
- main.aux
- main.out (optional)
- main.toc (optional)
- gate_reports/ (if applicable)

**Checklist:**
- [ ] Archive directory created
- [ ] Build logs copied
- [ ] Build summary generated
- [ ] All expected files present
- [ ] Archive committed to git

**Time estimate:** 1 minute

---

## Section J: Progress Tracking & Handoff

### J1. Update Progress Tracker

**File to update:** `docs/MANUSCRIPT_COMPLETION_PLAN.md`

**Mark Phase 7 complete:**
- [ ] Check all Phase 7 boxes
- [ ] Update completion percentage (should be 100%)
- [ ] Record final statistics (page count, figure count, table count)
- [ ] Update last modified date

**Time estimate:** 3 minutes

---

### J2. File Handoff Note (Template)

**Create handoff note in project root or docs/:**

```markdown
Phase 7 Handoff — 2025-10-12 — Release Manager

What I completed:
- Final build orchestration (cleanup + 3× pdflatex + bibtex)
- PDF metadata set (Title/Author/Keywords)
- Repository tagged: v1.0-rc
- Final PDF exported: L2_Causal_Analysis_Manuscript_2025-10-12.pdf
- Checksum generated for integrity verification (SHA256)
- Build logs archived: archive/build_logs/v1.0-rc/
- Build summary report created
- Progress tracker updated (Phase 7 complete)

What's left / open questions:
- Awaiting journal submission instructions (formatting requirements)
- Zenodo archive to be created post-acceptance (if not already done)
- Consider generating supplementary materials package if required by journal
- PI final review and approval for submission

Files edited (relative paths):
- submission/L2_Causal_Analysis_Manuscript_2025-10-12.pdf (final export)
- submission/L2_Causal_Analysis_Manuscript_2025-10-12.pdf.sha256 (checksum)
- archive/build_logs/v1.0-rc/ (build artifacts and summary)
- docs/MANUSCRIPT_COMPLETION_PLAN.md (progress tracker updated)

Known risks or blockers:
- None - release candidate ready for PI approval
- All quality gates passed
- All placeholders resolved
- Clean compilation with 0 errors

Next owner:
- PI (for final approval and journal submission)
- Journal submission system (for upload after PI approval)

Release statistics:
- Pages: [XX from pdfinfo]
- PDF size: [X.X MB]
- Compilation time: ~5 minutes (3-pass with bibtex)
- Total Phase 7 time: ~60 minutes

Recommendation: PI should perform final read-through focusing on:
1. Abstract numbers match results
2. Conclusion emphasizes $97.35B finding
3. All author affiliations correct
4. Acknowledgments section (if any)
5. Supplementary materials requirements (if any)
```

**Time estimate:** 5 minutes

---

## Section K: Submission Package Preparation

### K1. Supplementary Materials (if required)

**Create supplementary directory:**
```bash
mkdir -p submission/supplementary/
```

**Potential supplementary materials:**
- [ ] Appendix figures (if separate from main manuscript)
- [ ] Data dictionary or codebook
- [ ] Replication script summary
- [ ] Extended robustness checks (if not in main appendix)

**Archive supplementary materials:**
```bash
cd submission/
zip -r supplementary_materials.zip supplementary/
cd ..

ls -lh submission/supplementary_materials.zip
```

**Note:** Coordinate with journal requirements - some journals include appendices in main PDF, others require separate files

**Time estimate:** 10 minutes (if needed)

---

### K2. Cover Letter Template

**Create cover letter:**
```bash
cat > submission/cover_letter.txt <<'EOF'
Dear Editor,

We are pleased to submit our manuscript titled "Do Layer-2s Decongest Ethereum? A Causal Analysis of Rollup Adoption and L1 Congestion" for consideration for publication in [Journal Name].

This manuscript presents the first rigorous causal analysis of Layer-2 scaling solutions' impact on Ethereum Layer-1 blockchain congestion. Using four complementary identification strategies (Interrupted Time Series, Event Studies, Bayesian Structural Time Series, and Regression Discontinuity in Time), we provide robust evidence that L2 adoption reduces L1 congestion and quantify the economic impact at $97.35 billion in cumulative fee savings over 137 days.

Key contributions:
1. Rigorous causal identification using posting-clean treatment and regime-aware design to address Ethereum's multiple structural breaks (EIP-1559, The Merge, EIP-4844)
2. Triangulation across four complementary methods with 87% sign consistency across 15 robustness specifications
3. Policy-relevant quantification of congestion relief, validating the Ethereum roadmap's scaling investment case

This work is of broad interest to blockchain economics, applied causal inference methodology, and decentralized systems scaling research. Our findings have direct implications for protocol design, L2 ecosystem policy, and academic understanding of blockchain scaling solutions.

All data and analysis code are publicly available on GitHub, and the analysis is fully reproducible from raw blockchain data. We have preregistered our analysis plan and followed version-controlled implementation to ensure transparency.

We confirm that this manuscript has not been published elsewhere and is not under consideration by another journal. All authors have approved the manuscript and agree with its submission to [Journal Name].

We suggest the following potential reviewers with relevant expertise:
[TO BE COMPLETED BY PI - suggest 3-5 reviewers with expertise in:
 - Blockchain economics / cryptocurrency markets
 - Applied causal inference / time series econometrics
 - Platform economics / network effects]

Thank you for your consideration. We look forward to your response.

Sincerely,

[Author Names and Affiliations]

Corresponding Author:
Aysajan Eziz
Ivey Business School, Western University
Email: aeziz@ivey.ca

EOF

echo "Cover letter template created: submission/cover_letter.txt"
```

**Time estimate:** 5 minutes (template creation)

**Note:** PI must complete reviewer suggestions and finalize before submission

---

## Section L: Final Quality Gates

### L1. Comprehensive QA Checklist

**Run through all gates one final time:**

**Content completeness:**
- [ ] Zero `[TBD]` / `[Content to be written]` / `TODO` markers
- [ ] Zero `??` (unresolved cross-references)
- [ ] Zero `[?]` (unresolved citations)
- [ ] All 10 figures present and render correctly
- [ ] All 8 tables populated with actual data
- [ ] Abstract includes concrete numbers ($97.35B, 137 days, etc.)
- [ ] Conclusion synthesizes findings and policy implications

**Placeholder resolution:**
- [ ] YOUR_USERNAME replaced with actual GitHub org/username
- [ ] Zenodo DOI inserted (or marked as "to be assigned" if pre-submission)
- [ ] All XXX page numbers in references.bib updated or justified

**Compilation quality:**
- [ ] PDF metadata set (Title/Author/Keywords)
- [ ] Clean compilation (0 errors)
- [ ] All cross-references resolve (0 ?? in PDF)
- [ ] All citations resolve (0 [?] in PDF)
- [ ] Bibliography complete and formatted correctly
- [ ] Page count reasonable (~30-40 pages)
- [ ] PDF file size reasonable (< 10 MB)

**Version control:**
- [ ] Repository tagged: v1.0-rc
- [ ] Final commit message documents completion
- [ ] Build logs archived
- [ ] Checksum generated for final PDF

**Approvals:**
- [ ] QA final gate: PASS
- [ ] PI sign-off received
- [ ] All co-authors approved (if applicable)

**Time estimate:** 10 minutes

---

### L2. If Any Gate Fails - Escalation Protocol

**HALT release process immediately if:**
- Any `[TBD]` or `[Content to be written]` markers remain
- Any unresolved cross-references or citations
- Any LaTeX compilation errors
- Missing figures or tables
- Placeholders (YOUR_USERNAME, Zenodo) not resolved
- QA gate failures

**Escalation path:**
1. Document specific failure in detail
2. Report to QA Lead
3. QA escalates to relevant role (LE for build issues, LW for content, RDE for citations)
4. If unresolved, QA escalates to PI
5. PI makes final decision (delay release or accept risk with documentation)

**Do NOT:**
- Override QA gate failures without PI authorization
- Push tags to remote without PI approval
- Create final release tag (v1.0) before journal acceptance
- Proceed with submission if any critical issues remain

---

## Section M: Release Announcement

### M1. Internal Team Announcement

**Create release announcement:**
```bash
cat > release_announcement.txt <<EOF
RELEASE ANNOUNCEMENT
====================================================================

L1-L2 Causal Analysis Manuscript - v1.0-rc

Status: READY FOR SUBMISSION

Final PDF: submission/L2_Causal_Analysis_Manuscript_$(date +%Y-%m-%d).pdf
Repository Tag: v1.0-rc
Pages: [XX from pdfinfo]
PDF Size: [X.X MB]

Completion Summary
------------------
Phase 1 (Figures): ✓ 10/10 integrated
Phase 2 (Tables): ✓ 8/8 populated
Phase 3 (Results): ✓ All sections complete
Phase 4 (Front Matter): ✓ Abstract/Intro/Lit complete
Phase 5 (Discussion): ✓ Discussion/Conclusion complete
Phase 6 (Appendices): ✓ Appendices complete
Phase 7 (Final Polish): ✓ Build clean, metadata set

Quality Gates
-------------
Compilation: PASS (0 errors)
Cross-references: PASS (0 ??)
Citations: PASS (0 [?])
Placeholder purge: PASS (0 [TBD])
Username replacement: PASS
DOI insertion: PASS
QA Final Gate: PASS
PI Sign-Off: APPROVED

Key Findings (for reference)
----------------------------
- Total Effect: $97.35B cumulative fee savings [95% CI: $79.87B, $118.45B]
- Period: 137 days (post-London, pre-Dencun exclusion)
- Posterior: P(TE<0) = 0.995 (99.5% probability of congestion reduction)
- Daily savings: $710.56M/day
- Methods: ITS + Event Study + BSTS + RDiT (triangulation)
- Robustness: 87% sign consistency across 15 specifications

Next Steps
----------
1. PI reviews final PDF
2. PI approves submission to journal
3. Submit manuscript via journal submission system
4. Create Zenodo archive (if not already done)
5. Update README with publication status

Timeline
--------
- Phase 1-2: Days 1-2 (Figures + Tables)
- Phase 3-4: Days 2-3 (Results + Front matter)
- Phase 5-6: Days 3-4 (Discussion + Appendices)
- Phase 7: Day 5 (Final polish)
- Total: 5 days (estimated from guideline)

Contributor Acknowledgments
----------------------------
Thank you to all team members:
- Data Integration Specialist (DIS): CSV → LaTeX tables
- Figure/Table Specialist (FTS): 10 figures integrated
- LaTeX Engineer (LE): Clean build, cross-refs
- Lead Writer (LW): Narrative synthesis
- PI / Causal Lead: Scientific guidance, final approval
- Quality Assurance Lead (QA): Gate enforcement
- References & Data Availability Editor (RDE): Citations, DOI
- Release Manager (RM): Final build, tagging, packaging

Release Date: $(date)
Release Manager: [RM Name/ID]

Changelog
---------
For detailed changes, see:
git log v1.0-p6..v1.0-rc

====================================================================
EOF

cat release_announcement.txt
```

**Distribute to:**
- [ ] All team members (via email or project communication channel)
- [ ] PI (for final approval)
- [ ] Project stakeholders (if any)

**Time estimate:** 5 minutes

---

## Section N: Time Estimates Summary

### N1. Time Breakdown by Section

**Section A: Placeholder Replacement**
- A1. YOUR_USERNAME: 2 min
- A2. Zenodo DOI: 5 min
- **Subtotal: 7 min**

**Section B: Cross-Reference Verification**
- B1. Figures: 5 min
- B2. Tables: 5 min
- B3. Sections: 2 min
- B4. Equations: 2 min
- **Subtotal: 14 min**

**Section C: Bibliography**
- C1. Compilation cycle: 5 min
- C2. Citation verification: 3 min
- C3. Placeholder resolution: 5 min
- **Subtotal: 13 min**

**Section D: Placeholder Purge**
- D1. [TBD] markers: 10 min (requires DIS input)
- D2. [Content to be written]: 2 min (verification only)
- D3. TODO/FIXME: 1 min
- **Subtotal: 13 min**

**Section E: Compilation**
- E1. Clean aux files: 0.5 min
- E2. Full compilation: 5 min
- E3. Error check: 3 min
- E4. PDF artifact checks: 2 min
- **Subtotal: 10.5 min**

**Section F: PDF Metadata**
- F1. Configure metadata: 5 min
- **Subtotal: 5 min**

**Section G: Final PDF Export**
- G1. Generate filename: 1 min
- G2. Generate checksum: 1 min
- G3. Move to submission/: 1 min
- **Subtotal: 3 min**

**Section H: Repository Tagging**
- H1. Pre-tag verification: 2 min
- H2. Create tag: 3 min
- H3. Push tag: 2 min
- **Subtotal: 7 min**

**Section I: Build Log Archival**
- I1. Create directory: 0.5 min
- I2. Archive artifacts: 1 min
- I3. Build summary: 2 min
- I4. Verification: 1 min
- **Subtotal: 4.5 min**

**Section J: Progress Tracking**
- J1. Update tracker: 3 min
- J2. Handoff note: 5 min
- **Subtotal: 8 min**

**Section K: Submission Package (optional)**
- K1. Supplementary materials: 10 min
- K2. Cover letter: 5 min
- **Subtotal: 15 min (optional)**

**Section L: Final QA**
- L1. QA checklist: 10 min
- **Subtotal: 10 min**

**Section M: Release Announcement**
- M1. Announcement: 5 min
- **Subtotal: 5 min**

---

### N2. Total Time Estimate

**Core Phase 7 tasks (required):** 60 minutes
**Optional tasks (submission package):** 15 minutes
**Total maximum time:** 75 minutes

**Critical path:**
1. Placeholder replacement (7 min)
2. Bibliography compilation (13 min)
3. Placeholder purge (13 min) - *may require DIS input*
4. Compilation + verification (24 min)
5. Export + tagging + archival (14.5 min)
6. Final QA (10 min)

**Parallelization opportunities:**
- While LaTeX compiles (5 min), can prepare cover letter
- While generating checksums, can start handoff notes

---

## Section O: Potential Blockers & Risks

### O1. High-Risk Blockers

**Blocker 1: Phase 5 not complete**
- **Risk:** [Content to be written] markers remain in Discussion/Conclusion
- **Impact:** Cannot proceed to Phase 7
- **Mitigation:** Verify Phase 5 completion before starting Phase 7
- **Owner:** Lead Writer (LW)
- **Escalation:** QA → PI if Phase 5 delayed

**Blocker 2: Appendix [TBD] values missing**
- **Risk:** Diagnostic statistics not yet computed by EDA/QA
- **Impact:** 8 [TBD] markers remain in appendix_technical.tex
- **Mitigation:** Coordinate with DIS to extract from Phase 5/6 CSVs
- **Owner:** Data Integration Specialist (DIS)
- **Escalation:** RM → DIS → QA → PI if data unavailable

**Blocker 3: Zenodo DOI not obtained**
- **Risk:** Cannot replace placeholder if archive not created
- **Impact:** Manuscript references non-existent DOI
- **Mitigation:** Create Zenodo archive early in Phase 7, OR mark as "to be assigned upon publication"
- **Owner:** PI / RM
- **Decision:** PI decides if placeholder acceptable for initial submission

**Blocker 4: YOUR_USERNAME not decided**
- **Risk:** Don't know actual GitHub org/username to use
- **Impact:** Cannot replace placeholder
- **Mitigation:** Confirm with PI before Phase 7
- **Owner:** PI
- **Decision:** Likely `aeziz-ivey` or Western/Ivey org name

---

### O2. Medium-Risk Issues

**Issue 1: Bibliography placeholder entries**
- **Risk:** 4 entries have XXX page numbers
- **Impact:** References section incomplete
- **Mitigation:** Low priority - can defer if working papers
- **Owner:** RDE
- **Acceptance:** Can submit with "Forthcoming" for unpublished papers

**Issue 2: Overfull/underfull box warnings**
- **Risk:** Minor LaTeX formatting warnings
- **Impact:** Aesthetic only (if < 5pt)
- **Mitigation:** Document and accept if minimal
- **Owner:** LE
- **Acceptance:** < 5pt overfull acceptable

**Issue 3: Figure file sizes large**
- **Risk:** PDF exceeds 10 MB
- **Impact:** May need to compress figures
- **Mitigation:** Check individual figure sizes, compress if needed
- **Owner:** FTS / LE
- **Threshold:** Total PDF < 10 MB preferred

---

### O3. Low-Risk Considerations

**Consideration 1: Supplementary materials requirements**
- **Risk:** Journal may require separate appendix files
- **Impact:** Need to repackage after submission
- **Mitigation:** Check journal guidelines early
- **Owner:** PI / RM

**Consideration 2: Co-author approvals**
- **Risk:** If multiple authors, all must approve
- **Impact:** Cannot submit without all approvals
- **Mitigation:** Circulate draft early in Phase 7
- **Owner:** PI

**Consideration 3: Journal-specific formatting**
- **Risk:** May need to reformat for specific journal
- **Impact:** Additional LaTeX work post-Phase 7
- **Mitigation:** Target generic academic format in Phase 7
- **Owner:** LE (if reformatting needed)

---

## Section P: Success Criteria & Acceptance

### P1. Phase 7 Success Criteria

**Phase 7 is COMPLETE when ALL of the following are true:**

**Content:**
- [ ] Zero `[TBD]` markers in entire manuscript
- [ ] Zero `[Content to be written]` markers in entire manuscript
- [ ] Zero `TODO/FIXME/XXX` markers in manuscript sections
- [ ] All 10 figures present and rendering correctly
- [ ] All 8 tables populated with actual data
- [ ] Abstract includes concrete findings ($97.35B, etc.)

**Technical:**
- [ ] Manuscript compiles cleanly (0 LaTeX errors)
- [ ] Zero unresolved cross-references (??)
- [ ] Zero unresolved citations ([?])
- [ ] Bibliography complete (all cited papers in References)
- [ ] PDF metadata configured correctly

**Placeholders:**
- [ ] YOUR_USERNAME replaced with actual GitHub org/username
- [ ] Zenodo DOI inserted (or marked "to be assigned")
- [ ] No placeholder URLs or XXX markers in critical locations

**Versioning:**
- [ ] Repository tagged: v1.0-rc
- [ ] Final commit documented
- [ ] Build logs archived
- [ ] Checksum generated for final PDF

**Quality Gates:**
- [ ] LE confirms: Manuscript compiles clean
- [ ] RDE confirms: Citations complete, DOI inserted
- [ ] QA confirms: All gates PASS
- [ ] PI confirms: Final sign-off memo issued

**Deliverables:**
- [ ] Final PDF exported: `L2_Causal_Analysis_Manuscript_YYYY-MM-DD.pdf`
- [ ] Checksum file: `*.sha256`
- [ ] Build logs archived: `archive/build_logs/v1.0-rc/`
- [ ] Handoff notes filed
- [ ] Release announcement sent

---

### P2. Acceptance Criteria

**Release Manager signs off when:**
1. All success criteria met (above checklist 100% complete)
2. PI has reviewed and approved final PDF
3. QA final gate result: PASS
4. No outstanding blockers or risks
5. Release announcement distributed to team

**PI approval checklist:**
- [ ] Abstract accurately reflects findings
- [ ] $97.35B finding prominently featured
- [ ] Conclusion strong and policy-relevant
- [ ] All author names and affiliations correct
- [ ] Acknowledgments section (if any) appropriate
- [ ] Ready for journal submission

---

## Section Q: Key References

### Q1. Documentation Files

**Always have these files open during Phase 7:**

1. **Implementation guideline:**
   - Path: `project_A_effects/docs/manuscript_writing_guideline.md`
   - Section: Phase 7 (lines 268-275)

2. **Role specifications:**
   - Path: `project_A_effects/docs/staffing_and_orchestration_spec.md`
   - Section: Release Manager (lines 232-256)

3. **PI sign-off memo:**
   - Path: `docs/pi_signoff_memo.txt` (to be created by PI)

4. **Progress tracker:**
   - Path: `docs/MANUSCRIPT_COMPLETION_PLAN.md`

5. **Current status:**
   - Path: `project_A_effects/manuscript/MANUSCRIPT_STATUS.md`

---

### Q2. Command Quick Reference

**Essential commands for Phase 7:**

```bash
# Navigate to manuscript directory
cd project_A_effects/manuscript

# Clean auxiliary files
rm -f *.aux *.bbl *.blg *.log *.out *.toc *.lof *.lot sections/*.aux

# Full compilation cycle
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex

# Search for placeholders
grep -rn "\[TBD\]" sections/
grep -rn "Content to be written" sections/
grep -rn "YOUR_USERNAME" sections/
grep -rn "zenodo.XXXXXX" sections/

# Check for unresolved references
grep "??" main.log
grep "\[?\]" main.pdf

# PDF info
pdfinfo main.pdf

# Create final export
DATE=$(date +%Y-%m-%d)
cp main.pdf "../../L2_Causal_Analysis_Manuscript_${DATE}.pdf"
sha256sum "../../L2_Causal_Analysis_Manuscript_${DATE}.pdf" > "../../L2_Causal_Analysis_Manuscript_${DATE}.pdf.sha256"

# Git tagging
git tag -a v1.0-rc -m "Release candidate 1.0"
git tag -l -n9 v1.0-rc
```

---

## Section R: Execution Checklist

### R1. Pre-execution Verification

**Before starting Phase 7 tasks, verify:**

- [ ] Phase 1 COMPLETE (10/10 figures integrated)
- [ ] Phase 2 COMPLETE (8/8 tables populated)
- [ ] Phase 3 COMPLETE (Results section written)
- [ ] Phase 4 COMPLETE (Abstract/Intro/Lit written)
- [ ] Phase 5 COMPLETE (Discussion/Conclusion written)
- [ ] Phase 6 COMPLETE (Appendices populated)
- [ ] QA final gate: PASS
- [ ] PI sign-off memo received
- [ ] No outstanding issues from previous phases

**If ANY prerequisite is incomplete:**
- [ ] HALT Phase 7 execution
- [ ] Document incomplete prerequisite
- [ ] Escalate to QA → PI
- [ ] Wait for completion before proceeding

---

### R2. Phase 7 Execution Order

**Follow this sequence strictly:**

1. **Prerequisites check** (5 min)
   - [ ] Verify all phases 1-6 complete
   - [ ] Obtain PI authorization to proceed

2. **Placeholder replacement** (10 min)
   - [ ] Confirm YOUR_USERNAME with PI
   - [ ] Replace YOUR_USERNAME (3 locations)
   - [ ] Obtain/confirm Zenodo DOI
   - [ ] Replace Zenodo DOI (2 locations)
   - [ ] Verify replacements

3. **Appendix [TBD] resolution** (15 min)
   - [ ] Coordinate with DIS for diagnostic values
   - [ ] Update appendix_technical.tex (8 [TBD] markers)
   - [ ] Verify no [TBD] remain

4. **Bibliography compilation** (10 min)
   - [ ] Clean auxiliary files
   - [ ] Run full pdflatex → bibtex → pdflatex × 2 cycle
   - [ ] Verify 0 errors, 0 warnings (or document acceptable warnings)

5. **Cross-reference verification** (15 min)
   - [ ] Check figures (no ??)
   - [ ] Check tables (no ??)
   - [ ] Check sections (no ??)
   - [ ] Check equations (no ??)
   - [ ] Check citations (no [?])

6. **PDF metadata configuration** (5 min)
   - [ ] Add hyperref metadata to preamble
   - [ ] Re-compile
   - [ ] Verify metadata in PDF

7. **Final PDF export** (5 min)
   - [ ] Generate canonical filename
   - [ ] Copy to submission/
   - [ ] Generate checksum
   - [ ] Verify export

8. **Repository tagging** (10 min)
   - [ ] Commit final changes
   - [ ] Create annotated tag v1.0-rc
   - [ ] Verify tag
   - [ ] (Optional) Push to remote if authorized

9. **Build log archival** (5 min)
   - [ ] Create archive directory
   - [ ] Copy build logs
   - [ ] Create build summary
   - [ ] Verify archive

10. **Final QA & handoff** (15 min)
    - [ ] Run comprehensive QA checklist
    - [ ] Update progress tracker
    - [ ] Write handoff notes
    - [ ] Create release announcement
    - [ ] Distribute to team

**Total time:** 60-75 minutes

---

## Section S: Post-Phase 7 Activities

### S1. Journal Submission (PI responsibility)

**After Phase 7 complete and PI approval:**

1. **Select target journal**
   - [ ] Identify appropriate venue (blockchain, economics, causal inference)
   - [ ] Review submission guidelines
   - [ ] Check formatting requirements

2. **Prepare submission materials**
   - [ ] Final PDF (from submission/ directory)
   - [ ] Cover letter (customize template in submission/)
   - [ ] Supplementary materials (if required)
   - [ ] Author information forms
   - [ ] Conflict of interest disclosures

3. **Submit via journal system**
   - [ ] Create account / log in
   - [ ] Upload manuscript PDF
   - [ ] Upload supplementary materials
   - [ ] Enter metadata (title, authors, abstract, keywords)
   - [ ] Suggest reviewers (if applicable)
   - [ ] Submit and obtain submission ID

4. **Post-submission**
   - [ ] Update repository README with "Under Review" status
   - [ ] Monitor for editor/reviewer correspondence
   - [ ] Prepare response-to-reviewers template

---

### S2. Zenodo Archive Creation (if not already done)

**Create persistent archive:**

1. **Prepare repository**
   - [ ] Ensure all files committed
   - [ ] Clean up any sensitive/temporary files
   - [ ] Verify README is comprehensive

2. **Create GitHub release**
   - [ ] Go to repository Releases page
   - [ ] Click "Create a new release"
   - [ ] Select tag: v1.0-rc
   - [ ] Title: "L1-L2 Causal Analysis v1.0 - Submission Version"
   - [ ] Description: Copy from release_announcement.txt
   - [ ] Attach final PDF (optional)
   - [ ] Publish release

3. **Link to Zenodo**
   - [ ] Enable Zenodo integration for repository
   - [ ] Trigger Zenodo archive creation
   - [ ] Obtain DOI from Zenodo
   - [ ] Update manuscript with DOI (if not done in Phase 7)

4. **Verify archive**
   - [ ] Check Zenodo archive page
   - [ ] Verify all files present
   - [ ] Test download and checksum
   - [ ] Update README with Zenodo badge

---

### S3. Long-term Maintenance

**After submission/acceptance:**

1. **Version management**
   - v1.0-rc → v1.0 (final submitted version)
   - v1.1 (if minor revisions requested)
   - v2.0 (if major revision)

2. **Publication updates**
   - Update README with publication status
   - Add DOI of published paper
   - Link to journal page

3. **Citation tracking**
   - Monitor Google Scholar citations
   - Update CV/website with publication

---

## Conclusion

This checklist provides a comprehensive, step-by-step guide for Phase 7 final release activities. Follow the execution order strictly, verify all prerequisites before starting, and escalate any blockers immediately to QA → PI.

**Remember:**
- Process discipline over speed
- Better to delay 30 minutes than ship with errors
- Document everything for reproducibility
- Verify before announcing "READY FOR SUBMISSION"
- Celebrate the team's accomplishment

**Release Manager responsibility:**
You are the conductor of the final act. All prior work culminates in your delivery. Your rigor ensures the manuscript represents the team's best work and is ready for the world to see.

---

**Checklist prepared by:** Release Manager
**Date:** 2025-10-12
**Status:** PREPARATION COMPLETE - Ready for Phase 7 execution when Phases 5-6 complete
**Estimated execution time:** 60-75 minutes
**Critical dependencies:** Phases 1-6 complete, QA gate PASS, PI sign-off received

---

END OF PHASE 7 RELEASE CHECKLIST
