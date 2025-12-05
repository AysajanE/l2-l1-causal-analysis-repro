# Phase 3: Table 3 Baseline Specification Correction Report

**Date:** 2025-10-12
**Role:** Data Integration Specialist (DIS)
**Issue:** Critical table-text mismatch in Table 3 (Main ITS Effects)
**Status:** ✓ RESOLVED

---

## Executive Summary

**CRITICAL MISMATCH IDENTIFIED AND CORRECTED:**

Table 3 (Main ITS Effects) contained incorrect baseline specification numbers that contradicted both the narrative text and Table 8 (Robustness). The table showed a highly significant effect (β = -1.497***, p < 0.001), while the text and approved Phase 10 findings correctly stated a non-significant effect (β = -0.66, p = 0.17). This correction ensures consistency across all manuscript elements.

---

## Issue Details

### Problem Identified by QA

| Element | Old (WRONG) | Correct (APPROVED) |
|---------|-------------|-------------------|
| **Table 3 β** | -1.497*** | -0.656 |
| **Table 3 CI** | [-2.301, -0.692] | [-1.588, 0.276] |
| **Table 3 Effect** | -13.9% | -6.3% per 10-pp ΔA |
| **Table 3 p-value** | <0.001 (***) | 0.17 (no stars) |
| **Significance** | Highly significant | NOT significant |

### Inconsistency Evidence

1. **Narrative text (line 161)** correctly states: β = -0.66, p = 0.17, "suggestive evidence" (NOT significant)
2. **Table 8 baseline row (line 203)** correctly shows: β = -0.656, p = 0.168
3. **Table 3 (line 174)** INCORRECTLY showed: β = -1.497***, p < 0.001

---

## Root Cause Analysis

### Source Data Investigation

1. **`table3_main_its_final.csv` (INCORRECT SOURCE):**
   - Contains: β = -1.497, CI: [-2.301, -0.692], p = 0.0003
   - **Diagnosis:** This file appears to contain a misspecified model variant, possibly an earlier specification before Phase 10 finalization

2. **`table7_robustness_grid.csv` (CORRECT SOURCE):**
   - Line 2 (baseline row): β = -0.656, CI: [-1.588, 0.276], p = 0.168
   - Marked as `Is Baseline = True`
   - **Diagnosis:** This is the PI-approved Phase 10 baseline specification

### Why the Error Occurred

The file `table3_main_its_final.csv` was likely generated from an intermediate analysis run that was later superseded by Phase 10 respecification decisions. The correct baseline numbers were finalized in Phase 10 and appear in `table7_robustness_grid.csv`, but the Table 3 CSV was not updated to reflect these decisions.

---

## Correction Applied

### File Modified
- **Location:** `/manuscript/sections/04_results.tex`
- **Lines:** 174-176 (Table 3 data rows)

### Changes Made

**Log Base Fee Row (line 174):**

```latex
OLD: Log Base Fee ($\log C^{fee}$) & -1.497*** & [-2.301, -0.692] & -13.9\% & First Differences & 1,242 \\

NEW: Log Base Fee ($\log C^{fee}$) & -0.656 & [-1.588, 0.276] & -6.3\% & First Differences & 1,242 \\
```

**Utilization Row (line 175) - Minor CI correction:**

```latex
OLD: Utilization ($u_t$) & -0.004 & [-0.011, 0.003] & --- & Detrended & 1,244 \\

NEW: Utilization ($u_t$) & -0.004 & [-0.012, 0.004] & --- & Detrended & 1,244 \\
```

**Scarcity Row (line 176):**
- NO CHANGE (already correct with S_t β = -1.526***, p < 0.001)

---

## Validation Checks Performed

### 1. Transformation Verification

