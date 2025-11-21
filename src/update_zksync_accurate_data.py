#!/usr/bin/env python3
"""
Update zkSync data with accurate query results from Dune Analytics
Fetch data from query 5809095 and update all data sources including BigQuery
"""

import pandas as pd
import requests
import json
from datetime import datetime
from pathlib import Path
import logging
import subprocess
import sys
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AccurateZkSyncUpdater:
    def __init__(self, dune_api_key: str):
        self.dune_api_key = dune_api_key
        self.dune_api = "https://api.dune.com/api/v1"

        # Use absolute path based on script location
        script_dir = Path(__file__).parent.absolute()
        self.data_dir = script_dir.parent / "data" / "intermediate"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Query ID for accurate zkSync data
        self.accurate_query_id = 5809095

    def fetch_accurate_zksync_data(self) -> List[Dict]:
        """Fetch accurate zkSync data from Dune query 5809095"""
        logger.info(f"🔍 Fetching accurate zkSync data from query {self.accurate_query_id}")

        try:
            # Fetch results directly using the results endpoint with limit
            results_url = f"{self.dune_api}/query/{self.accurate_query_id}/results"
            headers = {'X-Dune-API-Key': self.dune_api_key}
            params = {'limit': 1000}

            logger.info("Fetching query results...")
            response = requests.get(results_url, headers=headers, params=params)

            if response.status_code != 200:
                logger.error(f"Failed to fetch results: {response.status_code} - {response.text}")
                return []

            result_data = response.json()
            rows = result_data.get('result', {}).get('rows', [])

            if not rows:
                logger.error("No data returned from query")
                return []

            logger.info(f"✅ Successfully fetched {len(rows)} rows")
            logger.info(f"Column names: {list(rows[0].keys())}")
            logger.info(f"Sample rows (first 3): {rows[:3]}")

            return rows

        except Exception as e:
            logger.error(f"Error fetching accurate zkSync data: {e}")
            return []

    def process_accurate_data(self, rows: List[Dict]) -> List[Dict]:
        """Process the accurate zkSync data into standard format"""
        logger.info("📊 Processing accurate zkSync data...")

        processed_data = []

        for row in rows:
            try:
                # Expected columns from the accurate query: day, daily_tx_count, active_addresses
                date_str = row.get('day')
                tx_count = row.get('daily_tx_count')
                active_addresses = row.get('active_addresses')

                if not date_str or tx_count is None:
                    logger.warning(f"Missing required data in row: {row}")
                    continue

                # Handle date format - convert to timestamp
                if isinstance(date_str, str):
                    date_clean = date_str.split('T')[0].split(' ')[0]
                    date_obj = datetime.strptime(date_clean, '%Y-%m-%d')
                else:
                    date_obj = date_str if hasattr(date_str, 'strftime') else datetime.strptime(str(date_str).split('T')[0], '%Y-%m-%d')

                timestamp = date_obj.timestamp() * 1_000_000_000

                processed_data.append({
                    'date': timestamp,
                    'chain': 'zksync',
                    'tx_count': float(tx_count),
                    'active_addr': float(active_addresses) if active_addresses is not None else None
                })

            except Exception as e:
                logger.warning(f"Error processing row: {e} - Row: {row}")
                continue

        logger.info(f"✅ Processed {len(processed_data)} accurate zkSync records")

        # Show data range and statistics
        if processed_data:
            dates = [pd.to_datetime(d['date'], unit='ns').date() for d in processed_data]
            tx_counts = [d['tx_count'] for d in processed_data]
            active_addrs = [d['active_addr'] for d in processed_data if d['active_addr'] is not None]

            logger.info(f"Date range: {min(dates)} to {max(dates)}")
            logger.info(f"Transaction range: {min(tx_counts):,.0f} to {max(tx_counts):,.0f}")
            logger.info(f"Average daily transactions: {sum(tx_counts)/len(tx_counts):,.0f}")
            if active_addrs:
                logger.info(f"Active addresses range: {min(active_addrs):,.0f} to {max(active_addrs):,.0f}")
                logger.info(f"Average daily active addresses: {sum(active_addrs)/len(active_addrs):,.0f}")

        return processed_data

    def update_zksync_real_data(self, zksync_data: List[Dict]):
        """Update the zksync_real_data.parquet file"""
        logger.info("💾 Updating zksync_real_data.parquet...")

        if not zksync_data:
            logger.error("❌ No zkSync data to save")
            return

        # Create DataFrame and save
        zksync_df = pd.DataFrame(zksync_data)
        zksync_df['date'] = zksync_df['date'].astype('float64')

        output_file = self.data_dir / "zksync_real_data.parquet"
        zksync_df.to_parquet(output_file, index=False)

        logger.info(f"💾 Updated zksync_real_data.parquet: {len(zksync_df)} records")
        logger.info(f"📂 File: {output_file}")

        # Show summary statistics
        summary = zksync_df.agg({
            'tx_count': ['count', 'sum', 'mean', 'min', 'max'],
            'active_addr': ['count', 'sum', 'mean', 'min', 'max']
        }).round(2)

        logger.info("📋 Updated zkSync Data Summary:")
        logger.info(f"\n{summary}")

    def update_l2_daily_metrics(self, new_zksync_data: List[Dict]):
        """Update the l2_daily_metrics.parquet file with accurate zkSync data"""
        logger.info("🔄 Updating l2_daily_metrics.parquet with accurate zkSync data...")

        l2_metrics_file = self.data_dir / "l2_daily_metrics.parquet"

        if not l2_metrics_file.exists():
            logger.error(f"❌ {l2_metrics_file} not found")
            return

        # Load existing data
        df = pd.read_parquet(l2_metrics_file)
        logger.info(f"Loaded existing L2 metrics: {len(df)} total records")

        # Remove old zkSync data
        non_zksync_df = df[df['chain'] != 'zksync'].copy()
        logger.info(f"Removed old zkSync data, remaining: {len(non_zksync_df)} records")

        # Add new accurate zkSync data
        new_zksync_df = pd.DataFrame(new_zksync_data)
        new_zksync_df['date'] = new_zksync_df['date'].astype('float64')

        # Combine data
        updated_df = pd.concat([non_zksync_df, new_zksync_df], ignore_index=True)

        # Sort by date for consistency
        updated_df = updated_df.sort_values('date').reset_index(drop=True)

        # Save updated file
        updated_df.to_parquet(l2_metrics_file, index=False)

        logger.info(f"✅ Updated l2_daily_metrics.parquet: {len(updated_df)} total records")
        logger.info(f"📈 New zkSync records: {len(new_zksync_df)}")

        # Show chain distribution
        chain_counts = updated_df['chain'].value_counts()
        logger.info("Chain distribution:")
        for chain, count in chain_counts.items():
            logger.info(f"  {chain}: {count} records")

    def sync_to_bigquery(self):
        """Sync updated data to BigQuery mart_l2_daily table"""
        logger.info("☁️ Syncing updated data to BigQuery...")

        try:
            l2_metrics_file = self.data_dir / "l2_daily_metrics.parquet"

            if not l2_metrics_file.exists():
                logger.error(f"❌ {l2_metrics_file} not found")
                return

            # Load environment variables for BigQuery
            from dotenv import load_dotenv
            import os

            env_file = Path(__file__).parent.parent / ".env"
            load_dotenv(env_file)

            project_id = os.getenv('PROJECT_ID', 'l2-l1-causal-analysis')
            mart_dataset = os.getenv('MART_DATASET', 'eth_scaling_mart')

            # Convert timestamps to proper format for BigQuery
            df = pd.read_parquet(l2_metrics_file)
            df['date'] = pd.to_datetime(df['date'], unit='ns').dt.date

            # Save as temporary CSV for BigQuery load
            temp_csv = self.data_dir / "temp_l2_daily_metrics.csv"
            df.to_csv(temp_csv, index=False)

            # Use gcloud CLI to load data to BigQuery
            table_id = f"{project_id}.{mart_dataset}.mart_l2_daily"

            cmd = [
                "bq", "load",
                "--replace=true",
                "--source_format=CSV",
                "--skip_leading_rows=1",
                "--autodetect",
                table_id,
                str(temp_csv)
            ]

            logger.info(f"Loading data to BigQuery table: {table_id}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("✅ Successfully synced data to BigQuery")
                logger.info(f"📊 Loaded {len(df)} records to {table_id}")
            else:
                logger.error(f"❌ BigQuery load failed: {result.stderr}")

            # Clean up temporary file
            if temp_csv.exists():
                temp_csv.unlink()

        except Exception as e:
            logger.error(f"Error syncing to BigQuery: {e}")

    def run_complete_update(self):
        """Run the complete update process"""
        logger.info("🚀 Starting complete zkSync data update process")
        logger.info("=" * 60)

        # Step 1: Fetch accurate data
        accurate_data = self.fetch_accurate_zksync_data()
        if not accurate_data:
            logger.error("❌ Failed to fetch accurate zkSync data")
            return

        # Step 2: Process the data
        processed_data = self.process_accurate_data(accurate_data)
        if not processed_data:
            logger.error("❌ Failed to process zkSync data")
            return

        # Step 3: Update zksync_real_data.parquet
        self.update_zksync_real_data(processed_data)

        # Step 4: Update l2_daily_metrics.parquet
        self.update_l2_daily_metrics(processed_data)

        # Step 5: Sync to BigQuery
        self.sync_to_bigquery()

        logger.info("\n✅ Complete zkSync data update process finished!")
        logger.info("🎯 All data sources now contain accurate zkSync Era metrics")

def main():
    """Main execution function"""
    logger.info("🚀 Updating zkSync data with accurate Dune Analytics results")
    logger.info("=" * 60)

    # Load API key
    script_dir = Path(__file__).parent.absolute()
    env_file = script_dir.parent / ".env"

    dune_api_key = None
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip().startswith('DUNE_API_KEY='):
                    dune_api_key = line.strip().split('=', 1)[1]
                    break

    if not dune_api_key:
        logger.error("❌ DUNE_API_KEY not found in .env file")
        return

    logger.info("✅ Found Dune API key")

    # Create updater and run complete process
    updater = AccurateZkSyncUpdater(dune_api_key=dune_api_key)

    try:
        updater.run_complete_update()

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    main()