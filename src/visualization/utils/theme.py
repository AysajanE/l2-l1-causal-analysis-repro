#!/usr/bin/env python3
"""
Publication-Quality Theme Configuration
========================================
Author: Visualization Lead
Date: 2025-01-09

This module provides consistent theming for all figures in the L1-L2 causal analysis project.
Ensures publication-quality output with regime awareness and colorblind-friendly palettes.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from typing import Optional, Dict, Tuple
import numpy as np
from datetime import datetime

# Define regime boundaries
REGIME_DATES = {
    'london': datetime(2021, 8, 5),
    'merge': datetime(2022, 9, 15),
    'dencun': datetime(2024, 3, 13)
}

# Regime colors (colorblind-friendly)
REGIME_COLORS = {
    'pre_london': '#E8E8E8',      # Light gray
    'london_merge': '#A8D5E8',    # Light blue
    'merge_dencun': '#A8E8A8',    # Light green
    'post_dencun': '#FFD9A8'      # Light orange
}

# Main color palette (colorblind-friendly)
MAIN_COLORS = [
    '#0173B2',  # Blue
    '#DE8F05',  # Orange
    '#029E73',  # Green
    '#CC78BC',  # Purple
    '#ECE133',  # Yellow
    '#56B4E9',  # Light blue
    '#F0E442',  # Light yellow
    '#D55E00',  # Dark orange
]

def set_publication_theme():
    """
    Set matplotlib parameters for publication-quality figures.

    Uses sans-serif fonts for better screen rendering and journal compatibility.
    Sets high DPI for crisp output.
    """
    # Reset to default first
    plt.rcdefaults()

    # Set style
    plt.style.use('default')

    # Figure and DPI settings
    plt.rcParams['figure.dpi'] = 100  # Display DPI
    plt.rcParams['savefig.dpi'] = 300  # Save DPI
    plt.rcParams['savefig.format'] = 'png'
    plt.rcParams['savefig.bbox'] = 'tight'
    plt.rcParams['savefig.pad_inches'] = 0.1

    # Font settings (sans-serif for better rendering)
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.titlesize'] = 11
    plt.rcParams['axes.labelsize'] = 10
    plt.rcParams['xtick.labelsize'] = 9
    plt.rcParams['ytick.labelsize'] = 9
    plt.rcParams['legend.fontsize'] = 9
    plt.rcParams['figure.titlesize'] = 12

    # Axes settings
    plt.rcParams['axes.linewidth'] = 0.8
    plt.rcParams['axes.edgecolor'] = '#333333'
    plt.rcParams['axes.labelcolor'] = '#333333'
    plt.rcParams['axes.axisbelow'] = True
    plt.rcParams['axes.grid'] = True
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.spines.right'] = False

    # Grid settings
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['grid.color'] = '#CCCCCC'
    plt.rcParams['grid.linestyle'] = '-'
    plt.rcParams['grid.linewidth'] = 0.5

    # Tick settings
    plt.rcParams['xtick.color'] = '#333333'
    plt.rcParams['ytick.color'] = '#333333'
    plt.rcParams['xtick.major.size'] = 4
    plt.rcParams['ytick.major.size'] = 4
    plt.rcParams['xtick.major.width'] = 0.8
    plt.rcParams['ytick.major.width'] = 0.8

    # Legend settings
    plt.rcParams['legend.frameon'] = True
    plt.rcParams['legend.framealpha'] = 0.9
    plt.rcParams['legend.edgecolor'] = '#CCCCCC'
    plt.rcParams['legend.fancybox'] = False

    # Line settings
    plt.rcParams['lines.linewidth'] = 1.5
    plt.rcParams['lines.markersize'] = 6

    # Patch settings
    plt.rcParams['patch.linewidth'] = 0.5
    plt.rcParams['patch.edgecolor'] = '#333333'

    # Set seaborn palette
    sns.set_palette(MAIN_COLORS)

    # Disable seaborn styling to keep our custom settings
    sns.set_style(None)


def add_regime_bands(ax, y_range: Optional[Tuple[float, float]] = None,
                    alpha: float = 0.3, labels: bool = True):
    """
    Add regime-aware background bands to a plot.

    Parameters
    ----------
    ax : matplotlib axis
        The axis to add bands to
    y_range : tuple, optional
        Y-axis range for bands. If None, uses current ylim
    alpha : float
        Transparency of regime bands
    labels : bool
        Whether to add regime labels at top
    """
    if y_range is None:
        y_range = ax.get_ylim()

    # Pre-London (up to London)
    ax.axvspan(datetime(2015, 1, 1), REGIME_DATES['london'],
              alpha=alpha, color=REGIME_COLORS['pre_london'],
              zorder=0, label='Pre-London' if labels else '')

    # London to Merge
    ax.axvspan(REGIME_DATES['london'], REGIME_DATES['merge'],
              alpha=alpha, color=REGIME_COLORS['london_merge'],
              zorder=0, label='London-Merge' if labels else '')

    # Merge to Dencun
    ax.axvspan(REGIME_DATES['merge'], REGIME_DATES['dencun'],
              alpha=alpha, color=REGIME_COLORS['merge_dencun'],
              zorder=0, label='Merge-Dencun' if labels else '')

    # Post-Dencun
    ax.axvspan(REGIME_DATES['dencun'], datetime(2025, 1, 1),
              alpha=alpha, color=REGIME_COLORS['post_dencun'],
              zorder=0, label='Post-Dencun' if labels else '')

    # Add vertical lines at transitions
    for event_name, event_date in REGIME_DATES.items():
        ax.axvline(event_date, color='#666666', linestyle='--',
                  linewidth=0.8, alpha=0.5, zorder=1)

        # Add event labels at top if requested
        if labels:
            y_pos = y_range[1] - (y_range[1] - y_range[0]) * 0.02
            ax.text(event_date, y_pos, event_name.capitalize(),
                   fontsize=8, ha='center', va='top',
                   color='#666666', weight='bold')


def add_regime_labels(ax, y_position: str = 'top'):
    """
    Add regime labels to the plot.

    Parameters
    ----------
    ax : matplotlib axis
        The axis to add labels to
    y_position : str
        Position for labels ('top', 'middle', 'bottom')
    """
    y_range = ax.get_ylim()

    if y_position == 'top':
        y_pos = y_range[1] - (y_range[1] - y_range[0]) * 0.05
    elif y_position == 'middle':
        y_pos = (y_range[0] + y_range[1]) / 2
    else:  # bottom
        y_pos = y_range[0] + (y_range[1] - y_range[0]) * 0.05

    # Add centered labels for each regime period
    regime_centers = {
        'Pre-London': (datetime(2019, 1, 1), REGIME_DATES['london']),
        'London': (REGIME_DATES['london'], REGIME_DATES['merge']),
        'Merge': (REGIME_DATES['merge'], REGIME_DATES['dencun']),
        'Dencun': (REGIME_DATES['dencun'], datetime(2024, 12, 31))
    }

    for regime_name, (start, end) in regime_centers.items():
        center = start + (end - start) / 2
        ax.text(center, y_pos, regime_name,
               ha='center', va='center',
               fontsize=9, color='#333333',
               bbox=dict(boxstyle='round,pad=0.3',
                        facecolor='white',
                        edgecolor='#CCCCCC',
                        alpha=0.8))


def format_date_axis(ax, years_only: bool = False):
    """
    Format date axis with appropriate labels.

    Parameters
    ----------
    ax : matplotlib axis
        The axis to format
    years_only : bool
        If True, only show years. Otherwise show month-year
    """
    if years_only:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_minor_locator(mdates.MonthLocator((1, 7)))
    else:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.xaxis.set_minor_locator(mdates.MonthLocator())

    # Rotate labels for better readability
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')


def get_figure_size(figure_type: str = 'single') -> Tuple[float, float]:
    """
    Get appropriate figure size for publication.

    Parameters
    ----------
    figure_type : str
        Type of figure ('single', 'double', 'full')

    Returns
    -------
    tuple
        (width, height) in inches
    """
    sizes = {
        'single': (7.5, 5),      # Single column width
        'double': (15, 8),       # Double column width
        'full': (15, 10),        # Full page
        'square': (7.5, 7.5),    # Square figure
        'wide': (15, 5),         # Wide but short
        'tall': (7.5, 10),       # Tall single column
    }
    return sizes.get(figure_type, (7.5, 5))


def save_figure(fig, filename: str, formats: list = None, dpi: int = 300):
    """
    Save figure in multiple formats.

    Parameters
    ----------
    fig : matplotlib figure
        Figure to save
    filename : str
        Base filename (without extension)
    formats : list
        List of formats to save ['png', 'pdf', 'svg']
    dpi : int
        DPI for raster formats
    """
    if formats is None:
        formats = ['png', 'pdf']

    for fmt in formats:
        save_path = f"{filename}.{fmt}"
        if fmt in ['png', 'jpg']:
            fig.savefig(save_path, format=fmt, dpi=dpi,
                       bbox_inches='tight', pad_inches=0.1)
        else:
            fig.savefig(save_path, format=fmt,
                       bbox_inches='tight', pad_inches=0.1)
        print(f"Saved: {save_path}")


def create_colormap_regime_aware() -> Dict:
    """
    Create colormaps that are regime-aware.

    Returns
    -------
    dict
        Dictionary of colormaps for different purposes
    """
    return {
        'diverging': plt.cm.RdBu_r,
        'sequential': plt.cm.viridis,
        'qualitative': MAIN_COLORS,
        'regime': REGIME_COLORS
    }