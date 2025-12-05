# Item 10 Calibration Summary
## Manuscript Claims Calibrated to Match Evidence Strength
**Date:** 2025-10-18
**Frozen Dataset Hash:** 52f4ed01663228ae80cd53dca9bac4bfdff6f6a197443bb79d7434a603fe2423

## Overview
Successfully calibrated manuscript claims to match evidence strength per revision implementation plan Item 10.

## Key Changes Implemented

### 1. Welfare Estimate Correction
- **OLD:** $97.35 billion over 137 days
- **NEW:** $79.6 million (base fees) / $92.6 million (base+tip) over 137-day subset (14.41% of 951 pre-Dencun days)
- **Rationale:** Previous estimate inflated; new estimate reflects limited temporal coverage and dual dollarization series

### 2. Precision Calibration for ITS
- **Maintained:** "Suggestive evidence" language for base fee effect (p≈0.17)
- **Emphasized:** Strong scarcity mechanism (S_t significant, p<0.001)
- **Added:** "Limited precision" qualifiers where appropriate

### 3. Exploratory Analysis Labels
- **Event Study:** Now labeled "Exploratory Analysis"
- **RDiT:** Now labeled "Exploratory"
- **BSTS:** Marked as exploratory with temporal coverage caveats
- **ITS:** Marked as "Confirmatory Analysis"

### 4. Removed Overstated Language
- **Removed:** "definitive affirmative" from conclusion
- **Removed:** "conclusive evidence" claims
- **Added:** "directional negative effect" with appropriate nuance

## Files Modified
1. `abstract.tex` - Updated welfare estimates, added temporal qualifiers
2. `06_conclusion.tex` - Removed definitive language, added nuance
3. `04_results.tex` - Added confirmatory/exploratory labels, updated tables
4. `05_discussion.tex` - Updated welfare narrative to $79.6M (base) / $92.6M (base+tip)

## Validation Tools Created
1. `forbidden_phrases.txt` - List of phrases that should NOT appear
2. `check_calibrated_claims.sh` - Automated CI check script

## Validation Results
✓ **PASS:** Manuscript now uses appropriately calibrated claims
- No forbidden phrases found
- All required calibrated phrases present
- Exploratory analyses properly labeled
- Temporal coverage limitations acknowledged

## Key Messages Preserved
Despite calibration, the manuscript still demonstrates:
1. **Directional evidence** of L2 congestion relief
2. **Strong mechanistic validation** through scarcity channel (p<0.001)
3. **Economically meaningful** welfare gains ($79.6M base-only / $92.6M base+tip) despite limited scope
4. **Robust sign consistency** (87% negative across specifications)
5. **Policy relevance** for L2 infrastructure investment

## Compliance Check Command
```bash
cd project_A_effects/manuscript
./check_calibrated_claims.sh
```

## Next Steps
- Ensure all co-authors aware of calibrated language
- Update any supplementary materials to match
- Add CI hook to prevent regression to uncalibrated claims
- Consider expanding analysis to full 951-day period in future work
