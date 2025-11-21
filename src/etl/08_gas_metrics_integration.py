#!/usr/bin/env python3
"""
Gas Metrics Integration and Transaction Cost Calculator
========================================================

This module integrates gas metrics from the panel data with ETH prices
to calculate transaction costs in USD for BSTS counterfactual analysis.

Author: Data Engineering Lead
Date: 2025-01-10
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pyarrow.parquet as pq
import logging
import sys
from typing import Dict, Tuple, Optional

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.price_conversions import (
    wei_to_gwei, wei_to_usd, gwei_to_usd,
    calculate_transaction_cost_usd, EthereumUnitConverter
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set working directory
WORK_DIR = Path("/Users/aeziz-local/Research/Projects-05-Ethereum Blockchain Economic Analysis/Causal Influence of L2 Scaling Solutions on Ethereum L1 Mainnet Congestion/L1-L2-causal-influence-analysis/wt/analysis-r")


class GasMetricsIntegrator:
    """Integrates gas metrics with ETH prices to calculate transaction costs."""

    def __init__(self, work_dir: Path = WORK_DIR):
        """Initialize the integrator."""
        self.work_dir = work_dir
        self.data_dir = work_dir / "data/analytical"
        self.results_dir = work_dir / "results/bsts"
        self.converter = EthereumUnitConverter()

        logger.info(f"Initialized Gas Metrics Integrator at {work_dir}")

    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load panel data and ETH prices."""

        # Load converted panel with gas metrics
        panel_path = self.data_dir / "core_panel_v1_converted.parquet"
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
        panel_df = panel_df.sort_values('date')

        # Load ETH price series
        eth_prices = pd.read_parquet(self.data_dir / "eth_price_series.parquet")

        logger.info(f"Loaded panel data: {len(panel_df)} rows")
        logger.info(f"Loaded ETH prices: {len(eth_prices)} rows")

        return panel_df, eth_prices

    def calculate_daily_costs(self, panel_df: pd.DataFrame, eth_prices: pd.DataFrame) -> pd.DataFrame:
        """Calculate daily transaction costs in various units."""

        # Merge panel with ETH prices
        df = panel_df.merge(eth_prices, on='date', how='left', suffixes=('', '_price'))

        # Calculate median gas used per transaction (approximate)
        # Assuming gas_used_total is for all transactions that day
        # We'll use a standard transaction gas amount for per-transaction estimates
        STANDARD_TRANSACTION_GAS = 21_000  # Standard ETH transfer
        COMPLEX_TRANSACTION_GAS = 150_000  # Complex smart contract interaction

        # Calculate costs for different transaction types
        results = pd.DataFrame()
        results['date'] = df['date']

        # Store base fee in different units
        results['base_fee_wei'] = df['base_fee_median_wei']
        results['base_fee_gwei'] = df['base_fee_median_gwei']

        # Use the price series ETH price (not the panel's original one)
        # After merge, the price series columns have '_price' suffix if there was a conflict
        eth_price_col = 'eth_price_usd_price' if 'eth_price_usd_price' in df.columns else 'eth_price_usd'

        # Calculate costs for standard transaction
        results['standard_tx_cost_wei'] = df['base_fee_median_wei'] * STANDARD_TRANSACTION_GAS
        results['standard_tx_cost_gwei'] = wei_to_gwei(results['standard_tx_cost_wei'])
        results['standard_tx_cost_eth'] = self.converter.wei_to_eth(results['standard_tx_cost_wei'])
        results['standard_tx_cost_usd'] = wei_to_usd(
            results['standard_tx_cost_wei'],
            df[eth_price_col]
        )

        # With confidence intervals
        results['standard_tx_cost_usd_lower'] = wei_to_usd(
            results['standard_tx_cost_wei'],
            df['eth_price_usd_lower_95']
        )
        results['standard_tx_cost_usd_upper'] = wei_to_usd(
            results['standard_tx_cost_wei'],
            df['eth_price_usd_upper_95']
        )

        # Calculate costs for complex transaction
        results['complex_tx_cost_wei'] = df['base_fee_median_wei'] * COMPLEX_TRANSACTION_GAS
        results['complex_tx_cost_gwei'] = wei_to_gwei(results['complex_tx_cost_wei'])
        results['complex_tx_cost_eth'] = self.converter.wei_to_eth(results['complex_tx_cost_wei'])
        results['complex_tx_cost_usd'] = wei_to_usd(
            results['complex_tx_cost_wei'],
            df[eth_price_col]
        )

        # Calculate actual daily total gas costs
        if 'gas_used_total' in df.columns:
            results['daily_total_cost_wei'] = df['base_fee_median_wei'] * df['gas_used_total']
            results['daily_total_cost_eth'] = self.converter.wei_to_eth(results['daily_total_cost_wei'])
            results['daily_total_cost_usd'] = wei_to_usd(
                results['daily_total_cost_wei'],
                df[eth_price_col]
            )

            # Average cost per gas unit in USD
            results['cost_per_gas_usd'] = results['daily_total_cost_usd'] / df['gas_used_total']

        # Add metadata columns
        results['eth_price_usd'] = df[eth_price_col]
        results['gas_used_total'] = df.get('gas_used_total', np.nan)
        results['regime_post_london'] = df['regime_post_london']
        results['regime_post_merge'] = df['regime_post_merge']
        results['regime_post_dencun'] = df['regime_post_dencun']

        # Filter to post-London period (when base fee exists)
        results = results[results['regime_post_london'] == 1].copy()

        logger.info(f"Calculated transaction costs for {len(results)} days")

        return results

    def calculate_regime_averages(self, costs_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate average transaction costs by regime."""

        regime_stats = []

        # London to Merge
        london_merge = costs_df[
            (costs_df['regime_post_london'] == 1) &
            (costs_df['regime_post_merge'] == 0)
        ]
        if len(london_merge) > 0:
            regime_stats.append({
                'regime': 'London-Merge',
                'period_start': london_merge['date'].min(),
                'period_end': london_merge['date'].max(),
                'days': len(london_merge),
                'avg_base_fee_gwei': london_merge['base_fee_gwei'].mean(),
                'median_base_fee_gwei': london_merge['base_fee_gwei'].median(),
                'avg_standard_tx_usd': london_merge['standard_tx_cost_usd'].mean(),
                'median_standard_tx_usd': london_merge['standard_tx_cost_usd'].median(),
                'avg_complex_tx_usd': london_merge['complex_tx_cost_usd'].mean(),
                'median_complex_tx_usd': london_merge['complex_tx_cost_usd'].median(),
                'total_daily_cost_usd': london_merge['daily_total_cost_usd'].mean() if 'daily_total_cost_usd' in london_merge else np.nan
            })

        # Merge to Dencun
        merge_dencun = costs_df[
            (costs_df['regime_post_merge'] == 1) &
            (costs_df['regime_post_dencun'] == 0)
        ]
        if len(merge_dencun) > 0:
            regime_stats.append({
                'regime': 'Merge-Dencun',
                'period_start': merge_dencun['date'].min(),
                'period_end': merge_dencun['date'].max(),
                'days': len(merge_dencun),
                'avg_base_fee_gwei': merge_dencun['base_fee_gwei'].mean(),
                'median_base_fee_gwei': merge_dencun['base_fee_gwei'].median(),
                'avg_standard_tx_usd': merge_dencun['standard_tx_cost_usd'].mean(),
                'median_standard_tx_usd': merge_dencun['standard_tx_cost_usd'].median(),
                'avg_complex_tx_usd': merge_dencun['complex_tx_cost_usd'].mean(),
                'median_complex_tx_usd': merge_dencun['complex_tx_cost_usd'].median(),
                'total_daily_cost_usd': merge_dencun['daily_total_cost_usd'].mean() if 'daily_total_cost_usd' in merge_dencun else np.nan
            })

        # Post-Dencun
        post_dencun = costs_df[costs_df['regime_post_dencun'] == 1]
        if len(post_dencun) > 0:
            regime_stats.append({
                'regime': 'Post-Dencun',
                'period_start': post_dencun['date'].min(),
                'period_end': post_dencun['date'].max(),
                'days': len(post_dencun),
                'avg_base_fee_gwei': post_dencun['base_fee_gwei'].mean(),
                'median_base_fee_gwei': post_dencun['base_fee_gwei'].median(),
                'avg_standard_tx_usd': post_dencun['standard_tx_cost_usd'].mean(),
                'median_standard_tx_usd': post_dencun['standard_tx_cost_usd'].median(),
                'avg_complex_tx_usd': post_dencun['complex_tx_cost_usd'].mean(),
                'median_complex_tx_usd': post_dencun['complex_tx_cost_usd'].median(),
                'total_daily_cost_usd': post_dencun['daily_total_cost_usd'].mean() if 'daily_total_cost_usd' in post_dencun else np.nan
            })

        return pd.DataFrame(regime_stats)

    def create_translation_lookup(self, costs_df: pd.DataFrame) -> pd.DataFrame:
        """Create lookup table for common base fee values."""

        # Common base fee values in Gwei
        base_fees_gwei = [10, 20, 30, 40, 50, 75, 100, 150, 200, 300]

        # Use median ETH prices from each regime
        regime_prices = {}
        for regime in ['London-Merge', 'Merge-Dencun', 'Post-Dencun']:
            if regime == 'London-Merge':
                mask = (costs_df['regime_post_london'] == 1) & (costs_df['regime_post_merge'] == 0)
            elif regime == 'Merge-Dencun':
                mask = (costs_df['regime_post_merge'] == 1) & (costs_df['regime_post_dencun'] == 0)
            else:  # Post-Dencun
                mask = costs_df['regime_post_dencun'] == 1

            if mask.any():
                regime_prices[regime] = costs_df.loc[mask, 'eth_price_usd'].median()

        # Create lookup table
        rows = []
        for base_fee in base_fees_gwei:
            for gas_used in [21_000, 50_000, 100_000, 150_000, 200_000]:
                for regime, eth_price in regime_prices.items():
                    base_fee_wei = self.converter.gwei_to_wei(base_fee)
                    cost_wei = base_fee_wei * gas_used
                    cost_eth = self.converter.wei_to_eth(cost_wei)
                    cost_usd = self.converter.eth_to_usd(cost_eth, eth_price)

                    rows.append({
                        'base_fee_gwei': base_fee,
                        'gas_used': gas_used,
                        'regime': regime,
                        'eth_price_usd': eth_price,
                        'cost_wei': cost_wei,
                        'cost_gwei': self.converter.wei_to_gwei(cost_wei),
                        'cost_eth': cost_eth,
                        'cost_usd': cost_usd
                    })

        lookup_df = pd.DataFrame(rows)
        return lookup_df

    def save_results(
        self,
        costs_df: pd.DataFrame,
        regime_stats: pd.DataFrame,
        lookup_df: pd.DataFrame
    ):
        """Save all results to files."""

        # Save daily costs
        costs_path = self.results_dir / "transaction_costs_daily.parquet"
        costs_df.to_parquet(costs_path, index=False)
        logger.info(f"Saved daily costs to {costs_path}")

        # Save CSV version for readability
        costs_csv_path = self.results_dir / "transaction_costs_daily.csv"
        # Select key columns for CSV
        csv_cols = [
            'date', 'base_fee_gwei', 'eth_price_usd',
            'standard_tx_cost_usd', 'complex_tx_cost_usd',
            'daily_total_cost_usd'
        ]
        available_cols = [col for col in csv_cols if col in costs_df.columns]
        costs_df[available_cols].to_csv(costs_csv_path, index=False)
        logger.info(f"Saved daily costs CSV to {costs_csv_path}")

        # Save regime statistics
        regime_path = self.results_dir / "transaction_costs_by_regime.csv"
        regime_stats.to_csv(regime_path, index=False)
        logger.info(f"Saved regime statistics to {regime_path}")

        # Save lookup table
        lookup_path = self.results_dir / "transaction_cost_lookup.csv"
        lookup_df.to_csv(lookup_path, index=False)
        logger.info(f"Saved lookup table to {lookup_path}")

    def run(self):
        """Run the complete gas metrics integration."""

        logger.info("Starting Gas Metrics Integration")
        logger.info("=" * 50)

        # Load data
        panel_df, eth_prices = self.load_data()

        # Calculate daily costs
        costs_df = self.calculate_daily_costs(panel_df, eth_prices)

        # Calculate regime averages
        regime_stats = self.calculate_regime_averages(costs_df)

        # Create translation lookup
        lookup_df = self.create_translation_lookup(costs_df)

        # Save results
        self.save_results(costs_df, regime_stats, lookup_df)

        logger.info("=" * 50)
        logger.info("Gas Metrics Integration completed successfully")

        return costs_df, regime_stats, lookup_df


if __name__ == "__main__":
    integrator = GasMetricsIntegrator()
    costs_df, regime_stats, lookup_df = integrator.run()

    print("\n" + "="*70)
    print("GAS METRICS INTEGRATION SUMMARY")
    print("="*70)

    print("\nREGIME AVERAGE TRANSACTION COSTS:")
    print("-" * 70)
    for _, row in regime_stats.iterrows():
        print(f"\n{row['regime']} ({row['period_start'].date()} to {row['period_end'].date()}):")
        print(f"  Average base fee: {row['avg_base_fee_gwei']:.1f} Gwei")
        print(f"  Standard tx cost: ${row['avg_standard_tx_usd']:.2f} (median: ${row['median_standard_tx_usd']:.2f})")
        print(f"  Complex tx cost: ${row['avg_complex_tx_usd']:.2f} (median: ${row['median_complex_tx_usd']:.2f})")
        if not pd.isna(row['total_daily_cost_usd']):
            print(f"  Daily network total: ${row['total_daily_cost_usd']:,.0f}")

    print("\n" + "="*70)
    print("SAMPLE LOOKUP TABLE (50 Gwei base fee):")
    print("-" * 70)
    sample = lookup_df[lookup_df['base_fee_gwei'] == 50][['gas_used', 'regime', 'cost_usd']]
    print(sample.pivot(index='gas_used', columns='regime', values='cost_usd').to_string())

    print("="*70)