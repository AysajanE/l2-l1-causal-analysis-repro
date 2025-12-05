#!/bin/bash
# Item 10: Check for calibrated claims compliance
# Purpose: Ensure manuscript uses appropriate language matching evidence strength

echo "=== Checking for calibrated claims compliance (Item 10) ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for forbidden phrases
FORBIDDEN_COUNT=0
echo "Checking for forbidden uncalibrated phrases..."

# Extract just the forbidden phrases (not comments) from the file
PHRASES=(
    "\$97.35 billion"
    "\$97.35B"
    "\$79.87B"
    "\$118.45B"
    "\$710.56 million"
    "\$711 million"
    "\$10.6 trillion"
    "\$10.6T"
    "\$96.50 billion"
    "\$96.5B"
    "definitive affirmative"
    "definitively demonstrates"
    "conclusive evidence"
)

# Check main sections
for phrase in "${PHRASES[@]}"; do
    COUNT=$(grep -l "$phrase" sections/0[1-6]_*.tex sections/abstract.tex 2>/dev/null | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        echo -e "${RED}✗ Found forbidden phrase: '$phrase' in $COUNT file(s)${NC}"
        grep -n "$phrase" sections/0[1-6]_*.tex sections/abstract.tex 2>/dev/null
        FORBIDDEN_COUNT=$((FORBIDDEN_COUNT + COUNT))
    fi
done

echo ""
echo "Checking for required calibrated language..."

# Check for required calibrated phrases
REQUIRED_FOUND=0
REQUIRED_TOTAL=6

# Check for updated welfare magnitudes
if grep -q "\$79.6 million" sections/abstract.tex sections/06_conclusion.tex 2>/dev/null; then
    echo -e "${GREEN}✓ Found required: \$79.6 million base-fee welfare estimate${NC}"
    REQUIRED_FOUND=$((REQUIRED_FOUND + 1))
else
    echo -e "${RED}✗ Missing: \$79.6 million base-fee welfare estimate${NC}"
fi

if grep -q "\$92.6 million" sections/abstract.tex sections/06_conclusion.tex 2>/dev/null; then
    echo -e "${GREEN}✓ Found required: \$92.6 million base+tip welfare estimate${NC}"
    REQUIRED_FOUND=$((REQUIRED_FOUND + 1))
else
    echo -e "${YELLOW}⚠ Consider adding: \$92.6 million base+tip welfare estimate${NC}"
fi

# Check for 137-day subset mention
if grep -q "137-day" sections/abstract.tex sections/06_conclusion.tex 2>/dev/null; then
    echo -e "${GREEN}✓ Found required: 137-day subset qualifier${NC}"
    REQUIRED_FOUND=$((REQUIRED_FOUND + 1))
else
    echo -e "${RED}✗ Missing: 137-day subset qualifier${NC}"
fi

# Check for 14.41% coverage mention
if grep -q "14.4\\\\%" sections/abstract.tex sections/06_conclusion.tex 2>/dev/null; then
    echo -e "${GREEN}✓ Found required: 14.41% coverage qualifier${NC}"
    REQUIRED_FOUND=$((REQUIRED_FOUND + 1))
else
    echo -e "${YELLOW}⚠ Consider adding: 14.41% coverage qualifier${NC}"
fi

# Check for "suggestive evidence"
if grep -q "suggestive evidence" sections/abstract.tex sections/04_results.tex 2>/dev/null; then
    echo -e "${GREEN}✓ Found required: 'suggestive evidence' for ITS${NC}"
    REQUIRED_FOUND=$((REQUIRED_FOUND + 1))
else
    echo -e "${RED}✗ Missing: 'suggestive evidence' language for ITS${NC}"
fi

# Check for exploratory labels
if grep -q "Exploratory" sections/04_results.tex 2>/dev/null; then
    echo -e "${GREEN}✓ Found required: 'Exploratory' labels for event study/RDiT${NC}"
    REQUIRED_FOUND=$((REQUIRED_FOUND + 1))
else
    echo -e "${RED}✗ Missing: 'Exploratory' labels for event study/RDiT${NC}"
fi

echo ""
echo "=== SUMMARY ==="

if [ "$FORBIDDEN_COUNT" -eq 0 ] && [ "$REQUIRED_FOUND" -ge 5 ]; then
    echo -e "${GREEN}✓ PASS: Manuscript uses appropriately calibrated claims${NC}"
    echo "  - No forbidden phrases found"
    echo "  - $REQUIRED_FOUND/6 required calibrated phrases present"
    exit 0
else
    echo -e "${RED}✗ FAIL: Manuscript needs calibration updates${NC}"
    if [ "$FORBIDDEN_COUNT" -gt 0 ]; then
        echo "  - Found $FORBIDDEN_COUNT instances of forbidden phrases"
    fi
    if [ "$REQUIRED_FOUND" -lt 5 ]; then
        echo "  - Only $REQUIRED_FOUND/6 required calibrated phrases present"
    fi
    echo ""
    echo "Please update manuscript to:"
    echo "  1. Use \$79.6M base-fee (\$92.6M base+tip) instead of legacy figures"
    echo "  2. Mention 137-day subset and 14.41% coverage"
    echo "  3. Use 'suggestive evidence' for base fee ITS (p=0.17)"
    echo "  4. Label event study and RDiT as 'exploratory'"
    echo "  5. Avoid 'definitive' or 'conclusive' language"
    exit 1
fi
