#!/bin/bash
#
# Wait for core_panel_v1.parquet and generate documentation
#
# This script monitors for the panel file creation and automatically
# generates all required documentation once it's available.
#
# Author: Reproducibility Lead
# Phase: 4 - Panel Assembly & Snapshotting

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PANEL_PATH="$PROJECT_ROOT/data/core_panel_v1/core_panel_v1.parquet"
WAIT_INTERVAL=5  # seconds
MAX_WAIT=600     # 10 minutes

echo "=================================================="
echo "Phase 4: Panel Documentation Generator"
echo "=================================================="
echo ""
echo "Configuration:"
echo "  Panel path: $PANEL_PATH"
echo "  Check interval: ${WAIT_INTERVAL}s"
echo "  Max wait time: ${MAX_WAIT}s"
echo ""

# Function to check if panel exists
check_panel() {
    if [ -f "$PANEL_PATH" ]; then
        return 0
    else
        return 1
    fi
}

# Wait for panel to be created
echo "Waiting for Data Engineer to create panel..."
elapsed=0

while ! check_panel; do
    if [ $elapsed -ge $MAX_WAIT ]; then
        echo ""
        echo "✗ Timeout: Panel not created after ${MAX_WAIT} seconds"
        echo "  The Data Engineer may still be working on panel assembly."
        echo "  You can:"
        echo "    1. Run this script again later"
        echo "    2. Run documentation manually: python src/reproducibility/generate_panel_docs.py"
        exit 1
    fi

    echo -ne "\r  Waiting... ${elapsed}s"
    sleep $WAIT_INTERVAL
    elapsed=$((elapsed + WAIT_INTERVAL))
done

echo ""
echo "✓ Panel file detected!"
echo ""

# Wait a bit more to ensure file write is complete
echo "Waiting for file to stabilize..."
sleep 2

# Generate documentation
echo ""
echo "Generating documentation..."
echo "--------------------------------------------------"
python "$SCRIPT_DIR/generate_panel_docs.py" --panel-path "$PANEL_PATH" --version 1

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✓ Phase 4 Documentation Complete!"
    echo "=================================================="
    echo ""
    echo "Generated artifacts:"
    ls -lh "$PROJECT_ROOT/data/core_panel_v1/core_panel_v1"*
    echo ""
    echo "Ready for QA validation and subsequent phases."
else
    echo ""
    echo "✗ Documentation generation failed"
    exit 1
fi
