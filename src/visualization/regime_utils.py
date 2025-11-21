"""
Regime-aware visualization utilities for L1-L2 causal analysis.

This module provides functions for adding consistent regime demarcations,
labels, and styling across all figures in the manuscript.

Author: Visualization Lead
Date: 2025-10-07
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Union
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .plot_config import REGIME_DATES, REGIME_COLORS, REGIME_LABELS


# ============================================================================
# REGIME PERIOD HELPERS
# ============================================================================

def get_regime_periods() -> Dict[str, Tuple[datetime, datetime]]:
    """
    Get regime period start and end dates.

    Returns
    -------
    dict
        Mapping of regime name to (start_date, end_date) tuple

    Examples
    --------
    >>> periods = get_regime_periods()
    >>> periods['london_merge']
    (datetime(2021, 8, 5), datetime(2022, 9, 15))
    """
    dates = {k: pd.to_datetime(v) for k, v in REGIME_DATES.items()}

    # Define analysis period boundaries
    analysis_start = pd.to_datetime('2015-07-30')  # Ethereum mainnet launch
    analysis_end = pd.to_datetime('2024-12-31')    # End of analysis period

    periods = {
        'pre_london': (analysis_start, dates['london']),
        'london_merge': (dates['london'], dates['merge']),
        'merge_dencun': (dates['merge'], dates['dencun']),
        'post_dencun': (dates['dencun'], analysis_end),
    }

    return periods


def get_regime_for_date(date: Union[str, datetime, pd.Timestamp]) -> str:
    """
    Determine which regime a given date falls into.

    Parameters
    ----------
    date : str, datetime, or pd.Timestamp
        Date to classify

    Returns
    -------
    str
        Regime identifier

    Examples
    --------
    >>> get_regime_for_date('2022-01-15')
    'london_merge'
    >>> get_regime_for_date('2024-06-01')
    'post_dencun'
    """
    date = pd.to_datetime(date)
    periods = get_regime_periods()

    for regime, (start, end) in periods.items():
        if start <= date < end:
            return regime

    # If after all regimes, return last regime
    return 'post_dencun'


def filter_data_by_regime(
    df: pd.DataFrame,
    regime: str,
    date_column: str = 'date'
) -> pd.DataFrame:
    """
    Filter DataFrame to specific regime period.

    Parameters
    ----------
    df : pd.DataFrame
        Data with date column
    regime : str
        Regime identifier
    date_column : str
        Name of date column (default: 'date')

    Returns
    -------
    pd.DataFrame
        Filtered data
    """
    periods = get_regime_periods()
    start, end = periods[regime]

    mask = (df[date_column] >= start) & (df[date_column] < end)
    return df[mask].copy()


# ============================================================================
# REGIME BAND VISUALIZATION
# ============================================================================

def add_regime_bands(
    ax: Axes,
    alpha: float = 0.15,
    zorder: int = -100,
    vertical: bool = True,
    extend_limits: bool = True
) -> Dict:
    """
    Add vertical shaded bands for regime periods.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes to add bands to
    alpha : float
        Transparency of bands (default: 0.15)
    zorder : int
        Drawing order (default: -100 for background)
    vertical : bool
        If True, add vertical bands; if False, add horizontal bands
    extend_limits : bool
        If True, extend axis limits to include all regimes

    Returns
    -------
    dict
        Mapping of regime name to Rectangle patch

    Examples
    --------
    >>> fig, ax = plt.subplots()
    >>> ax.plot(dates, values)
    >>> add_regime_bands(ax)
    """
    periods = get_regime_periods()
    patches = {}

    for regime, (start, end) in periods.items():
        color = REGIME_COLORS[regime]

        if vertical:
            # Vertical bands (for time series with dates on x-axis)
            patch = ax.axvspan(
                start, end,
                alpha=alpha,
                color=color,
                zorder=zorder,
                label=REGIME_LABELS[regime]
            )
        else:
            # Horizontal bands (for plots with dates on y-axis)
            patch = ax.axhspan(
                start, end,
                alpha=alpha,
                color=color,
                zorder=zorder,
                label=REGIME_LABELS[regime]
            )

        patches[regime] = patch

    if extend_limits and vertical:
        # Extend x-axis to show all regimes
        ax.set_xlim(periods['pre_london'][0], periods['post_dencun'][1])
    elif extend_limits and not vertical:
        # Extend y-axis to show all regimes
        ax.set_ylim(periods['pre_london'][0], periods['post_dencun'][1])

    return patches


def add_regime_vlines(
    ax: Axes,
    linewidth: float = 1.5,
    linestyle: str = '--',
    color: str = 'black',
    alpha: float = 0.5,
    zorder: int = 100
) -> Dict:
    """
    Add vertical lines at regime transition points.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes to add lines to
    linewidth : float
        Line width (default: 1.5)
    linestyle : str
        Line style (default: '--')
    color : str
        Line color (default: 'black')
    alpha : float
        Line transparency (default: 0.5)
    zorder : int
        Drawing order (default: 100 for foreground)

    Returns
    -------
    dict
        Mapping of regime transition to Line2D object

    Examples
    --------
    >>> fig, ax = plt.subplots()
    >>> ax.plot(dates, values)
    >>> add_regime_vlines(ax)
    """
    lines = {}

    for transition, date in REGIME_DATES.items():
        date = pd.to_datetime(date)
        line = ax.axvline(
            date,
            linewidth=linewidth,
            linestyle=linestyle,
            color=color,
            alpha=alpha,
            zorder=zorder
        )
        lines[transition] = line

    return lines


def add_regime_labels(
    ax: Axes,
    y_position: float = 0.98,
    fontsize: int = 8,
    fontweight: str = 'normal',
    rotation: int = 0,
    verticalalignment: str = 'top',
    horizontalalignment: str = 'center'
) -> Dict:
    """
    Add text labels for regime periods.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes to add labels to
    y_position : float
        Vertical position in axes coordinates (0-1)
    fontsize : int
        Font size (default: 8)
    fontweight : str
        Font weight (default: 'normal')
    rotation : int
        Label rotation in degrees (default: 0)
    verticalalignment : str
        Vertical alignment (default: 'top')
    horizontalalignment : str
        Horizontal alignment (default: 'center')

    Returns
    -------
    dict
        Mapping of regime name to Text object

    Examples
    --------
    >>> fig, ax = plt.subplots()
    >>> ax.plot(dates, values)
    >>> add_regime_bands(ax, alpha=0.1)
    >>> add_regime_labels(ax, y_position=0.95)
    """
    periods = get_regime_periods()
    labels = {}

    for regime, (start, end) in periods.items():
        # Calculate midpoint of regime period
        midpoint = start + (end - start) / 2

        # Add text label
        text = ax.text(
            midpoint, y_position,
            REGIME_LABELS[regime],
            transform=ax.get_xaxis_transform(),
            fontsize=fontsize,
            fontweight=fontweight,
            rotation=rotation,
            verticalalignment=verticalalignment,
            horizontalalignment=horizontalalignment,
            color=REGIME_COLORS[regime],
            bbox=dict(
                boxstyle='round,pad=0.3',
                facecolor='white',
                edgecolor=REGIME_COLORS[regime],
                alpha=0.8
            )
        )

        labels[regime] = text

    return labels


# ============================================================================
# DATE AXIS FORMATTING
# ============================================================================

def format_date_axis(
    ax: Axes,
    axis: str = 'x',
    major_interval: str = 'yearly',
    minor_interval: str = 'quarterly',
    date_format: str = '%Y',
    rotation: int = 0,
    ha: str = 'center'
) -> None:
    """
    Format date axis with appropriate tick intervals and labels.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes to format
    axis : str
        Which axis to format ('x' or 'y')
    major_interval : str
        Major tick interval ('yearly', 'quarterly', 'monthly')
    minor_interval : str
        Minor tick interval ('quarterly', 'monthly', 'weekly', None)
    date_format : str
        Date format string (default: '%Y' for year only)
    rotation : int
        Label rotation in degrees (default: 0)
    ha : str
        Horizontal alignment (default: 'center')

    Examples
    --------
    >>> fig, ax = plt.subplots()
    >>> ax.plot(dates, values)
    >>> format_date_axis(ax, major_interval='yearly', date_format='%Y')
    """
    # Select axis
    if axis == 'x':
        ax_obj = ax.xaxis
    else:
        ax_obj = ax.yaxis

    # Define major tick locators
    major_locators = {
        'yearly': mdates.YearLocator(),
        'quarterly': mdates.MonthLocator([1, 4, 7, 10]),
        'monthly': mdates.MonthLocator(),
    }

    # Define minor tick locators
    minor_locators = {
        'quarterly': mdates.MonthLocator([1, 4, 7, 10]),
        'monthly': mdates.MonthLocator(),
        'weekly': mdates.WeekdayLocator(),
        None: None,
    }

    # Set major locator and formatter
    if major_interval in major_locators:
        ax_obj.set_major_locator(major_locators[major_interval])
        ax_obj.set_major_formatter(mdates.DateFormatter(date_format))

    # Set minor locator
    if minor_interval in minor_locators and minor_locators[minor_interval] is not None:
        ax_obj.set_minor_locator(minor_locators[minor_interval])

    # Rotate labels if requested
    if axis == 'x':
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=rotation, ha=ha)
    else:
        plt.setp(ax.yaxis.get_majorticklabels(), rotation=rotation, ha=ha)


def set_analysis_period_limits(
    ax: Axes,
    axis: str = 'x',
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    padding: float = 0.02
) -> None:
    """
    Set axis limits to analysis period with optional padding.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes to modify
    axis : str
        Which axis to set ('x' or 'y')
    start_date : str, optional
        Start date (default: 2015-07-30)
    end_date : str, optional
        End date (default: 2024-12-31)
    padding : float
        Fraction of range to add as padding (default: 0.02)

    Examples
    --------
    >>> fig, ax = plt.subplots()
    >>> ax.plot(dates, values)
    >>> set_analysis_period_limits(ax, padding=0.05)
    """
    if start_date is None:
        start_date = '2015-07-30'
    if end_date is None:
        end_date = '2024-12-31'

    start = mdates.date2num(pd.to_datetime(start_date))
    end = mdates.date2num(pd.to_datetime(end_date))

    # Add padding
    range_size = end - start
    start -= range_size * padding
    end += range_size * padding

    if axis == 'x':
        ax.set_xlim(start, end)
    else:
        ax.set_ylim(start, end)


# ============================================================================
# REGIME STATISTICS
# ============================================================================

def compute_regime_statistics(
    df: pd.DataFrame,
    value_column: str,
    date_column: str = 'date',
    statistics: List[str] = None
) -> pd.DataFrame:
    """
    Compute statistics for each regime period.

    Parameters
    ----------
    df : pd.DataFrame
        Data with date and value columns
    value_column : str
        Name of column to compute statistics for
    date_column : str
        Name of date column (default: 'date')
    statistics : list, optional
        Statistics to compute (default: ['mean', 'std', 'median', 'min', 'max'])

    Returns
    -------
    pd.DataFrame
        Statistics by regime

    Examples
    --------
    >>> stats = compute_regime_statistics(df, 'gas_used_pct')
    >>> print(stats)
    """
    if statistics is None:
        statistics = ['count', 'mean', 'std', 'median', 'min', 'max']

    # Add regime column
    df = df.copy()
    df['regime'] = df[date_column].apply(get_regime_for_date)

    # Compute statistics by regime
    stats = df.groupby('regime')[value_column].agg(statistics)

    # Reorder by chronological regime order
    regime_order = ['pre_london', 'london_merge', 'merge_dencun', 'post_dencun']
    stats = stats.reindex([r for r in regime_order if r in stats.index])

    return stats


def add_regime_statistics_table(
    fig: Figure,
    stats: pd.DataFrame,
    position: Tuple[float, float, float, float] = (0.65, 0.15, 0.3, 0.2),
    **table_kwargs
):
    """
    Add a table with regime statistics to a figure.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure to add table to
    stats : pd.DataFrame
        Statistics DataFrame from compute_regime_statistics()
    position : tuple
        (left, bottom, width, height) in figure coordinates
    **table_kwargs
        Additional arguments for plt.table()

    Returns
    -------
    matplotlib.table.Table
        Table object

    Examples
    --------
    >>> fig, ax = plt.subplots()
    >>> stats = compute_regime_statistics(df, 'gas_used_pct')
    >>> add_regime_statistics_table(fig, stats[['mean', 'std']])
    """
    # Create axes for table
    ax_table = fig.add_axes(position)
    ax_table.axis('off')

    # Format statistics
    stats_fmt = stats.copy()
    for col in stats_fmt.columns:
        if stats_fmt[col].dtype in [np.float64, np.float32]:
            stats_fmt[col] = stats_fmt[col].map('{:.3f}'.format)

    # Create table
    table = ax_table.table(
        cellText=stats_fmt.values,
        rowLabels=[REGIME_LABELS.get(idx, idx) for idx in stats_fmt.index],
        colLabels=stats_fmt.columns,
        cellLoc='center',
        loc='center',
        **table_kwargs
    )

    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.5)

    return table


# ============================================================================
# REGIME COLOR MAPPING
# ============================================================================

def regime_color_map(
    data: pd.Series,
    date_column: str = None
) -> pd.Series:
    """
    Create a Series mapping each observation to its regime color.

    Parameters
    ----------
    data : pd.Series
        Series with datetime index or values
    date_column : str, optional
        If data is a DataFrame, column to use for dates

    Returns
    -------
    pd.Series
        Series of color codes

    Examples
    --------
    >>> colors = regime_color_map(df.index)
    >>> ax.scatter(df.index, df['value'], c=colors)
    """
    if date_column is not None:
        dates = data[date_column]
    else:
        dates = data

    colors = dates.apply(lambda d: REGIME_COLORS[get_regime_for_date(d)])
    return colors


def create_regime_legend(
    ax: Axes,
    loc: str = 'best',
    ncol: int = 1,
    **legend_kwargs
):
    """
    Create a legend for regime periods.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes to add legend to
    loc : str
        Legend location (default: 'best')
    ncol : int
        Number of columns (default: 1)
    **legend_kwargs
        Additional arguments for ax.legend()

    Returns
    -------
    matplotlib.legend.Legend
        Legend object

    Examples
    --------
    >>> fig, ax = plt.subplots()
    >>> add_regime_bands(ax)
    >>> create_regime_legend(ax, loc='upper right', ncol=2)
    """
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor=REGIME_COLORS[regime], label=REGIME_LABELS[regime], alpha=0.5)
        for regime in ['pre_london', 'london_merge', 'merge_dencun', 'post_dencun']
    ]

    legend = ax.legend(
        handles=legend_elements,
        loc=loc,
        ncol=ncol,
        **legend_kwargs
    )

    return legend


if __name__ == '__main__':
    # Demonstration of regime utilities
    print("L1-L2 Causal Analysis - Regime Utilities")
    print("=" * 60)

    periods = get_regime_periods()
    print("\nRegime Periods:")
    for regime, (start, end) in periods.items():
        print(f"  {REGIME_LABELS[regime]:15s}: {start.date()} to {end.date()}")

    print("\nExample date classifications:")
    test_dates = ['2020-01-01', '2022-01-01', '2023-01-01', '2024-06-01']
    for date in test_dates:
        regime = get_regime_for_date(date)
        print(f"  {date}: {REGIME_LABELS[regime]}")

    print("\nRegime Colors:")
    for regime, color in REGIME_COLORS.items():
        print(f"  {REGIME_LABELS[regime]:15s}: {color}")
