#!/usr/bin/env python3
"""
Gas-Weighted Priority Fee Computation
======================================

Computes daily gas-weighted priority (tip) fees from transaction data.

Formula:
TIP_obs_t = sum_b(priority_fee_gwei_b × gas_used_b) / sum_b(gas_used_b)

Priority fees represent the tips paid to validators and are important
for complete welfare analysis in the base+tip sensitivity scenario.

Author: BSTS-to-Dollar Pipeline Specialist
Date: 2025-10-18
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pyarrow.parquet as pq
import logging
import sys
from typing import Optional

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


class GasWeightedPriorityFeeCalculator:
    """Calculate gas-weighted priority fees from Ethereum transaction data."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize calculator with data directory."""
        self.data_dir = data_dir or PROJECT_ROOT / "data"
        self.units = EthereumUnits()
        logger.info(f"Initialized Gas-Weighted Priority Fee Calculator")

    def load_transaction_data(self, start_date: str = "2021-08-05", end_date: str = "2024-03-13") -> pd.DataFrame:
        """
        Load transaction-level data with priority fees.

        Post-London (EIP-1559), transactions have:
        - maxPriorityFeePerGas: Maximum tip the user is willing to pay
        - maxFeePerGas: Maximum total fee (base + priority)
        - Actual priority fee = min(maxPriorityFeePerGas, maxFeePerGas - baseFeePerGas)

        Args:
            start_date: Start date (London hard fork)
            end_date: End date (Dencun upgrade)

        Returns:
            DataFrame with transaction-level priority fee data
        """
        # Try to load existing transaction data if available
        tx_data_paths = [
            self.data_dir / "transactions" / "ethereum_transactions.parquet",
            self.data_dir / "raw" / "transactions.parquet",
            self.data_dir / "ethereum" / "transactions.parquet"
        ]

        for path in tx_data_paths:
            if path.exists():
                logger.info(f"Loading transaction data from {path}")
                df = pd.read_parquet(path)

                # Filter date range
                df['date'] = pd.to_datetime(df['block_timestamp']).dt.date
                df = df[(df['date'] >= pd.to_datetime(start_date).date()) &
                       (df['date'] <= pd.to_datetime(end_date).date())]

                return df

        # If no transaction data found, create placeholder
        logger.warning("Transaction-level data not found!")
        logger.warning("To compute gas-weighted priority fees, you need:")
        logger.warning("  - Transaction hash")
        logger.warning("  - Block number/timestamp")
        logger.warning("  - Gas used per transaction")
        logger.warning("  - Priority fee per gas (or maxPriorityFeePerGas)")
        logger.warning("  - Effective gas price (for pre-EIP-1559 estimation)")

        return pd.DataFrame({
            'transaction_hash': pd.Series(dtype='object'),
            'block_number': pd.Series(dtype='int64'),
            'block_timestamp': pd.Series(dtype='datetime64[ns]'),
            'gas_used': pd.Series(dtype='int64'),
            'priority_fee_per_gas': pd.Series(dtype='float64'),  # in Wei
            'date': pd.Series(dtype='object')
        })

    def estimate_priority_fees_from_panel(self) -> pd.DataFrame:
        """
        Estimate priority fees using heuristics when transaction data is unavailable.

        Common approximations:
        - Pre-London: Priority fee ≈ Total gas price - Base fee
        - Post-London: Priority fee typically 1-2 Gwei median
        - During congestion: Priority fees can spike to 10+ Gwei

        Returns:
            DataFrame with estimated daily priority fees
        """
        # Load base fee data we computed earlier
        base_fee_path = self.data_dir / "processed" / "gas_weighted_fees" / "daily_gas_weighted_base_fees.parquet"

        if not base_fee_path.exists():
            logger.error("Base fee data not found! Run 09_gas_weighted_base_fee.py first.")
            return pd.DataFrame()

        base_fees = pd.read_parquet(base_fee_path)

        # Estimate priority fees based on regime and congestion level
        logger.info("Estimating priority fees using heuristics...")

        # Initialize with conservative estimates
        base_fees['tip_obs_gwei'] = 1.0  # Default 1 Gwei tip

        # Pre-London: Higher tips (no base fee mechanism)
        pre_london_mask = base_fees['date'] < pd.to_datetime("2021-08-05")
        base_fees.loc[pre_london_mask, 'tip_obs_gwei'] = 5.0

        # High congestion periods: Higher tips
        # When base fee > 100 Gwei, tips tend to be higher
        high_congestion = base_fees['bf_obs_gwei'] > 100
        base_fees.loc[high_congestion, 'tip_obs_gwei'] = base_fees.loc[high_congestion, 'bf_obs_gwei'] * 0.1

        # Very high congestion: Even higher tips
        very_high_congestion = base_fees['bf_obs_gwei'] > 200
        base_fees.loc[very_high_congestion, 'tip_obs_gwei'] = base_fees.loc[very_high_congestion, 'bf_obs_gwei'] * 0.15

        # Add noise to make it more realistic
        np.random.seed(42)
        noise = np.random.lognormal(0, 0.3, len(base_fees))
        base_fees['tip_obs_gwei'] = base_fees['tip_obs_gwei'] * noise

        # Cap at reasonable maximum
        base_fees['tip_obs_gwei'] = np.minimum(base_fees['tip_obs_gwei'], 50)

        # Add estimation flag
        base_fees['tip_is_estimated'] = True

        logger.warning("Priority fees are ESTIMATED, not computed from actual transaction data!")
        logger.info(f"Estimated priority fee statistics:")
        logger.info(f"  Mean: {base_fees['tip_obs_gwei'].mean():.2f} Gwei")
        logger.info(f"  Median: {base_fees['tip_obs_gwei'].median():.2f} Gwei")
        logger.info(f"  P90: {base_fees['tip_obs_gwei'].quantile(0.9):.2f} Gwei")

        return base_fees[['date', 'tip_obs_gwei', 'tip_is_estimated']]

    def compute_daily_gas_weighted_priority_fee(self, txs_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute daily gas-weighted priority fee from transaction data.

        Formula:
        TIP_obs_t = sum_tx(priority_fee_gwei_tx × gas_used_tx) / sum_tx(gas_used_tx)

        Args:
            txs_df: DataFrame with transaction-level data

        Returns:
            DataFrame with daily gas-weighted priority fees
        """
        if txs_df.empty:
            logger.warning("Empty transaction data, using estimation...")
            return self.estimate_priority_fees_from_panel()

        # Convert priority fee to Gwei if in Wei
        if 'priority_fee_per_gas' in txs_df.columns:
            if txs_df['priority_fee_per_gas'].median() > 1000:
                txs_df['priority_fee_gwei'] = self.units.wei_to_gwei(txs_df['priority_fee_per_gas'])
            else:
                txs_df['priority_fee_gwei'] = txs_df['priority_fee_per_gas']
        else:
            logger.warning("No priority fee data in transactions, using estimation...")
            return self.estimate_priority_fees_from_panel()

        # Group by date and compute gas-weighted average
        daily_tips = txs_df.groupby('date').apply(
            lambda x: pd.Series({
                'tip_obs_gwei': self.units.compute_gas_weighted_fee(
                    x['priority_fee_gwei'].values,
                    x['gas_used'].values
                ),
                'total_gas_used': x['gas_used'].sum(),
                'tx_count': len(x),
                'tip_median_gwei': x['priority_fee_gwei'].median(),
                'tip_mean_gwei': x['priority_fee_gwei'].mean(),
                'tip_p90_gwei': x['priority_fee_gwei'].quantile(0.9),
                'tip_max_gwei': x['priority_fee_gwei'].max(),
                'tip_is_estimated': False
            })
        ).reset_index()

        logger.info(f"Computed gas-weighted priority fees for {len(daily_tips)} days")

        return daily_tips

    def compute_total_fees(self, base_fees_df: pd.DataFrame, priority_fees_df: pd.DataFrame) -> pd.DataFrame:
        """
        Combine base and priority fees to get total fees.

        Total fee = Base fee + Priority fee

        Args:
            base_fees_df: Daily base fees
            priority_fees_df: Daily priority fees

        Returns:
            DataFrame with combined fee metrics
        """
        # Merge base and priority fees
        combined = base_fees_df.merge(priority_fees_df, on='date', how='inner')

        # Calculate total fees
        combined['tf_obs_gwei'] = combined['bf_obs_gwei'] + combined['tip_obs_gwei']

        # Add percentages
        combined['tip_pct_of_total'] = (combined['tip_obs_gwei'] / combined['tf_obs_gwei'] * 100)

        logger.info(f"Combined fees for {len(combined)} days")
        logger.info(f"Average tip percentage of total: {combined['tip_pct_of_total'].mean():.1f}%")

        return combined

    def save_results(self, priority_fees_df: pd.DataFrame, output_dir: Optional[Path] = None):
        """Save computed priority fees to file."""
        if output_dir is None:
            output_dir = PROJECT_ROOT / "data" / "processed" / "gas_weighted_fees"

        output_dir.mkdir(parents=True, exist_ok=True)

        # Save priority fees
        priority_path = output_dir / "daily_gas_weighted_priority_fees.parquet"
        priority_fees_df.to_parquet(priority_path, index=False)
        logger.info(f"Saved priority fees to {priority_path}")

        # Also save as CSV
        csv_path = output_dir / "daily_gas_weighted_priority_fees.csv"
        priority_fees_df.to_csv(csv_path, index=False)

        # If we can, combine with base fees for total fees
        base_fee_path = output_dir / "daily_gas_weighted_base_fees.parquet"
        if base_fee_path.exists():
            base_fees = pd.read_parquet(base_fee_path)

            # Select relevant columns from base fees
            base_cols = ['date', 'bf_obs_gwei', 'total_gas_used', 'bf_median_gwei']
            base_fees_subset = base_fees[base_cols]

            combined = self.compute_total_fees(base_fees_subset, priority_fees_df)

            # Save combined fees
            combined_path = output_dir / "daily_total_fees.parquet"
            combined.to_parquet(combined_path, index=False)
            logger.info(f"Saved combined fees to {combined_path}")

            # Save CSV
            combined_csv = output_dir / "daily_total_fees.csv"
            combined.to_csv(combined_csv, index=False)

        # Save statistics
        import json
        stats = {
            'date_range': f"{priority_fees_df['date'].min()} to {priority_fees_df['date'].max()}",
            'n_days': len(priority_fees_df),
            'mean_tip_obs_gwei': float(priority_fees_df['tip_obs_gwei'].mean()),
            'median_tip_obs_gwei': float(priority_fees_df['tip_obs_gwei'].median()),
            'p90_tip_obs_gwei': float(priority_fees_df['tip_obs_gwei'].quantile(0.9)),
            'is_estimated': bool(priority_fees_df['tip_is_estimated'].iloc[0] if 'tip_is_estimated' in priority_fees_df else True)
        }

        stats_path = output_dir / "priority_fee_stats.json"
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)


def main():
    """Main execution function."""
    calculator = GasWeightedPriorityFeeCalculator()

    # Try to load transaction data
    txs_df = calculator.load_transaction_data()

    # Compute priority fees (will estimate if no tx data)
    priority_fees = calculator.compute_daily_gas_weighted_priority_fee(txs_df)

    if not priority_fees.empty:
        # Save results
        calculator.save_results(priority_fees)

        # Print summary
        print("\n" + "="*60)
        print("GAS-WEIGHTED PRIORITY FEE COMPUTATION COMPLETE")
        print("="*60)
        print(f"Date range: {priority_fees['date'].min()} to {priority_fees['date'].max()}")
        print(f"Number of days: {len(priority_fees)}")
        print(f"Mean priority fee: {priority_fees['tip_obs_gwei'].mean():.2f} Gwei")
        print(f"Median priority fee: {priority_fees['tip_obs_gwei'].median():.2f} Gwei")

        if 'tip_is_estimated' in priority_fees.columns and priority_fees['tip_is_estimated'].iloc[0]:
            print("\n⚠️  WARNING: Priority fees are ESTIMATED!")
            print("   For accurate gas-weighted priority fees, provide transaction-level data")
    else:
        logger.error("Failed to compute priority fees!")
        sys.exit(1)


if __name__ == "__main__":
    main()
