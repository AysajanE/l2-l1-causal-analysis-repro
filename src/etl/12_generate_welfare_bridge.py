#!/usr/bin/env python3
"""
Daily Welfare Bridge Generator
===============================

Combines all components to generate the comprehensive welfare bridge CSV
with full schema for BSTS-to-dollar mapping.

Critical Output Schema:
- date, BF_obs_gwei, BF_cf_gwei, BF_cf_p05_gwei, BF_cf_p95_gwei
- TIP_obs_gwei, TF_obs_gwei, GAS
- ETHUSD_gwt, ETHUSD_close, ETHUSD_mean
- Delta_usd_base_only, Delta_usd_base_only_p05, Delta_usd_base_only_p95
- Delta_usd_base_plus_tip, Delta_usd_base_plus_tip_p05, Delta_usd_base_plus_tip_p95
- is_capped, is_extrapolation_day

Author: BSTS-to-Dollar Pipeline Specialist
Date: 2025-10-18
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pyarrow.parquet as pq
import logging
import sys
import json
from typing import Dict, Optional
from datetime import datetime

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
PROJECT_ROOT = Path("/Users/aeziz-local/Research/Projects-05-Ethereum Blockchain Economic Analysis/"
                   "Causal Influence of L2 Scaling Solutions on Ethereum L1 Mainnet Congestion/"
                   "L1-L2-causal-influence-analysis/l2-l1-causal-impact")

# Key dates
LONDON_DATE = pd.to_datetime("2021-08-05")
MERGE_DATE = pd.to_datetime("2022-09-15")
DENCUN_DATE = pd.to_datetime("2024-03-13")
WINDOW_START = pd.to_datetime("2023-10-28")  # 137 days before Dencun


class WelfareBridgeGenerator:
    """Generate comprehensive welfare bridge CSV for BSTS-to-dollar mapping."""

    def __init__(self, data_dir: Optional[Path] = None, results_dir: Optional[Path] = None):
        """Initialize generator."""
        self.data_dir = data_dir or PROJECT_ROOT / "data"
        self.results_dir = results_dir or PROJECT_ROOT / "results" / "bsts"
        self.units = EthereumUnits()

        self.results_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Initialized Welfare Bridge Generator")

    def load_all_components(self) -> Dict[str, pd.DataFrame]:
        """Load all required data components."""
        components = {}

        # 1. Load gas-weighted base fees
        base_fee_path = self.data_dir / "processed" / "gas_weighted_fees" / "daily_gas_weighted_base_fees.parquet"
        if base_fee_path.exists():
            components['base_fees'] = pd.read_parquet(base_fee_path)
            logger.info(f"Loaded base fees: {len(components['base_fees'])} days")
        else:
            logger.error("Base fee data not found!")
            raise FileNotFoundError(f"Missing: {base_fee_path}")

        # 2. Load priority fees
        priority_path = self.data_dir / "processed" / "gas_weighted_fees" / "daily_gas_weighted_priority_fees.parquet"
        if priority_path.exists():
            components['priority_fees'] = pd.read_parquet(priority_path)
            logger.info(f"Loaded priority fees: {len(components['priority_fees'])} days")
        else:
            logger.warning("Priority fees not found, will use zeros")
            components['priority_fees'] = None

        # 3. Load ETH prices
        price_path = self.data_dir / "processed" / "eth_prices" / "eth_price_series.parquet"
        if price_path.exists():
            components['eth_prices'] = pd.read_parquet(price_path)
            logger.info(f"Loaded ETH prices: {len(components['eth_prices'])} days")
        else:
            logger.error("ETH price data not found!")
            raise FileNotFoundError(f"Missing: {price_path}")

        # 4. Load BSTS counterfactual results (if available)
        bsts_results_paths = [
            self.results_dir / "bsts_natural_scale_results.parquet",
            self.results_dir / "bsts_results.parquet",
            self.results_dir / "counterfactual_base_fees.csv"
        ]

        for path in bsts_results_paths:
            if path.exists():
                if path.suffix == '.parquet':
                    components['bsts_results'] = pd.read_parquet(path)
                else:
                    components['bsts_results'] = pd.read_csv(path)
                if 'date' in components['bsts_results'].columns:
                    components['bsts_results']['date'] = pd.to_datetime(
                        components['bsts_results']['date']
                    )
                logger.info(f"Loaded BSTS results from: {path}")
                break
        else:
            logger.warning("No BSTS results found, will generate synthetic counterfactuals")
            components['bsts_results'] = None

        return components

    def generate_synthetic_counterfactuals(self, base_fees: pd.DataFrame) -> pd.DataFrame:
        """
        Generate synthetic counterfactuals for testing when BSTS results unavailable.

        The counterfactual assumes low L2 adoption would have led to higher fees.
        """
        logger.warning("Generating SYNTHETIC counterfactuals for testing!")

        # Simple model: counterfactual = observed * (1 + impact_factor)
        # Impact increases over time as L2s grow
        days_since_london = (base_fees['date'] - LONDON_DATE).dt.days
        max_days = days_since_london.max()

        # Impact factor grows from 0% to 30% over the period
        impact_factor = 0.3 * (days_since_london / max_days)

        # Add noise for realism
        np.random.seed(42)
        noise = np.random.normal(1.0, 0.1, len(base_fees))

        cf_multiplier = (1 + impact_factor) * noise

        synthetic_cf = pd.DataFrame({
            'date': base_fees['date'],
            'bf_cf_gwei': base_fees['bf_obs_gwei'] * cf_multiplier,
            'bf_cf_p05_gwei': base_fees['bf_obs_gwei'] * cf_multiplier * 0.8,
            'bf_cf_p95_gwei': base_fees['bf_obs_gwei'] * cf_multiplier * 1.2,
            'is_synthetic': True
        })

        return synthetic_cf

    def compute_welfare_deltas(self, row: pd.Series) -> Dict[str, float]:
        """
        Compute welfare deltas for a single day across price and tip scenarios.
        """
        deltas: Dict[str, float] = {}

        prices = {
            "gwt": row.get("ETHUSD_gwt"),
            "close": row.get("ETHUSD_close"),
            "mean": row.get("ETHUSD_mean"),
            "high": row.get("ETHUSD_high"),
            "low": row.get("ETHUSD_low")
        }

        def base_delta(counterfactual_fee: float, price: float) -> float:
            return self.units.calculate_welfare_delta_usd(
                base_fee_counterfactual_gwei=counterfactual_fee,
                base_fee_observed_gwei=row['BF_obs_gwei'],
                total_gas_used=row['GAS'],
                eth_price_usd=price
            )

        primary_price = prices["gwt"]
        deltas['delta_usd_base_only'] = base_delta(row['BF_cf_gwei'], primary_price)
        deltas['delta_usd_base_only_p05'] = base_delta(row['BF_cf_p05_gwei'], primary_price)
        deltas['delta_usd_base_only_p95'] = base_delta(row['BF_cf_p95_gwei'], primary_price)

        for label in ['close', 'mean', 'high', 'low']:
            price = prices.get(label)
            if price is None or pd.isna(price):
                continue
            deltas[f'delta_usd_base_only_{label}'] = base_delta(row['BF_cf_gwei'], price)

        tip_obs = row.get('TIP_obs_gwei', 0.0) or 0.0
        tip_cf = row.get('TIP_cf_gwei', tip_obs)
        tip_cf_p05 = row.get('TIP_cf_p05_gwei', tip_cf)
        tip_cf_p95 = row.get('TIP_cf_p95_gwei', tip_cf)

        deltas['delta_usd_base_plus_tip'] = self.units.calculate_welfare_delta_usd(
            base_fee_counterfactual_gwei=row['BF_cf_gwei'],
            base_fee_observed_gwei=row['BF_obs_gwei'],
            total_gas_used=row['GAS'],
            eth_price_usd=primary_price,
            include_tip=True,
            tip_counterfactual_gwei=tip_cf,
            tip_observed_gwei=tip_obs
        )
        deltas['delta_usd_base_plus_tip_p05'] = self.units.calculate_welfare_delta_usd(
            base_fee_counterfactual_gwei=row['BF_cf_p05_gwei'],
            base_fee_observed_gwei=row['BF_obs_gwei'],
            total_gas_used=row['GAS'],
            eth_price_usd=primary_price,
            include_tip=True,
            tip_counterfactual_gwei=tip_cf_p05,
            tip_observed_gwei=tip_obs
        )
        deltas['delta_usd_base_plus_tip_p95'] = self.units.calculate_welfare_delta_usd(
            base_fee_counterfactual_gwei=row['BF_cf_p95_gwei'],
            base_fee_observed_gwei=row['BF_obs_gwei'],
            total_gas_used=row['GAS'],
            eth_price_usd=primary_price,
            include_tip=True,
            tip_counterfactual_gwei=tip_cf_p95,
            tip_observed_gwei=tip_obs
        )

        for label in ['close', 'mean', 'high', 'low']:
            price = prices.get(label)
            if price is None or pd.isna(price):
                continue
            deltas[f'delta_usd_base_plus_tip_{label}'] = self.units.calculate_welfare_delta_usd(
                base_fee_counterfactual_gwei=row['BF_cf_gwei'],
                base_fee_observed_gwei=row['BF_obs_gwei'],
                total_gas_used=row['GAS'],
                eth_price_usd=price,
                include_tip=True,
                tip_counterfactual_gwei=tip_cf,
                tip_observed_gwei=tip_obs
            )

        return deltas

    def create_welfare_bridge(self, components: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Create the comprehensive welfare bridge DataFrame.

        Combines all components according to the required schema.
        """
        logger.info("Creating welfare bridge...")

        # Start with base fees
        bridge = components['base_fees'][['date', 'bf_obs_gwei', 'total_gas_used']].copy()

        # Rename columns to match schema
        bridge.rename(columns={
            'bf_obs_gwei': 'BF_obs_gwei',
            'total_gas_used': 'GAS'
        }, inplace=True)

        # Add priority fees
        if components['priority_fees'] is not None:
            bridge = bridge.merge(
                components['priority_fees'][['date', 'tip_obs_gwei']],
                on='date',
                how='left'
            )
            bridge.rename(columns={'tip_obs_gwei': 'TIP_obs_gwei'}, inplace=True)
        else:
            bridge['TIP_obs_gwei'] = 0.0  # Default to zero when tips unavailable

        # Add ETH prices
        price_cols = ['ethusd_gwt', 'ethusd_close', 'ethusd_mean',
                      'ethusd_high', 'ethusd_low', 'price_volatility']
        available_price_cols = [c for c in price_cols if c in components['eth_prices'].columns]
        bridge = bridge.merge(
            components['eth_prices'][['date'] + available_price_cols],
            on='date',
            how='left'
        )
        rename_map = {
            'ethusd_gwt': 'ETHUSD_gwt',
            'ethusd_close': 'ETHUSD_close',
            'ethusd_mean': 'ETHUSD_mean',
            'ethusd_high': 'ETHUSD_high',
            'ethusd_low': 'ETHUSD_low',
            'price_volatility': 'ETHUSD_volatility'
        }
        bridge.rename(columns={k: v for k, v in rename_map.items() if k in bridge.columns}, inplace=True)

        # Add counterfactuals
        if components['bsts_results'] is not None:
            # Map column names from BSTS results
            cf_mapping = {
                'bf_cf_gwei': 'BF_cf_gwei',
                'bf_cf_p05_gwei': 'BF_cf_p05_gwei',
                'bf_cf_p95_gwei': 'BF_cf_p95_gwei',
                'is_capped': 'is_capped'
            }

            bsts_cols = ['date'] + list(cf_mapping.keys())
            available_cols = [c for c in bsts_cols if c in components['bsts_results'].columns]

            bridge['date'] = pd.to_datetime(bridge['date'])
            cf_df = components['bsts_results'][available_cols].copy()
            cf_df['date'] = pd.to_datetime(cf_df['date'])

            bridge = bridge.merge(
                cf_df,
                on='date',
                how='left'
            )

            # Rename if needed
            for old, new in cf_mapping.items():
                if old in bridge.columns and old != new:
                    bridge.rename(columns={old: new}, inplace=True)
        else:
            # Use synthetic counterfactuals
            synthetic_cf = self.generate_synthetic_counterfactuals(
                components['base_fees']
            )
            bridge = bridge.merge(synthetic_cf, on='date', how='left')
            bridge.rename(columns={
                'bf_cf_gwei': 'BF_cf_gwei',
                'bf_cf_p05_gwei': 'BF_cf_p05_gwei',
                'bf_cf_p95_gwei': 'BF_cf_p95_gwei'
            }, inplace=True)
            bridge['is_capped'] = False

        # Fill missing counterfactuals (pre-model period) with observed
        bridge['BF_cf_gwei'] = bridge['BF_cf_gwei'].fillna(bridge['BF_obs_gwei'])
        bridge['BF_cf_p05_gwei'] = bridge['BF_cf_p05_gwei'].fillna(bridge['BF_obs_gwei'] * 0.9)
        bridge['BF_cf_p95_gwei'] = bridge['BF_cf_p95_gwei'].fillna(bridge['BF_obs_gwei'] * 1.1)

        # Compute counterfactual priority fees via proportional scaling
        bf_obs = bridge['BF_obs_gwei'].replace(0, np.nan)
        with np.errstate(divide='ignore', invalid='ignore'):
            tip_scale = bridge['BF_cf_gwei'] / bf_obs
            tip_scale_p05 = bridge['BF_cf_p05_gwei'] / bf_obs
            tip_scale_p95 = bridge['BF_cf_p95_gwei'] / bf_obs

        tip_scale = tip_scale.replace([np.inf, -np.inf], np.nan).fillna(1.0)
        tip_scale_p05 = tip_scale_p05.replace([np.inf, -np.inf], np.nan).fillna(tip_scale)
        tip_scale_p95 = tip_scale_p95.replace([np.inf, -np.inf], np.nan).fillna(tip_scale)

        bridge['TIP_obs_gwei'] = bridge['TIP_obs_gwei'].fillna(0.0)
        bridge['TIP_cf_gwei'] = bridge['TIP_obs_gwei'] * tip_scale
        bridge['TIP_cf_p05_gwei'] = bridge['TIP_obs_gwei'] * tip_scale_p05
        bridge['TIP_cf_p95_gwei'] = bridge['TIP_obs_gwei'] * tip_scale_p95

        bridge['TF_obs_gwei'] = bridge['BF_obs_gwei'] + bridge['TIP_obs_gwei']
        bridge['TF_cf_gwei'] = bridge['BF_cf_gwei'] + bridge['TIP_cf_gwei']

        # Compute welfare deltas
        logger.info("Computing welfare deltas...")
        delta_results = bridge.apply(self.compute_welfare_deltas, axis=1)
        delta_df = pd.DataFrame(delta_results.tolist())

        # Rename delta columns to match schema
        delta_df.rename(columns={
            'delta_usd_base_only': 'Delta_usd_base_only',
            'delta_usd_base_only_p05': 'Delta_usd_base_only_p05',
            'delta_usd_base_only_p95': 'Delta_usd_base_only_p95',
            'delta_usd_base_plus_tip': 'Delta_usd_base_plus_tip',
            'delta_usd_base_plus_tip_p05': 'Delta_usd_base_plus_tip_p05',
            'delta_usd_base_plus_tip_p95': 'Delta_usd_base_plus_tip_p95',
            'delta_usd_base_only_close': 'Delta_usd_base_only_close',
            'delta_usd_base_only_mean': 'Delta_usd_base_only_mean',
            'delta_usd_base_only_high': 'Delta_usd_base_only_high',
            'delta_usd_base_only_low': 'Delta_usd_base_only_low',
            'delta_usd_base_plus_tip_close': 'Delta_usd_base_plus_tip_close',
            'delta_usd_base_plus_tip_mean': 'Delta_usd_base_plus_tip_mean',
            'delta_usd_base_plus_tip_high': 'Delta_usd_base_plus_tip_high',
            'delta_usd_base_plus_tip_low': 'Delta_usd_base_plus_tip_low'
        }, inplace=True)

        # Combine with bridge
        bridge = pd.concat([bridge, delta_df], axis=1)

        # Add extrapolation flag
        bridge['is_extrapolation_day'] = (
            (bridge['date'] < WINDOW_START) | (bridge['date'] >= DENCUN_DATE)
        )

        # Ensure is_capped column exists
        if 'is_capped' not in bridge.columns:
            bridge['is_capped'] = False
        if 'is_synthetic' not in bridge.columns:
            bridge['is_synthetic'] = False

        # Filter to analysis window within pre-Dencun period
        bridge = bridge[(bridge['date'] >= WINDOW_START) & (bridge['date'] < DENCUN_DATE)]

        # Sort by date
        bridge = bridge.sort_values('date')

        return bridge

    def validate_bridge(self, bridge: pd.DataFrame) -> Dict[str, any]:
        """Validate the welfare bridge and compute sanity checks."""
        validation = {}

        # Check required columns
        required_columns = [
            'date', 'BF_obs_gwei', 'BF_cf_gwei', 'BF_cf_p05_gwei', 'BF_cf_p95_gwei',
            'TIP_obs_gwei', 'TIP_cf_gwei', 'TIP_cf_p05_gwei', 'TIP_cf_p95_gwei',
            'TF_obs_gwei', 'TF_cf_gwei', 'GAS',
            'ETHUSD_gwt', 'ETHUSD_close', 'ETHUSD_mean', 'ETHUSD_high', 'ETHUSD_low',
            'Delta_usd_base_only', 'Delta_usd_base_only_p05', 'Delta_usd_base_only_p95',
            'Delta_usd_base_only_close', 'Delta_usd_base_only_mean',
            'Delta_usd_base_only_high', 'Delta_usd_base_only_low',
            'Delta_usd_base_plus_tip', 'Delta_usd_base_plus_tip_p05', 'Delta_usd_base_plus_tip_p95',
            'Delta_usd_base_plus_tip_close', 'Delta_usd_base_plus_tip_mean',
            'Delta_usd_base_plus_tip_high', 'Delta_usd_base_plus_tip_low',
            'is_capped', 'is_extrapolation_day'
        ]

        missing_cols = [c for c in required_columns if c not in bridge.columns]
        validation['schema_complete'] = len(missing_cols) == 0
        validation['missing_columns'] = missing_cols

        # Window analysis
        window_mask = (bridge['date'] >= WINDOW_START) & (bridge['date'] < DENCUN_DATE)
        validation['total_days'] = len(bridge)
        validation['window_days'] = window_mask.sum()
        validation['window_pct'] = (validation['window_days'] / validation['total_days']) * 100

        # Compute aggregate welfare for window period
        window_data = bridge[window_mask]
        validation['window_welfare_usd'] = window_data['Delta_usd_base_only'].sum()
        validation['window_welfare_per_day'] = validation['window_welfare_usd'] / validation['window_days']
        for label in ['close', 'mean', 'high', 'low']:
            base_col = f'Delta_usd_base_only_{label}'
            tip_col = f'Delta_usd_base_plus_tip_{label}'
            if base_col in window_data.columns:
                validation[f'window_welfare_usd_{label}'] = window_data[base_col].sum()
            if tip_col in window_data.columns:
                validation[f'window_welfare_plus_tip_usd_{label}'] = window_data[tip_col].sum()

        # Full period projection (with WARNING)
        full_pre_dencun = bridge[bridge['date'] < DENCUN_DATE]
        validation['full_period_days'] = len(full_pre_dencun)
        validation['projected_full_welfare_usd'] = (
            validation['window_welfare_per_day'] * validation['full_period_days']
        )

        # Sanity check: Per-transaction bounds
        standard_tx_gas = 21_000
        complex_tx_gas = 300_000

        sample_day = window_data.iloc[len(window_data)//2]  # Middle day
        validation['sample_date'] = sample_day['date']

        # Standard transaction savings
        standard_savings = self.units.calculate_welfare_delta_usd(
            base_fee_counterfactual_gwei=sample_day['BF_cf_gwei'],
            base_fee_observed_gwei=sample_day['BF_obs_gwei'],
            total_gas_used=standard_tx_gas,
            eth_price_usd=sample_day['ETHUSD_gwt']
        )
        validation['standard_tx_savings_usd'] = standard_savings

        # Complex transaction savings
        complex_savings = self.units.calculate_welfare_delta_usd(
            base_fee_counterfactual_gwei=sample_day['BF_cf_gwei'],
            base_fee_observed_gwei=sample_day['BF_obs_gwei'],
            total_gas_used=complex_tx_gas,
            eth_price_usd=sample_day['ETHUSD_gwt']
        )
        validation['complex_tx_savings_usd'] = complex_savings

        # Check for implausible values
        validation['max_daily_delta_usd'] = bridge['Delta_usd_base_only'].max()
        validation['min_daily_delta_usd'] = bridge['Delta_usd_base_only'].min()

        # Flag if daily delta exceeds $1B (likely error)
        validation['has_implausible_values'] = (
            (bridge['Delta_usd_base_only'].abs() > 1e9).any()
        )
        validation['base_plus_tip_distinct'] = not np.allclose(
            window_data['Delta_usd_base_only'].values,
            window_data['Delta_usd_base_plus_tip'].values
        )

        return validation

    def save_welfare_bridge(self, bridge: pd.DataFrame, validation: Dict[str, any]):
        """Save the welfare bridge and associated metadata."""

        # Save main CSV
        csv_path = self.results_dir / "daily_welfare_bridge.csv"
        bridge.to_csv(csv_path, index=False)
        logger.info(f"Saved welfare bridge to: {csv_path}")

        # Also save as Parquet for efficiency
        parquet_path = self.results_dir / "daily_welfare_bridge.parquet"
        bridge.to_parquet(parquet_path, index=False)

        # Save validation results
        validation_path = self.results_dir / "welfare_bridge_validation.json"
        # Convert numpy/pandas types to Python native types
        validation_serializable = {}
        for k, v in validation.items():
            if isinstance(v, (np.integer, np.int64)):
                validation_serializable[k] = int(v)
            elif isinstance(v, (np.floating, np.float64)):
                validation_serializable[k] = float(v)
            elif isinstance(v, (np.bool_, bool)):
                validation_serializable[k] = bool(v)
            elif isinstance(v, pd.Timestamp):
                validation_serializable[k] = str(v)
            else:
                validation_serializable[k] = v

        with open(validation_path, 'w') as f:
            json.dump(validation_serializable, f, indent=2, default=str)

        # Save summary statistics
        summary = {
            'generation_timestamp': datetime.now().isoformat(),
            'date_range': {
                'start': str(bridge['date'].min()),
                'end': str(bridge['date'].max()),
                'n_days': len(bridge)
            },
            'window_analysis': {
                'start': str(WINDOW_START),
                'end': str(DENCUN_DATE),
                'days_analyzed': int(validation['window_days']) if isinstance(validation['window_days'], (np.integer, np.int64)) else validation['window_days'],
                'pct_of_total': float(validation['window_pct']) if isinstance(validation['window_pct'], (np.floating, np.float64)) else validation['window_pct'],
                'welfare_usd': float(validation['window_welfare_usd']) if isinstance(validation['window_welfare_usd'], (np.floating, np.float64)) else validation['window_welfare_usd'],
                'daily_average_usd': float(validation['window_welfare_per_day']) if isinstance(validation['window_welfare_per_day'], (np.floating, np.float64)) else validation['window_welfare_per_day']
            },
            'fee_statistics': {
                'mean_observed_gwei': float(bridge['BF_obs_gwei'].mean()),
                'mean_counterfactual_gwei': float(bridge['BF_cf_gwei'].mean()),
                'mean_difference_gwei': float((bridge['BF_cf_gwei'] - bridge['BF_obs_gwei']).mean())
            },
            'price_scenarios': {},
            'warnings': []
        }

        for label in ['close', 'mean', 'high', 'low']:
            welfare_key = f'window_welfare_usd_{label}'
            plus_tip_key = f'window_welfare_plus_tip_usd_{label}'
            scenario_entry = {}
            if welfare_key in validation:
                scenario_entry['base_only'] = float(validation[welfare_key])
            if plus_tip_key in validation:
                scenario_entry['base_plus_tip'] = float(validation[plus_tip_key])
            if scenario_entry:
                summary['price_scenarios'][label] = scenario_entry

        summary['base_plus_tip_distinct'] = bool(validation.get('base_plus_tip_distinct', True))

        # Add warnings
        if validation['window_pct'] < 20:
            summary['warnings'].append(
                f"Only {validation['window_pct']:.1f}% of data analyzed - results may not be representative"
            )

        if validation['has_implausible_values']:
            summary['warnings'].append(
                "Implausible daily welfare values detected (>$1B) - check calculations"
            )

        if not validation['schema_complete']:
            summary['warnings'].append(
                f"Missing required columns: {validation['missing_columns']}"
            )
        if not validation.get('base_plus_tip_distinct', True):
            summary['warnings'].append("Base+tip series identical to base-only; investigate tip counterfactuals.")

        summary_path = self.results_dir / "welfare_bridge_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Saved summary to: {summary_path}")


