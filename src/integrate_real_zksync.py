#!/usr/bin/env python3
"""
Integrate REAL zkSync Era data with existing L2 dataset
Replaces any synthetic zkSync data with the real data we extracted from Dune
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class L2DataIntegrator:
    def __init__(self):
        script_dir = Path(__file__).parent.absolute()
        self.data_dir = script_dir.parent / "data" / "intermediate"

    def integrate_real_zksync_data(self):
        """
        Integrate REAL zkSync data with existing L2 dataset
        """
        logger.info("🔄 Integrating REAL zkSync Era data with existing L2 dataset...")

        # Load existing L2 data (5 real chains)
        existing_file = self.data_dir / "l2_daily_metrics.parquet"
        if not existing_file.exists():
            logger.error("❌ No existing L2 data found")
            return None

        existing_df = pd.read_parquet(existing_file)
        logger.info(f"✅ Loaded existing data: {len(existing_df)} records")
        logger.info(f"Existing chains: {sorted(existing_df['chain'].unique())}")

        # Load REAL zkSync data
        zksync_file = self.data_dir / "zksync_real_data.parquet"
        if not zksync_file.exists():
            logger.error("❌ No REAL zkSync data found - run extract_zksync_only.py first")
            return None

        zksync_df = pd.read_parquet(zksync_file)
        logger.info(f"✅ Loaded REAL zkSync data: {len(zksync_df)} records")

        # Validate zkSync data
        dates = pd.to_datetime(zksync_df['date'], unit='ns')
        logger.info(f"zkSync date range: {dates.min().date()} to {dates.max().date()}")
        logger.info(f"zkSync transaction range: {zksync_df['tx_count'].min():,.0f} to {zksync_df['tx_count'].max():,.0f}")

        # Filter zkSync data to only include Era period (from March 24, 2023)
        era_start = datetime(2023, 3, 24).timestamp() * 1_000_000_000
        zksync_era_df = zksync_df[zksync_df['date'] >= era_start].copy()
        logger.info(f"Filtered to zkSync Era period: {len(zksync_era_df)} records")

        # Remove any existing zkSync data from existing dataset (in case there was synthetic data)
        existing_real_chains = existing_df[existing_df['chain'] != 'zksync'].copy()
        logger.info(f"Existing data without zkSync: {len(existing_real_chains)} records")

        # Ensure consistent data types
        if not existing_real_chains.empty:
            if existing_real_chains['date'].dtype != 'float64':
                existing_real_chains['date'] = pd.to_datetime(existing_real_chains['date']).astype('int64').astype('float64')

        zksync_era_df['date'] = zksync_era_df['date'].astype('float64')

        # Combine all REAL data
        combined_df = pd.concat([existing_real_chains, zksync_era_df], ignore_index=True)

        # Sort by date
        combined_df['date_for_sort'] = pd.to_datetime(combined_df['date'], unit='ns')
        combined_df = combined_df.sort_values(['date_for_sort', 'chain'])
        combined_df = combined_df.drop('date_for_sort', axis=1)

        logger.info(f"✅ Combined dataset: {len(combined_df)} records")
        logger.info(f"All chains: {sorted(combined_df['chain'].unique())}")

        # Save integrated REAL data
        output_file = self.data_dir / "l2_daily_metrics_with_real_zksync.parquet"
        combined_df.to_parquet(output_file, index=False)

        logger.info(f"💾 Saved integrated REAL data: {output_file}")

        # Create summary
        summary = combined_df.groupby('chain').agg({
            'tx_count': ['count', 'sum', 'mean', 'min', 'max'],
            'date': ['min', 'max']
        }).round(2)

        logger.info("\n📋 Integrated Dataset Summary:")
        logger.info(f"\n{summary}")

        # Show data quality assessment
        logger.info("\n🔍 Data Quality Assessment:")
        for chain in sorted(combined_df['chain'].unique()):
            chain_data = combined_df[combined_df['chain'] == chain]
            if len(chain_data) > 0:
                start_date = pd.to_datetime(chain_data['date'].min(), unit='ns').date()
                end_date = pd.to_datetime(chain_data['date'].max(), unit='ns').date()
                avg_tx = chain_data['tx_count'].mean()
                total_tx = chain_data['tx_count'].sum()
                data_type = "REAL" if chain in ['arbitrum', 'base', 'linea', 'optimism', 'scroll', 'zksync'] else "SYNTHETIC"
                logger.info(f"  {chain.upper()}: {len(chain_data)} days from {start_date} to {end_date}")
                logger.info(f"    Status: {data_type}, Avg: {avg_tx:,.0f} tx/day, Total: {total_tx:,.0f} tx")

        return combined_df

    def update_bigquery_with_real_zksync(self):
        """
        Update BigQuery with the integrated dataset including REAL zkSync data
        """
        logger.info("📤 Preparing to update BigQuery with REAL zkSync data...")

        integrated_file = self.data_dir / "l2_daily_metrics_with_real_zksync.parquet"
        if not integrated_file.exists():
            logger.error("❌ No integrated dataset found - run integration first")
            return False

        logger.info(f"✅ Integrated dataset ready: {integrated_file}")
        logger.info("📋 To update BigQuery, run:")
        logger.info(f"   bq load --replace --source_format=PARQUET eth_scaling_mart.mart_l2_daily {integrated_file}")

        return True

def main():
    """Main execution function"""
    logger.info("🚀 Integrating REAL zkSync Era Data with L2 Dataset")
    logger.info("=" * 60)

    integrator = L2DataIntegrator()

    try:
        # Integrate the data
        combined_df = integrator.integrate_real_zksync_data()

        if combined_df is not None:
            logger.info("\n✅ REAL zkSync integration completed successfully!")

            # Prepare BigQuery update
            integrator.update_bigquery_with_real_zksync()

            logger.info("\n🎯 Summary:")
            logger.info("  - 5 chains with REAL data: arbitrum, base, linea, optimism, scroll")
            logger.info("  - 1 chain with REAL data: zksync (from Dune Analytics)")
            logger.info("  - Still needed: Starknet REAL data (use corrected query)")

        else:
            logger.error("\n❌ Integration failed")

    except Exception as e:
        logger.error(f"❌ Error during integration: {e}")
        raise

if __name__ == "__main__":
    main()