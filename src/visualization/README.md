# Visualization Infrastructure

**L1-L2 Causal Influence Analysis**
**Version:** 1.0.0
**Date:** 2025-10-07

---

## Overview

This directory contains the visualization infrastructure for producing publication-quality, regime-aware figures for the L1-L2 causal analysis manuscript. The system ensures consistent styling, proper regime demarcation, and reproducible figure generation across all analysis phases.

## Directory Structure

```
src/visualization/
├── __init__.py                    # Package initialization and exports
├── README.md                      # This file
├── plot_config.py                 # Matplotlib configuration and styling
├── regime_utils.py                # Regime-aware visualization utilities
├── plot_timeseries.py             # Time series plotting functions
├── plot_treatment_support.py      # Treatment distribution plots
├── plot_event_study.py            # Event study coefficient plots
├── plot_bsts_effects.py           # BSTS counterfactual visualizations
├── plot_robustness_tornado.py     # Robustness tornado plots
└── captions.py                    # Figure caption management
```

## Quick Start

```python
# Import key functions
from src.visualization import (
    set_publication_style,
    plot_single_timeseries,
    get_caption
)
import pandas as pd

# Set publication style (do this once at start)
set_publication_style(dpi=300, use_latex=False)

# Load data
df = pd.read_parquet('data/core_panel_v1.parquet')

# Create figure
fig, ax = plot_single_timeseries(
    df,
    date_column='date',
    value_column='gas_used_pct',
    ylabel='Gas Used (%)',
    title='Ethereum L1 Utilization Over Time',
    output_path='results/figures/figure_02_utilization'
)

# Get caption
caption = get_caption('figure_02_outcome_timeseries')
print(caption)
```

## Core Components

### 1. Configuration (`plot_config.py`)

Central matplotlib configuration for publication quality:
- 300 DPI resolution
- Serif fonts (Computer Modern Roman, Times New Roman)
- Regime color palette (colorblind-friendly)
- Standard figure dimensions
- Multi-format export (PDF + PNG)

### 2. Regime Utilities (`regime_utils.py`)

Functions for regime-aware visualizations:
- `add_regime_bands()`: Shaded background regions
- `add_regime_vlines()`: Vertical transition lines
- `add_regime_labels()`: Text labels for regimes
- `format_date_axis()`: Proper date formatting
- `compute_regime_statistics()`: Regime-specific stats

### 3. Figure Templates

Five specialized plotting modules:
- **Time Series** (`plot_timeseries.py`): Multi-panel time series with regime bands
- **Treatment Support** (`plot_treatment_support.py`): Ridgeline, violin, boxplot distributions
- **Event Study** (`plot_event_study.py`): Lead-lag coefficients with confidence intervals
- **BSTS Effects** (`plot_bsts_effects.py`): Counterfactual paths and causal effects
- **Robustness** (`plot_robustness_tornado.py`): Tornado plots and forest plots

### 4. Caption Management (`captions.py`)

Centralized figure captions with LaTeX export:
- `get_caption()`: Retrieve formatted captions
- `export_all_captions()`: Export to LaTeX/Markdown
- `FIGURE_CAPTIONS`: Dictionary of all captions

## Regime Definitions

| Regime | Period | Color | Key Change |
|--------|--------|-------|------------|
| **Pre-London** | Before Aug 5, 2021 | Gray `#969696` | Pre-EIP-1559 |
| **London-Merge** | Aug 5, 2021 – Sep 15, 2022 | Blue `#4292C6` | EIP-1559 base fee |
| **Merge-Dencun** | Sep 15, 2022 – Mar 13, 2024 | Green `#41AB5D` | Proof-of-Stake |
| **Post-Dencun** | After Mar 13, 2024 | Red `#EF3B2C` | EIP-4844 blobs |

## Publication Standards

- **Resolution:** 300 DPI (print quality)
- **Formats:** PDF (vector) + PNG (raster)
- **Dimensions:** 3.5" (single column) or 7.5" (double column)
- **Typography:** Serif fonts, 9-11pt sizes
- **Colors:** Colorblind-friendly, WCAG AA compliant
- **Accessibility:** Alternative encodings (line styles, markers)

## Example Usage

### Multi-Panel Time Series

```python
from src.visualization import plot_multi_panel_timeseries

fig, axes = plot_multi_panel_timeseries(
    df,
    value_columns=['gas_used_pct', 'base_fee_gwei', 'txn_count'],
    ylabels=['Utilization (%)', 'Base Fee (Gwei)', 'Transactions'],
    output_path='results/figures/figure_02_timeseries'
)
```

### Event Study Plot

```python
from src.visualization import plot_event_study_coefficients

fig, ax = plot_event_study_coefficients(
    coefficients=results['beta'],
    ci_lower=results['ci_lower'],
    ci_upper=results['ci_upper'],
    output_path='results/figures/figure_08_event_study'
)
```

### BSTS Counterfactual

```python
from src.visualization import plot_bsts_full_analysis

fig, axes = plot_bsts_full_analysis(
    dates=df['date'],
    observed=df['outcome'],
    counterfactual_mean=bsts['cf_mean'],
    counterfactual_lower=bsts['cf_lower'],
    counterfactual_upper=bsts['cf_upper'],
    pointwise_effects=bsts['effects'],
    effects_lower=bsts['effects_lower'],
    effects_upper=bsts['effects_upper'],
    intervention_date='2022-09-15',
    output_path='results/figures/figure_09_bsts'
)
```

### Robustness Tornado

```python
from src.visualization import plot_robustness_tornado

fig, ax = plot_robustness_tornado(
    estimates=specs['estimate'],
    ci_lower=specs['ci_lower'],
    ci_upper=specs['ci_upper'],
    baseline_estimate=0.152,
    output_path='results/figures/figure_10_robustness'
)
```

## Documentation

- **Style Guide:** `docs/visualization/style_guide.md` - Comprehensive styling standards
- **Figure Checklist:** `docs/visualization/figure_checklist.md` - QA verification
- **Module Docstrings:** Each `.py` file has detailed documentation

## Dependencies

- matplotlib >= 3.5
- seaborn >= 0.11
- pandas >= 1.3
- numpy >= 1.21
- scipy >= 1.7

## Figure Checklist

Before finalizing any figure:
1. ✓ Resolution ≥ 300 DPI
2. ✓ PDF and PNG formats exported
3. ✓ Regime colors correct
4. ✓ All axes labeled with units
5. ✓ Legend present and legible
6. ✓ No overlapping text
7. ✓ Colorblind-safe palette
8. ✓ Caption added to `captions.py`

See `docs/visualization/figure_checklist.md` for complete verification.

---

**Maintainer:** Visualization Lead
**Version:** 1.0.0
**Last Updated:** 2025-10-07