def main():
    """Main execution function."""
    generator = WelfareBridgeGenerator()

    # Load all components
    logger.info("Loading all data components...")
    components = generator.load_all_components()

    # Create welfare bridge
    bridge = generator.create_welfare_bridge(components)

    # Validate
    logger.info("Validating welfare bridge...")
    validation = generator.validate_bridge(bridge)

    # Save results
    generator.save_welfare_bridge(bridge, validation)

    # Print summary
    print("\n" + "="*70)
    print("WELFARE BRIDGE GENERATION COMPLETE")
    print("="*70)
    print(f"Date range: {bridge['date'].min()} to {bridge['date'].max()}")
    print(f"Total days: {len(bridge)}")
    print(f"Schema complete: {validation['schema_complete']}")

    print("\n--- WINDOW ANALYSIS (137 days) ---")
    print(f"Window period: {WINDOW_START.date()} to {DENCUN_DATE.date()}")
    print(f"Days in window: {validation['window_days']} ({validation['window_pct']:.1f}% of total)")
    print(f"Window welfare: ${validation['window_welfare_usd']:,.2f}")
    print(f"Daily average: ${validation['window_welfare_per_day']:,.2f}")

    print("\n--- SANITY CHECKS ---")
    print(f"Sample date: {validation['sample_date']}")
    print(f"Standard tx (21k gas) savings: ${validation['standard_tx_savings_usd']:.2f}")
    print(f"Complex tx (300k gas) savings: ${validation['complex_tx_savings_usd']:.2f}")

    print("\n--- WARNINGS ---")
    if validation['window_pct'] < 20:
        print(f"⚠️  Only {validation['window_pct']:.1f}% of pre-Dencun period analyzed!")
        print("   Results may not be representative of full period")

    if validation['has_implausible_values']:
        print(f"⚠️  Maximum daily delta: ${validation['max_daily_delta_usd']:,.2f}")
        print("   Check for calculation errors if > $1B")

    if not validation['schema_complete']:
        print(f"⚠️  Missing columns: {validation['missing_columns']}")

    print("\n" + "="*70)
    print(f"Output saved to: {generator.results_dir / 'daily_welfare_bridge.csv'}")
    print("="*70)


if __name__ == "__main__":
    main()
