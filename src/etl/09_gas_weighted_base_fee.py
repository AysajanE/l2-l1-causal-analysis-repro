#!/usr/bin/env python3
"""
Gas-Weighted Base Fee Computation
==================================

Computes daily gas-weighted base fees from block-level data.

Formula:
BF_obs_t = sum_b(base_fee_gwei_b × gas_used_b) / sum_b(gas_used_b)

This ensures proper weighting of fees by actual gas consumption,
critical for accurate welfare calculations.

Author: BSTS-to-Dollar Pipeline Specialist
Date: 2025-10-18
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pyarrow.parquet as pq
import logging
import sys
from typing import Optional, Tuple

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from units import EthereumUnits

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class GasWeightedBaseFeeCalculator:
    """Calculate gas-weighted base fees from Ethereum block data."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize calculator with data directory."""
        self.data_dir = data_dir or PROJECT_ROOT / "data"
        self.units = EthereumUnits()
        logger.info(f"Initialized Gas-Weighted Base Fee Calculator with data_dir: {self.data_dir}")

    def load_block_data(self, start_date: str = "2021-08-05", end_date: str = "2024-03-13") -> pd.DataFrame:
        """
        Load block-level data with base fees and gas usage.

        Note: This function expects block-level data to be available.
        If not available, we'll need to fetch it from Dune or another source.

        Args:
            start_date: Start date (London hard fork)
            end_date: End date (Dencun upgrade)

        Returns:
            DataFrame with block-level data
        """
        # Try to load existing block data if available
        block_data_paths = [
            self.data_dir / "blocks" / "ethereum_blocks.parquet",
            self.data_dir / "raw" / "blocks.parquet",
            self.data_dir / "ethereum" / "blocks.parquet"
        ]

        for path in block_data_paths:
            if path.exists():
                logger.info(f"Loading block data from {path}")
                df = pd.read_parquet(path)

                # Filter date range
                df['date'] = pd.to_datetime(df['timestamp']).dt.date
                df = df[(df['date'] >= pd.to_datetime(start_date).date()) &
                       (df['date'] <= pd.to_datetime(end_date).date())]

                return df

        # If no block data found, create placeholder with warning
        logger.warning("Block-level data not found! Creating placeholder structure.")
        logger.warning("To compute accurate gas-weighted fees, you need to provide:")
        logger.warning("  - Block number")
        logger.warning("  - Block timestamp")
        logger.warning("  - Base fee per gas (in Wei or Gwei)")
        logger.warning("  - Gas used per block")
        logger.warning("  - Gas limit per block (optional)")

        # Return empty DataFrame with expected schema
        return pd.DataFrame({
            'block_number': pd.Series(dtype='int64'),
            'timestamp': pd.Series(dtype='datetime64[ns]'),
            'base_fee_per_gas': pd.Series(dtype='float64'),  # in Wei
            'gas_used': pd.Series(dtype='int64'),
            'gas_limit': pd.Series(dtype='int64'),
            'date': pd.Series(dtype='object')
        })

    def compute_daily_gas_weighted_base_fee(self, blocks_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute daily gas-weighted base fee from block data.

        Formula:
        BF_obs_t = sum_b(base_fee_gwei_b × gas_used_b) / sum_b(gas_used_b)

        Args:
            blocks_df: DataFrame with block-level data

        Returns:
            DataFrame with daily gas-weighted base fees
        """
        if blocks_df.empty:
            logger.error("Empty block data provided!")
            return pd.DataFrame()

        # Ensure we have required columns
        required_cols = ['date', 'base_fee_per_gas', 'gas_used']
        missing_cols = [col for col in required_cols if col not in blocks_df.columns]
        if missing_cols:
            # Try alternative column names
            col_mapping = {
                'base_fee_per_gas': ['baseFeePerGas', 'base_fee', 'basefee'],
                'gas_used': ['gasUsed', 'gas']
            }

            for req_col, alternatives in col_mapping.items():
                if req_col not in blocks_df.columns:
                    for alt in alternatives:
                        if alt in blocks_df.columns:
                            blocks_df[req_col] = blocks_df[alt]
                            break

        # Convert base fee to Gwei if in Wei
        if 'base_fee_per_gas' in blocks_df.columns:
            # Assume it's in Wei if values are very large
            if blocks_df['base_fee_per_gas'].median() > 1000:
                blocks_df['base_fee_gwei'] = self.units.wei_to_gwei(blocks_df['base_fee_per_gas'])
            else:
                blocks_df['base_fee_gwei'] = blocks_df['base_fee_per_gas']
        else:
            logger.error("base_fee_per_gas column not found!")
            return pd.DataFrame()

        # Group by date and compute gas-weighted average
        daily_stats = blocks_df.groupby('date').apply(
            lambda x: pd.Series({
                'bf_obs_gwei': self.units.compute_gas_weighted_fee(
                    x['base_fee_gwei'].values,
                    x['gas_used'].values
                ),
                'total_gas_used': x['gas_used'].sum(),
                'block_count': len(x),
                'bf_median_gwei': x['base_fee_gwei'].median(),
                'bf_mean_gwei': x['base_fee_gwei'].mean(),
                'bf_p90_gwei': x['base_fee_gwei'].quantile(0.9) if len(x) > 1 else x['base_fee_gwei'].iloc[0],
                'bf_min_gwei': x['base_fee_gwei'].min(),
                'bf_max_gwei': x['base_fee_gwei'].max()
            })
        ).reset_index()

        # Add validation metrics
        daily_stats['weight_vs_median_pct'] = (
            (daily_stats['bf_obs_gwei'] - daily_stats['bf_median_gwei']) /
            daily_stats['bf_median_gwei'] * 100
        )

        logger.info(f"Computed gas-weighted base fees for {len(daily_stats)} days")
        logger.info(f"Average difference between weighted and median: "
                   f"{daily_stats['weight_vs_median_pct'].mean():.2f}%")

        return daily_stats

    def load_or_compute_from_panel(self) -> pd.DataFrame:
        """
        Load existing panel data and compute approximation if block data unavailable.

        This uses the daily median base fee as an approximation when
        block-level data is not available.
        """
        # Load converted panel data
        panel_path = self.data_dir / "core_panel_v1" / "core_panel_v1_converted.parquet"

        if not panel_path.exists():
            logger.error(f"Panel data not found at {panel_path}")
            return pd.DataFrame()

        logger.info(f"Loading panel data from {panel_path}")

        # Read with pyarrow to handle special types
        table = pq.read_table(panel_path)

        # Convert to pandas, handling date column specially
        columns_dict = {}
        for i, name in enumerate(table.schema.names):
            column = table.column(i)
            if name == 'date':
                # Convert date column
                columns_dict[name] = pd.to_datetime(column.to_pandas())
            else:
                columns_dict[name] = column.to_pandas()

        panel_df = pd.DataFrame(columns_dict)

        # Create gas-weighted fee approximation
        # Note: This is using median, not truly gas-weighted without block data
        result_df = pd.DataFrame({
            'date': panel_df['date'],
            'bf_obs_gwei': panel_df['base_fee_median_gwei'],
            'total_gas_used': panel_df['gas_used_total'],
            'block_count': panel_df['blocks_count'] if 'blocks_count' in panel_df else np.nan,
            'bf_median_gwei': panel_df['base_fee_median_gwei'],
            'bf_p90_gwei': panel_df['base_fee_p90_gwei'] if 'base_fee_p90_gwei' in panel_df else np.nan,
            'is_approximation': True  # Flag that this is not true gas-weighted
        })

        # Add regime indicators
        LONDON_DATE = pd.to_datetime("2021-08-05")
        MERGE_DATE = pd.to_datetime("2022-09-15")
        DENCUN_DATE = pd.to_datetime("2024-03-13")

        result_df['regime_london'] = (result_df['date'] >= LONDON_DATE).astype(int)
        result_df['regime_merge'] = (result_df['date'] >= MERGE_DATE).astype(int)
        result_df['regime_dencun'] = (result_df['date'] >= DENCUN_DATE).astype(int)

        # Filter to pre-Dencun period for BSTS analysis
        result_df = result_df[result_df['date'] < DENCUN_DATE]

        logger.warning("Using daily median base fee as approximation!")
        logger.warning("For accurate gas-weighted fees, provide block-level data with:")
        logger.warning("  - base_fee_per_gas for each block")
        logger.warning("  - gas_used for each block")

        return result_df

    def validate_against_burn(self, daily_fees: pd.DataFrame, burn_data: Optional[pd.DataFrame] = None) -> dict:
        """
        Validate computed fees against on-chain burn data.

        The base fee is burned, so we can validate:
        Daily_Burn_ETH ≈ sum_blocks(base_fee_wei * gas_used) / 1e18

        Args:
            daily_fees: Daily gas-weighted fees
            burn_data: Optional burn data for validation

        Returns:
            Dictionary with validation metrics
        """
        if burn_data is None:
            logger.warning("No burn data provided for validation")
            return {}

        # Merge fees with burn data
        validation_df = daily_fees.merge(burn_data, on='date', how='inner')

        # Calculate expected burn from our fees
        validation_df['expected_burn_eth'] = (
            validation_df['bf_obs_gwei'] * validation_df['total_gas_used'] / 1e9
        )

        # Compare with actual burn
        validation_df['burn_diff_pct'] = (
            (validation_df['expected_burn_eth'] - validation_df['actual_burn_eth']) /
            validation_df['actual_burn_eth'] * 100
        )

        metrics = {
            'mean_diff_pct': validation_df['burn_diff_pct'].mean(),
            'median_diff_pct': validation_df['burn_diff_pct'].median(),
            'max_diff_pct': validation_df['burn_diff_pct'].abs().max(),
            'within_10pct': (validation_df['burn_diff_pct'].abs() <= 10).mean() * 100,
            'within_20pct': (validation_df['burn_diff_pct'].abs() <= 20).mean() * 100
        }

        logger.info("Burn validation results:")
        logger.info(f"  Mean difference: {metrics['mean_diff_pct']:.2f}%")
        logger.info(f"  Median difference: {metrics['median_diff_pct']:.2f}%")
        logger.info(f"  Max difference: {metrics['max_diff_pct']:.2f}%")
        logger.info(f"  Days within 10%: {metrics['within_10pct']:.1f}%")
        logger.info(f"  Days within 20%: {metrics['within_20pct']:.1f}%")

        return metrics

    def save_results(self, daily_fees: pd.DataFrame, output_dir: Optional[Path] = None):
        """Save computed gas-weighted fees to file."""
        if output_dir is None:
            output_dir = PROJECT_ROOT / "data" / "processed" / "gas_weighted_fees"

        output_dir.mkdir(parents=True, exist_ok=True)

        # Save as Parquet
        output_path = output_dir / "daily_gas_weighted_base_fees.parquet"
        daily_fees.to_parquet(output_path, index=False)
        logger.info(f"Saved gas-weighted fees to {output_path}")

        # Also save as CSV for easy inspection
        csv_path = output_dir / "daily_gas_weighted_base_fees.csv"
        daily_fees.to_csv(csv_path, index=False)
        logger.info(f"Saved CSV to {csv_path}")

        # Save summary statistics
        stats = {
            'date_range': f"{daily_fees['date'].min()} to {daily_fees['date'].max()}",
            'n_days': len(daily_fees),
            'mean_bf_obs_gwei': float(daily_fees['bf_obs_gwei'].mean()),
            'median_bf_obs_gwei': float(daily_fees['bf_obs_gwei'].median()),
            'p10_bf_obs_gwei': float(daily_fees['bf_obs_gwei'].quantile(0.1)),
            'p90_bf_obs_gwei': float(daily_fees['bf_obs_gwei'].quantile(0.9)),
            'total_gas_used': float(daily_fees['total_gas_used'].sum()),
            'has_block_data': 'is_approximation' not in daily_fees.columns
        }

        import json
        stats_path = output_dir / "gas_weighted_stats.json"
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"Saved statistics to {stats_path}")


def main():
    """Main execution function."""
    calculator = GasWeightedBaseFeeCalculator()

    # Try to load block data
    blocks_df = calculator.load_block_data()

    if not blocks_df.empty:
        # Compute from actual block data
        logger.info("Computing gas-weighted fees from block data...")
        daily_fees = calculator.compute_daily_gas_weighted_base_fee(blocks_df)
    else:
        # Fall back to panel data approximation
        logger.info("Using panel data for fee approximation...")
        daily_fees = calculator.load_or_compute_from_panel()

    if not daily_fees.empty:
        # Save results
        calculator.save_results(daily_fees)

        # Print summary
        print("\n" + "="*60)
        print("GAS-WEIGHTED BASE FEE COMPUTATION COMPLETE")
        print("="*60)
        print(f"Date range: {daily_fees['date'].min()} to {daily_fees['date'].max()}")
        print(f"Number of days: {len(daily_fees)}")
        print(f"Mean gas-weighted base fee: {daily_fees['bf_obs_gwei'].mean():.2f} Gwei")
        print(f"Median gas-weighted base fee: {daily_fees['bf_obs_gwei'].median():.2f} Gwei")

        if 'is_approximation' in daily_fees.columns:
            print("\n⚠️  WARNING: Using median as approximation!")
            print("   For accurate gas-weighted fees, provide block-level data")
    else:
        logger.error("Failed to compute gas-weighted fees!")
        sys.exit(1)


if __name__ == "__main__":
    main()