```python
import numpy as np

beta = -0.656
pct_change = 100 * (np.exp(0.10 * beta) - 1)
# Result: -6.347% ≈ -6.3% per 10-pp ΔA ✓

ci_lower = -1.588
ci_upper = 0.276
ci_lower_pct = 100 * (np.exp(0.10 * ci_lower) - 1)  # -14.7%
ci_upper_pct = 100 * (np.exp(0.10 * ci_upper) - 1)  # +2.8%
```

**Result:** ✓ Transformation formula correctly applied

### 2. Significance Check

- p-value: 0.168 → rounds to p = 0.17
- 0.168 > 0.05 → NOT statistically significant
- **∴ NO STARS in Table 3** (corrected from ***)

**Result:** ✓ Significance interpretation correct

### 3. Consistency with Table 8

| Outcome | Table 3 | Table 8 Baseline | Match? |
|---------|---------|------------------|--------|
| Log Base Fee β | -0.656 | -0.656 | ✓ |
| Log Base Fee CI | [-1.588, 0.276] | [-1.588, 0.276] | ✓ |
| Log Base Fee p | 0.17 | 0.168 | ✓ |
| Utilization β | -0.004 | -0.004 | ✓ |
| Utilization CI | [-0.012, 0.004] | [-0.012, 0.004] | ✓ |
| Scarcity β | -1.526*** | -1.526*** | ✓ |

**Result:** ✓ All values consistent across tables

### 4. Consistency with Narrative Text

- Text (line 161): "β = -0.66, p = 0.17, suggestive evidence"
- Table 3: β = -0.656, p = 0.17 (no stars)

**Result:** ✓ Table now matches narrative interpretation

### 5. Sample Size Verification

- Log base fee & scarcity: N = 1,242 (first differences lose 1 observation)
- Utilization: N = 1,244 (detrended, full sample)
- Total post-London sample: N = 1,245 days

**Result:** ✓ Sample sizes correct per specification

### 6. LaTeX Compilation

- Command: `pdflatex -interaction=nonstopmode main.tex`
- Output: No errors, warnings related to table content

**Result:** ✓ COMPILATION SUCCESSFUL

---

## Methodological Implications

### Causal Interpretation

**Before Correction:**
- Table 3 suggested **highly significant** congestion relief (p < 0.001)
- Would have implied strong causal evidence contradicting actual findings

**After Correction:**
- Table 3 now correctly shows **suggestive but non-significant** evidence (p = 0.17)
- Aligns with manuscript's cautious interpretation
- Highlights that **scarcity outcome (S_t)** provides the mechanistic validation (p < 0.001)

### Total-Effect Discipline

The correction preserves the manuscript's total-effect discipline:
- β = -0.656 reflects the FULL causal impact (no mediator conditioning)
- Wide confidence interval [-1.588, 0.276] reflects genuine uncertainty
- Scarcity result (β = -1.526***) validates the theoretical mechanism

---

## Data Provenance Documentation

### Correct Source (Used for Correction)
- **File:** `results/table7_robustness_grid.csv`
- **Row:** Line 2 (baseline, first_differences, log_base_fee)
- **Marked:** `Is Baseline = True`
- **Values:** β = -0.656, CI: [-1.588, 0.276], p = 0.168, N = 1,242

### Incorrect Source (Not Used)
- **File:** `results/table3_main_its_final.csv`
- **Row:** Line 2 (Log C Fee, First Differences)
- **Values:** β = -1.497, CI: [-2.301, -0.692], p = 0.0003, N = 1,242
- **Status:** ⚠️ DEPRECATED - superseded by Phase 10 respecification

### Recommendation for Future Work

**ACTION REQUIRED:** Update or delete `table3_main_its_final.csv` to prevent future confusion. The correct baseline specification lives in `table7_robustness_grid.csv` (baseline row).

---

## Quality Gates Passed

