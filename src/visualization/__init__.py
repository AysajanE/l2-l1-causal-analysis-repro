"""
Visualization module for L1-L2 Causal Influence Analysis.

This package provides publication-quality, regime-aware visualization tools
for the Ethereum L1-L2 causal analysis manuscript.

Modules
-------
plot_config
    Publication-quality matplotlib configuration and styling
regime_utils
    Regime-aware visualization utilities (bands, labels, colors)
plot_timeseries
    Time series plotting with regime demarcations
plot_treatment_support
    Treatment distribution visualization (ridgeline, violin, boxplot)
plot_event_study
    Event study coefficient plots with confidence intervals
plot_bsts_effects
    BSTS counterfactual path visualization
plot_robustness_tornado
    Robustness tornado and forest plots
captions
    Figure caption management and LaTeX export

Usage
-----
Import the configuration and utilities at the start of any visualization script:

    from src.visualization import (
        set_publication_style,
        add_regime_bands,
        plot_single_timeseries,
        get_caption
    )

    # Set publication style
    set_publication_style(dpi=300)

    # Create figure
    fig, ax = plot_single_timeseries(df, value_column='gas_used_pct')

    # Get caption
    caption = get_caption('figure_02_outcome_timeseries')

Author: Visualization Lead
Date: 2025-10-07
"""

# Version
__version__ = '1.0.0'

# Core configuration
from .plot_config import (
    set_publication_style,
    reset_style,
    get_regime_color,
    get_figure_size,
    save_figure,
    get_colorblind_palette,
    REGIME_COLORS,
    REGIME_DATES,
    REGIME_LABELS,
    FIGURE_SIZES,
    FONT_SIZES,
    DPI_SETTINGS,
)

# Regime utilities
from .regime_utils import (
    add_regime_bands,
    add_regime_vlines,
    add_regime_labels,
    format_date_axis,
    get_regime_periods,
    get_regime_for_date,
    filter_data_by_regime,
    compute_regime_statistics,
    regime_color_map,
    create_regime_legend,
)

# Time series plotting
from .plot_timeseries import (
    plot_single_timeseries,
    plot_multi_panel_timeseries,
    plot_timeseries_with_stats,
    plot_treatment_evolution,
)

# Treatment support visualization
from .plot_treatment_support import (
    plot_treatment_ridgeline,
    plot_treatment_boxplot,
    plot_treatment_violin,
    plot_treatment_histogram_grid,
)

# Event study visualization
from .plot_event_study import (
    plot_event_study_coefficients,
    plot_event_study_with_pretrend_test,
    plot_cumulative_effects,
    plot_event_study_multi_outcome,
)

# BSTS visualization
from .plot_bsts_effects import (
    plot_bsts_counterfactual,
    plot_bsts_pointwise_effects,
    plot_bsts_cumulative_effects,
    plot_bsts_full_analysis,
)

# Robustness visualization
from .plot_robustness_tornado import (
    plot_robustness_tornado,
    plot_robustness_forest,
    plot_robustness_summary_table,
    plot_specification_curve,
)

# Caption management
from .captions import (
    get_caption,
    get_title,
    get_short_caption,
    export_all_captions,
    list_all_figures,
    validate_figure_id,
    FIGURE_CAPTIONS,
)

# Define public API
__all__ = [
    # Configuration
    'set_publication_style',
    'reset_style',
    'get_regime_color',
    'get_figure_size',
    'save_figure',
    'get_colorblind_palette',

    # Constants
    'REGIME_COLORS',
    'REGIME_DATES',
    'REGIME_LABELS',
    'FIGURE_SIZES',
    'FONT_SIZES',
    'DPI_SETTINGS',

    # Regime utilities
    'add_regime_bands',
    'add_regime_vlines',
    'add_regime_labels',
    'format_date_axis',
    'get_regime_periods',
    'get_regime_for_date',
    'filter_data_by_regime',
    'compute_regime_statistics',
    'regime_color_map',
    'create_regime_legend',

    # Time series
    'plot_single_timeseries',
    'plot_multi_panel_timeseries',
    'plot_timeseries_with_stats',
    'plot_treatment_evolution',

    # Treatment support
    'plot_treatment_ridgeline',
    'plot_treatment_boxplot',
    'plot_treatment_violin',
    'plot_treatment_histogram_grid',

    # Event study
    'plot_event_study_coefficients',
    'plot_event_study_with_pretrend_test',
    'plot_cumulative_effects',
    'plot_event_study_multi_outcome',

    # BSTS
    'plot_bsts_counterfactual',
    'plot_bsts_pointwise_effects',
    'plot_bsts_cumulative_effects',
    'plot_bsts_full_analysis',

    # Robustness
    'plot_robustness_tornado',
    'plot_robustness_forest',
    'plot_robustness_summary_table',
    'plot_specification_curve',

    # Captions
    'get_caption',
    'get_title',
    'get_short_caption',
    'export_all_captions',
    'list_all_figures',
    'validate_figure_id',
    'FIGURE_CAPTIONS',
]
