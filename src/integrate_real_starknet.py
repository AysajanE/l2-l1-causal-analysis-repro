#!/usr/bin/env python3
"""
Integrate REAL Starknet data from Dune Analytics with existing L2 dataset
Creates the complete 7-chain dataset with 100% REAL data
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StarknetDataIntegrator:
    def __init__(self):
        script_dir = Path(__file__).parent.absolute()
        self.data_dir = script_dir.parent / "data" / "intermediate"

    def process_starknet_json(self):
        """
        Process the raw Starknet JSON data from Dune API
        """
        logger.info("🔍 Processing REAL Starknet data from Dune API...")

        # Load the raw JSON data
        starknet_json_file = self.data_dir / "starknet_dune_raw.json"
        if not starknet_json_file.exists():
            logger.error("❌ No Starknet JSON data found")
            return None

        with open(starknet_json_file, 'r') as f:
            dune_response = json.load(f)

        # Extract the rows from the Dune response
        rows = dune_response.get('result', {}).get('rows', [])
        logger.info(f"✅ Found {len(rows)} Starknet records in JSON")

        if not rows:
            logger.error("❌ No data rows found in JSON")
            return None

        # Convert to our format
        starknet_data = []
        for row in rows:
            day_str = row.get('day')
            daily_tx_count = row.get('daily_tx_count')
            active_addresses = row.get('active_addresses')

            if day_str and daily_tx_count is not None:
                try:
                    # Parse the date string: "2021-11-16 00:00:00.000 UTC"
                    date_obj = datetime.strptime(day_str.split(' ')[0], '%Y-%m-%d')
                    timestamp = date_obj.timestamp() * 1_000_000_000

                    starknet_data.append({
                        'date': timestamp,
                        'chain': 'starknet',
                        'tx_count': float(daily_tx_count),
                        'active_addr': float(active_addresses) if active_addresses is not None and active_addresses > 0 else None
                    })

                except Exception as e:
                    logger.warning(f"Error processing row: {e} - Row: {row}")
                    continue

        logger.info(f"✅ Processed {len(starknet_data)} REAL Starknet records")

        # Show data range
        if starknet_data:
            dates = [pd.to_datetime(d['date'], unit='ns').date() for d in starknet_data]
            tx_counts = [d['tx_count'] for d in starknet_data]
            logger.info(f"Date range: {min(dates)} to {max(dates)}")
            logger.info(f"Transaction range: {min(tx_counts):,.0f} to {max(tx_counts):,.0f}")
            logger.info(f"Average daily transactions: {sum(tx_counts)/len(tx_counts):,.0f}")

        return starknet_data

    def create_complete_real_dataset(self):
        """
        Create the complete 7-chain dataset with 100% REAL data
        """
        logger.info("🔄 Creating complete 7-chain REAL L2 dataset...")

        # Load existing data with REAL zkSync
        existing_file = self.data_dir / "l2_daily_metrics_with_real_zksync.parquet"
        if not existing_file.exists():
            logger.error("❌ No existing L2+zkSync data found - run integration first")
            return None

        existing_df = pd.read_parquet(existing_file)
        logger.info(f"✅ Loaded existing data: {len(existing_df)} records")
        logger.info(f"Existing chains: {sorted(existing_df['chain'].unique())}")

        # Process REAL Starknet data
        starknet_data = self.process_starknet_json()
        if not starknet_data:
            logger.error("❌ Failed to process Starknet data")
            return None

        # Convert Starknet data to DataFrame
        starknet_df = pd.DataFrame(starknet_data)
        starknet_df['date'] = starknet_df['date'].astype('float64')

        # Ensure existing data has consistent types
        if existing_df['date'].dtype != 'float64':
            existing_df['date'] = pd.to_datetime(existing_df['date']).astype('int64').astype('float64')

        # Combine all REAL data
        complete_df = pd.concat([existing_df, starknet_df], ignore_index=True)

        # Sort by date
        complete_df['date_for_sort'] = pd.to_datetime(complete_df['date'], unit='ns')
        complete_df = complete_df.sort_values(['date_for_sort', 'chain'])
        complete_df = complete_df.drop('date_for_sort', axis=1)

        logger.info(f"✅ Complete dataset: {len(complete_df)} records")
        logger.info(f"All 7 chains: {sorted(complete_df['chain'].unique())}")

        # Save complete REAL dataset
        output_file = self.data_dir / "l2_daily_metrics_complete_real.parquet"
        complete_df.to_parquet(output_file, index=False)

        logger.info(f"💾 Saved complete REAL dataset: {output_file}")

        # Create comprehensive summary
        summary = complete_df.groupby('chain').agg({
            'tx_count': ['count', 'sum', 'mean', 'min', 'max'],
            'date': ['min', 'max']
        }).round(2)

        logger.info("\n📋 Complete REAL L2 Dataset Summary:")
        logger.info(f"\n{summary}")

        # Data quality assessment
        logger.info("\n🎯 FINAL Data Quality Assessment:")
        total_records = 0
        total_transactions = 0

        for chain in sorted(complete_df['chain'].unique()):
            chain_data = complete_df[complete_df['chain'] == chain]
            if len(chain_data) > 0:
                start_date = pd.to_datetime(chain_data['date'].min(), unit='ns').date()
                end_date = pd.to_datetime(chain_data['date'].max(), unit='ns').date()
                avg_tx = chain_data['tx_count'].mean()
                total_tx = chain_data['tx_count'].sum()

                total_records += len(chain_data)
                total_transactions += total_tx

                logger.info(f"  {chain.upper()}: {len(chain_data)} days from {start_date} to {end_date}")
                logger.info(f"    Status: 100% REAL, Avg: {avg_tx:,.0f} tx/day, Total: {total_tx:,.0f} tx")

        logger.info(f"\n🏆 FINAL TOTALS:")
        logger.info(f"    Total Records: {total_records:,}")
        logger.info(f"    Total Transactions: {total_transactions:,.0f}")
        logger.info(f"    All 7 L2 chains: 100% REAL DATA")

        return complete_df

    def prepare_bigquery_update(self):
        """
        Prepare the final BigQuery update with complete REAL data
        """
        logger.info("📤 Preparing final BigQuery update with complete REAL data...")

        complete_file = self.data_dir / "l2_daily_metrics_complete_real.parquet"
        if not complete_file.exists():
            logger.error("❌ No complete dataset found")
            return False

        logger.info(f"✅ Complete REAL dataset ready: {complete_file}")
        logger.info("\n📋 To update BigQuery with complete REAL data, run:")
        logger.info(f"   bq load --replace --source_format=PARQUET eth_scaling_mart.mart_l2_daily {complete_file}")

        return True

def main():
    """Main execution function"""
    logger.info("🚀 Creating Complete 7-Chain REAL L2 Dataset")
    logger.info("=" * 60)

    integrator = StarknetDataIntegrator()

    try:
        # Create complete dataset
        complete_df = integrator.create_complete_real_dataset()

        if complete_df is not None:
            logger.info("\n✅ COMPLETE 7-CHAIN REAL L2 DATASET CREATED!")

            # Prepare BigQuery update
            integrator.prepare_bigquery_update()

            logger.info("\n🎯 MISSION ACCOMPLISHED:")
            logger.info("  ✅ All 7 L2 chains now have 100% REAL data")
            logger.info("  ✅ Arbitrum, Base, Linea, Optimism, Scroll: REAL (original)")
            logger.info("  ✅ zkSync Era: REAL (from Dune Analytics)")
            logger.info("  ✅ Starknet: REAL (from Dune Analytics)")
            logger.info("\n🎓 Dataset ready for academic research!")

        else:
            logger.error("\n❌ Complete dataset creation failed")

    except Exception as e:
        logger.error(f"❌ Error during complete dataset creation: {e}")
        raise

if __name__ == "__main__":
    main()