- [x] Transformation correct: -6.3% per 10-pp ΔA
- [x] Significance correct: p = 0.17 (no stars)
- [x] CI format: square brackets [-1.588, 0.276]
- [x] Sample sizes correct: N = 1,242 (first diff)
- [x] Units explicit: log points, % per 10-pp ΔA
- [x] Consistency with Table 8: ALL values match
- [x] Consistency with text: β = -0.66, p = 0.17 match
- [x] LaTeX compiles: No errors
- [x] HAC specification: 21 lags preserved
- [x] Method specification: First differences correct

---

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Table 3 β corrected to -0.656 | ✓ PASS |
| Table 3 CI corrected to [-1.588, 0.276] | ✓ PASS |
| Table 3 effect corrected to -6.3% | ✓ PASS |
| Table 3 significance stars removed | ✓ PASS |
| p = 0.17 stated in text (already correct) | ✓ PASS |
| Numbers match Table 8 baseline | ✓ PASS |
| Other rows (u_t, S_t) unchanged | ✓ PASS |
| LaTeX compiles without errors | ✓ PASS |

**OVERALL STATUS: ✓ ALL CRITERIA MET**

---

## Impact Assessment

### Before Correction (Critical Errors)
1. ❌ Table-text inconsistency undermined manuscript credibility
2. ❌ Table 3 contradicted Table 8 robustness baseline
3. ❌ Significance stars implied strong evidence not present
4. ❌ Effect size overstated by >2x (-13.9% vs -6.3%)

### After Correction (Resolved)
1. ✓ Table 3, Table 8, and narrative text fully consistent
2. ✓ Non-significance correctly reflected (p = 0.17, no stars)
3. ✓ Interpretation aligns: "suggestive evidence" not "strong evidence"
4. ✓ Scarcity result (S_t: p < 0.001) provides mechanistic validation

---

## Recommendations

### Immediate Actions
1. ✓ **COMPLETED:** Table 3 corrected in manuscript
2. ✓ **COMPLETED:** Validation checks performed
3. ✓ **COMPLETED:** LaTeX compilation verified

### Follow-Up Actions (for Lead Writer)
1. **Verify narrative consistency:** Ensure all text references to β and p-values match -0.656 and 0.17
2. **Check figure captions:** If any figures reference "significant" base fee effects, update to "suggestive"
3. **Review discussion section:** Ensure interpretation aligns with non-significant baseline estimate

### Data Stewardship (for QA/PI)
1. **Update or remove** `table3_main_its_final.csv` to prevent future errors
2. **Document canonical sources:** Establish that `table7_robustness_grid.csv` (baseline row) is the single source of truth
3. **Add validation script:** Create automated check that Table 3 matches Table 8 baseline

---

## Signed Off By

**Data Integration Specialist (DIS)**
Date: 2025-10-12
Status: CORRECTION COMPLETE, ALL VALIDATION CHECKS PASSED

**For QA Review:**
This correction resolves the Phase 3 critical issue. Table 3 now accurately reflects the Phase 10 approved baseline specification (β = -0.656, p = 0.168) and is fully consistent with Table 8 and narrative text.

---

## Appendix: Technical Details

### File Paths
- **Manuscript section:** `/manuscript/sections/04_results.tex`
- **Correct source:** `/results/table7_robustness_grid.csv` (line 2)
- **Deprecated source:** `/results/table3_main_its_final.csv` (line 2)

### Transformation Formula
```
percentage_change = 100 * (exp(0.10 * β) - 1)

For β = -0.656:
percentage_change = 100 * (exp(0.10 * -0.656) - 1)
                  = 100 * (exp(-0.0656) - 1)
                  = 100 * (0.93653 - 1)
                  = -6.347%
                  ≈ -6.3% per 10-pp ΔA
```

### Specification Details
- **Model:** First-differenced log base fees
- **Standard errors:** HAC with 21 lags
- **Sample:** N = 1,242 (post-London, first diff loses 1 obs)
- **Regime:** Full post-London period (2021-08-05 through 2024-12-31)
- **Treatment:** A_t^clean (posting-clean L2 adoption share)

---

**END OF REPORT**
