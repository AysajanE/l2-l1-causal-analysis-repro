#!/usr/bin/env python3
"""
Phase 8: ETH Price Series Integration Pipeline
===============================================

This module implements the ETH price data pipeline for converting
BSTS counterfactual effects from Wei to USD for economic interpretation.

Author: Data Engineering Lead
Date: 2025-01-10
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pyarrow.parquet as pq
import pyarrow as pa
from datetime import datetime, timedelta
import logging
import yaml
from typing import Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default to repo root; can be overridden via class init arg.
WORK_DIR = Path(__file__).resolve().parents[2]


class EthPricePipeline:
    """ETH price data pipeline for counterfactual cost translations."""

    def __init__(self, work_dir: Path = WORK_DIR):
        """Initialize the pipeline."""
        self.work_dir = work_dir
        self.data_dir = work_dir / "data/analytical"
        self.results_dir = work_dir / "results/bsts"

        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized ETH Price Pipeline at {work_dir}")

    def load_panel_data(self) -> pd.DataFrame:
        """Load the core panel data with ETH prices."""
        panel_path = self.data_dir / "core_panel_v1_converted.parquet"

        logger.info(f"Loading panel data from {panel_path}")

        # Read with pyarrow
        table = pq.read_table(panel_path)

        # Convert to pandas
        columns_dict = {}
        for i, name in enumerate(table.schema.names):
            column = table.column(i)
            if name == 'date':
                columns_dict[name] = pd.to_datetime(column.to_pandas())
            else:
                columns_dict[name] = column.to_pandas()

        panel_df = pd.DataFrame(columns_dict)

        # Sort by date
        panel_df = panel_df.sort_values('date')

        logger.info(f"Loaded {len(panel_df)} rows from {panel_df['date'].min()} to {panel_df['date'].max()}")

        return panel_df

    def extract_eth_prices(self, panel_df: pd.DataFrame) -> pd.DataFrame:
        """Extract and process ETH price series from panel."""

        # Select relevant columns
        price_cols = ['date', 'eth_price_usd']
        eth_prices = panel_df[price_cols].copy()

        # Check for missing values
        missing_count = eth_prices['eth_price_usd'].isna().sum()
        if missing_count > 0:
            logger.warning(f"Found {missing_count} missing ETH prices")

            # Set date as index for time-based interpolation
            eth_prices.set_index('date', inplace=True)

            # Interpolate missing values
            eth_prices['eth_price_usd_interpolated'] = eth_prices['eth_price_usd'].interpolate(
                method='time', limit_direction='both'
            )
            eth_prices['is_interpolated'] = eth_prices['eth_price_usd'].isna()
            eth_prices['eth_price_usd'] = eth_prices['eth_price_usd_interpolated']
            eth_prices.drop('eth_price_usd_interpolated', axis=1, inplace=True)

            # Reset index
            eth_prices.reset_index(inplace=True)
        else:
            eth_prices['is_interpolated'] = False

        # Add time-weighted average prices (7-day rolling)
        eth_prices['eth_price_usd_7d_ma'] = eth_prices['eth_price_usd'].rolling(
            window=7, min_periods=1, center=True
        ).mean()

        # Add 30-day rolling average
        eth_prices['eth_price_usd_30d_ma'] = eth_prices['eth_price_usd'].rolling(
            window=30, min_periods=1, center=True
        ).mean()

        # Add price volatility (rolling std)
        eth_prices['eth_price_volatility_7d'] = eth_prices['eth_price_usd'].rolling(
            window=7, min_periods=1
        ).std()

        # Add confidence intervals based on volatility
        z_score_95 = 1.96
        eth_prices['eth_price_usd_lower_95'] = (
            eth_prices['eth_price_usd'] - z_score_95 * eth_prices['eth_price_volatility_7d']
        )
        eth_prices['eth_price_usd_upper_95'] = (
            eth_prices['eth_price_usd'] + z_score_95 * eth_prices['eth_price_volatility_7d']
        )

        # Ensure non-negative prices
        eth_prices['eth_price_usd_lower_95'] = eth_prices['eth_price_usd_lower_95'].clip(lower=0)

        logger.info(f"Extracted ETH prices with {len(eth_prices)} days of data")
        logger.info(f"Price range: ${eth_prices['eth_price_usd'].min():.2f} - ${eth_prices['eth_price_usd'].max():.2f}")

        return eth_prices

    def add_regime_statistics(self, eth_prices: pd.DataFrame, panel_df: pd.DataFrame) -> pd.DataFrame:
        """Add regime-specific price statistics."""

        # Merge regime indicators
        regime_cols = ['date', 'regime_post_london', 'regime_post_merge', 'regime_post_dencun']
        regimes = panel_df[regime_cols].copy()

        eth_prices = eth_prices.merge(regimes, on='date', how='left')

        # Calculate regime-specific statistics
        regime_stats = []

        # Pre-London (everything before London)
        pre_london = eth_prices[eth_prices['regime_post_london'] == 0]
        if len(pre_london) > 0:
            regime_stats.append({
                'regime': 'Pre-London',
                'start_date': pre_london['date'].min(),
                'end_date': pre_london['date'].max(),
                'days': len(pre_london),
                'mean_price': pre_london['eth_price_usd'].mean(),
                'median_price': pre_london['eth_price_usd'].median(),
                'std_price': pre_london['eth_price_usd'].std(),
                'min_price': pre_london['eth_price_usd'].min(),
                'max_price': pre_london['eth_price_usd'].max()
            })

        # London to Merge
        london_merge = eth_prices[
            (eth_prices['regime_post_london'] == 1) &
            (eth_prices['regime_post_merge'] == 0)
        ]
        if len(london_merge) > 0:
            regime_stats.append({
                'regime': 'London-Merge',
                'start_date': london_merge['date'].min(),
                'end_date': london_merge['date'].max(),
                'days': len(london_merge),
                'mean_price': london_merge['eth_price_usd'].mean(),
                'median_price': london_merge['eth_price_usd'].median(),
                'std_price': london_merge['eth_price_usd'].std(),
                'min_price': london_merge['eth_price_usd'].min(),
                'max_price': london_merge['eth_price_usd'].max()
            })

        # Merge to Dencun
        merge_dencun = eth_prices[
            (eth_prices['regime_post_merge'] == 1) &
            (eth_prices['regime_post_dencun'] == 0)
        ]
        if len(merge_dencun) > 0:
            regime_stats.append({
                'regime': 'Merge-Dencun',
                'start_date': merge_dencun['date'].min(),
                'end_date': merge_dencun['date'].max(),
                'days': len(merge_dencun),
                'mean_price': merge_dencun['eth_price_usd'].mean(),
                'median_price': merge_dencun['eth_price_usd'].median(),
                'std_price': merge_dencun['eth_price_usd'].std(),
                'min_price': merge_dencun['eth_price_usd'].min(),
                'max_price': merge_dencun['eth_price_usd'].max()
            })

        # Post-Dencun
        post_dencun = eth_prices[eth_prices['regime_post_dencun'] == 1]
        if len(post_dencun) > 0:
            regime_stats.append({
                'regime': 'Post-Dencun',
                'start_date': post_dencun['date'].min(),
                'end_date': post_dencun['date'].max(),
                'days': len(post_dencun),
                'mean_price': post_dencun['eth_price_usd'].mean(),
                'median_price': post_dencun['eth_price_usd'].median(),
                'std_price': post_dencun['eth_price_usd'].std(),
                'min_price': post_dencun['eth_price_usd'].min(),
                'max_price': post_dencun['eth_price_usd'].max()
            })

        self.regime_stats = pd.DataFrame(regime_stats)

        logger.info("Calculated regime-specific price statistics:")
        for _, row in self.regime_stats.iterrows():
            logger.info(f"  {row['regime']}: ${row['mean_price']:.2f} mean (${row['min_price']:.2f} - ${row['max_price']:.2f})")

        return eth_prices

    def save_price_series(self, eth_prices: pd.DataFrame):
        """Save the ETH price series to parquet."""

        output_path = self.data_dir / "eth_price_series.parquet"

        # Save to parquet
        eth_prices.to_parquet(output_path, index=False)

        logger.info(f"Saved ETH price series to {output_path}")

        # Also save regime statistics as CSV for easy reading
        regime_stats_path = self.results_dir / "eth_price_regime_stats.csv"
        self.regime_stats.to_csv(regime_stats_path, index=False)
        logger.info(f"Saved regime statistics to {regime_stats_path}")

    def generate_metadata(self, eth_prices: pd.DataFrame) -> Dict:
        """Generate metadata for the price series."""

        metadata = {
            'pipeline_version': '1.0.0',
            'generated_at': datetime.now().isoformat(),
            'data_source': 'core_panel_v1_converted.parquet',
            'date_range': {
                'start': str(eth_prices['date'].min().date()),
                'end': str(eth_prices['date'].max().date()),
                'days': len(eth_prices)
            },
            'price_statistics': {
                'mean': float(eth_prices['eth_price_usd'].mean()),
                'median': float(eth_prices['eth_price_usd'].median()),
                'std': float(eth_prices['eth_price_usd'].std()),
                'min': float(eth_prices['eth_price_usd'].min()),
                'max': float(eth_prices['eth_price_usd'].max())
            },
            'interpolation': {
                'method': 'time-based linear',
                'interpolated_days': int(eth_prices['is_interpolated'].sum())
            },
            'columns': list(eth_prices.columns)
        }

        # Save metadata
        metadata_path = self.data_dir / "eth_price_series_metadata.yaml"
        with open(metadata_path, 'w') as f:
            yaml.dump(metadata, f, default_flow_style=False)

        logger.info(f"Saved metadata to {metadata_path}")

        return metadata

    def run(self):
        """Run the complete ETH price pipeline."""

        logger.info("Starting ETH Price Pipeline")
        logger.info("=" * 50)

        # Load panel data
        panel_df = self.load_panel_data()

        # Extract ETH prices
        eth_prices = self.extract_eth_prices(panel_df)

        # Add regime statistics
        eth_prices = self.add_regime_statistics(eth_prices, panel_df)

        # Save price series
        self.save_price_series(eth_prices)

        # Generate metadata
        metadata = self.generate_metadata(eth_prices)

        logger.info("=" * 50)
        logger.info("ETH Price Pipeline completed successfully")

        return eth_prices, metadata


if __name__ == "__main__":
    pipeline = EthPricePipeline()
    eth_prices, metadata = pipeline.run()

    print("\n" + "="*60)
    print("ETH PRICE PIPELINE SUMMARY")
    print("="*60)
    print(f"Date Range: {metadata['date_range']['start']} to {metadata['date_range']['end']}")
    print(f"Total Days: {metadata['date_range']['days']}")
    print(f"Mean Price: ${metadata['price_statistics']['mean']:.2f}")
    print(f"Price Range: ${metadata['price_statistics']['min']:.2f} - ${metadata['price_statistics']['max']:.2f}")
    print(f"Interpolated Days: {metadata['interpolation']['interpolated_days']}")
    print("="*60)
