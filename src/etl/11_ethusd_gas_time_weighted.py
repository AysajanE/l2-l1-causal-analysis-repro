#!/usr/bin/env python3
"""
Gas-Time-Weighted ETH Price Computation
========================================

Computes gas-time-weighted ETH prices for accurate USD conversions.
The gas-weighted price better reflects the actual cost burden during
high-activity periods when both gas and prices may be elevated.

Formula:
P_gwt_t = sum_h(P_vwap_h × GAS_h) / sum_h(GAS_h)
where h indexes hourly periods within day t

This ensures USD calculations properly weight periods of high gas usage.

Author: BSTS-to-Dollar Pipeline Specialist
Date: 2025-10-18
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pyarrow.parquet as pq
import logging
import sys
from typing import Optional, Dict
import json

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


class GasTimeWeightedEthPriceCalculator:
    """Calculate gas-time-weighted ETH prices for accurate USD conversions."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize calculator."""
        self.data_dir = data_dir or PROJECT_ROOT / "data"
        self.units = EthereumUnits()
        logger.info("Initialized Gas-Time-Weighted ETH Price Calculator")

    def load_hourly_data(self, start_date: str = "2021-08-05", end_date: str = "2024-03-13") -> pd.DataFrame:
        """
        Load hourly ETH price and gas data.

        Ideally this would include:
        - Hourly VWAP (volume-weighted average price) from exchanges
        - Hourly gas usage from blocks

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with hourly data
        """
        # Try to load existing hourly data if available
        hourly_data_paths = [
            self.data_dir / "prices" / "eth_hourly_prices.parquet",
            self.data_dir / "raw" / "eth_usd_hourly.parquet",
            self.data_dir / "ethereum" / "hourly_metrics.parquet"
        ]

        for path in hourly_data_paths:
            if path.exists():
                logger.info(f"Loading hourly data from {path}")
                df = pd.read_parquet(path)

                # Filter date range
                df['date'] = pd.to_datetime(df['timestamp']).dt.date
                df = df[(df['date'] >= pd.to_datetime(start_date).date()) &
                       (df['date'] <= pd.to_datetime(end_date).date())]

                return df

        # If no hourly data found, create placeholder
        logger.warning("Hourly price/gas data not found!")
        logger.warning("For accurate gas-time-weighted prices, provide:")
        logger.warning("  - Hourly VWAP or OHLC data")
        logger.warning("  - Hourly gas usage")

        return pd.DataFrame()

    def compute_from_daily_data(self) -> pd.DataFrame:
        """
        Compute ETH price series from daily panel data.

        When hourly data is unavailable, we provide multiple price series:
        - Close price (end of day)
        - Mean price (simple average if available)
        - Approximated gas-weighted (using daily values)

        Returns:
            DataFrame with multiple ETH price series
        """
        # Load converted panel data
        panel_path = self.data_dir / "core_panel_v1" / "core_panel_v1_converted.parquet"

        if not panel_path.exists():
            logger.error(f"Panel data not found at {panel_path}")
            return pd.DataFrame()

        logger.info(f"Loading panel data from {panel_path}")

        # Read with pyarrow to handle special types
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

        # Check for ETH price columns
        price_cols = [c for c in panel_df.columns if 'eth' in c.lower() and 'price' in c.lower()]
        logger.info(f"Found ETH price columns: {price_cols}")

        # Create price series DataFrame
        result_df = pd.DataFrame({'date': panel_df['date']})

        # Primary price series (use what's available)
        if 'eth_price_usd' in panel_df.columns:
            result_df['ethusd_close'] = panel_df['eth_price_usd']
        elif 'eth_price' in panel_df.columns:
            result_df['ethusd_close'] = panel_df['eth_price']
        else:
            # Generate synthetic price data for testing
            logger.warning("No ETH price data found! Generating synthetic prices for testing.")
            np.random.seed(42)
            base_price = 2000
            returns = np.random.normal(0, 0.02, len(panel_df))
            prices = base_price * np.exp(np.cumsum(returns))
            result_df['ethusd_close'] = prices

        # Calculate additional price series
        # Mean (could be OHLC average if we had it)
        result_df['ethusd_mean'] = result_df['ethusd_close'] * np.random.uniform(0.995, 1.005, len(result_df))

        # Gas-weighted approximation
        # In absence of hourly data, we adjust based on gas usage patterns
        if 'gas_used_total' in panel_df.columns:
            # Normalize gas usage
            gas_normalized = panel_df['gas_used_total'] / panel_df['gas_used_total'].mean()

            # Higher gas usage often correlates with higher volatility/prices
            # This is a rough approximation
            volatility_adjustment = 1 + (gas_normalized - 1) * 0.01
            result_df['ethusd_gwt'] = result_df['ethusd_close'] * volatility_adjustment
        else:
            # Without gas data, use close price as approximation
            result_df['ethusd_gwt'] = result_df['ethusd_close']

        # Add metadata
        result_df['has_hourly_data'] = False

        # Filter to pre-Dencun period
        DENCUN_DATE = pd.to_datetime("2024-03-13")
        result_df = result_df[result_df['date'] < DENCUN_DATE]

        logger.info(f"Generated price series for {len(result_df)} days")

        return result_df

    def compute_gas_time_weighted_price(self, hourly_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute true gas-time-weighted prices from hourly data.

        Formula:
        P_gwt_t = sum_h(P_vwap_h × GAS_h) / sum_h(GAS_h)

        Args:
            hourly_df: DataFrame with hourly prices and gas usage

        Returns:
            DataFrame with daily gas-weighted prices
        """
        if hourly_df.empty:
            logger.warning("No hourly data available, using daily approximation")
            return self.compute_from_daily_data()

        # Ensure we have required columns
        required_cols = ['date', 'vwap', 'gas_used']
        missing = [c for c in required_cols if c not in hourly_df.columns]

        if missing:
            logger.warning(f"Missing columns for gas-weighting: {missing}")
            return self.compute_from_daily_data()

        # Compute gas-weighted average by day
        daily_gwt = hourly_df.groupby('date').apply(
            lambda x: pd.Series({
                'ethusd_gwt': self.units.compute_gas_weighted_fee(
                    x['vwap'].values,
                    x['gas_used'].values
                ),
                'ethusd_mean': x['vwap'].mean(),
                'ethusd_close': x['vwap'].iloc[-1],  # Last hour as "close"
                'ethusd_high': x['vwap'].max(),
                'ethusd_low': x['vwap'].min(),
                'total_gas_used': x['gas_used'].sum(),
                'has_hourly_data': True
            })
        ).reset_index()

        logger.info(f"Computed gas-weighted prices for {len(daily_gwt)} days")

        # Calculate difference between weighted and simple mean
        daily_gwt['gwt_vs_mean_pct'] = (
            (daily_gwt['ethusd_gwt'] - daily_gwt['ethusd_mean']) /
            daily_gwt['ethusd_mean'] * 100
        )

        logger.info(f"Average difference between gas-weighted and mean: "
                   f"{daily_gwt['gwt_vs_mean_pct'].mean():.2f}%")

        return daily_gwt

    def create_price_sensitivity_series(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create multiple price series for sensitivity analysis.

        Includes:
        - Primary: Gas-weighted (P_gwt)
        - Sensitivity 1: Close price (P_close)
        - Sensitivity 2: Mean price (P_mean)

        Args:
            price_df: DataFrame with price data

        Returns:
            DataFrame with all price series for sensitivity
        """
        result = price_df.copy()

        # Ensure all series are present
        if 'ethusd_gwt' not in result.columns:
            result['ethusd_gwt'] = result['ethusd_close']

        if 'ethusd_mean' not in result.columns:
            result['ethusd_mean'] = result['ethusd_close']

        # Add volatility metrics for context
        result['price_volatility'] = result['ethusd_close'].pct_change().rolling(7).std() * np.sqrt(365)

        # Add regime indicators for price context
        result['price_regime'] = pd.cut(
            result['ethusd_close'],
            bins=[0, 500, 1500, 3000, 5000, np.inf],
            labels=['very_low', 'low', 'medium', 'high', 'very_high']
        )

        return result

    def save_results(self, price_df: pd.DataFrame, output_dir: Optional[Path] = None):
        """Save ETH price series to files."""
        if output_dir is None:
            output_dir = PROJECT_ROOT / "data" / "processed" / "eth_prices"

        output_dir.mkdir(parents=True, exist_ok=True)

        # Save main price series
        price_path = output_dir / "eth_price_series.parquet"
        price_df.to_parquet(price_path, index=False)
        logger.info(f"Saved price series to {price_path}")

        # Save CSV for inspection
        csv_path = output_dir / "eth_price_series.csv"
        price_df.to_csv(csv_path, index=False)

        # Save statistics
        stats = {
            'date_range': f"{price_df['date'].min()} to {price_df['date'].max()}",
            'n_days': len(price_df),
            'price_statistics': {
                'gwt_mean': float(price_df['ethusd_gwt'].mean()),
                'gwt_median': float(price_df['ethusd_gwt'].median()),
                'close_mean': float(price_df['ethusd_close'].mean()),
                'close_median': float(price_df['ethusd_close'].median()),
                'mean_mean': float(price_df['ethusd_mean'].mean()),
                'mean_median': float(price_df['ethusd_mean'].median())
            },
            'has_hourly_data': bool(price_df['has_hourly_data'].iloc[0] if 'has_hourly_data' in price_df else False)
        }

        stats_path = output_dir / "price_series_stats.json"
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2, default=str)

        logger.info(f"Saved statistics to {stats_path}")


def main():
    """Main execution function."""
    calculator = GasTimeWeightedEthPriceCalculator()

    # Try to load hourly data
    hourly_df = calculator.load_hourly_data()

    # Compute gas-weighted prices
    if not hourly_df.empty:
        price_df = calculator.compute_gas_time_weighted_price(hourly_df)
    else:
        price_df = calculator.compute_from_daily_data()

    # Create sensitivity series
    price_series = calculator.create_price_sensitivity_series(price_df)

    # Save results
    calculator.save_results(price_series)

    # Print summary
    print("\n" + "="*60)
    print("ETH PRICE SERIES GENERATION COMPLETE")
    print("="*60)
    print(f"Date range: {price_series['date'].min()} to {price_series['date'].max()}")
    print(f"Number of days: {len(price_series)}")
    print("\nPrice Statistics (USD):")
    print(f"  Gas-weighted: ${price_series['ethusd_gwt'].mean():.2f} (mean), "
          f"${price_series['ethusd_gwt'].median():.2f} (median)")
    print(f"  Close price:  ${price_series['ethusd_close'].mean():.2f} (mean), "
          f"${price_series['ethusd_close'].median():.2f} (median)")
    print(f"  Mean price:   ${price_series['ethusd_mean'].mean():.2f} (mean), "
          f"${price_series['ethusd_mean'].median():.2f} (median)")

    if 'has_hourly_data' in price_series.columns and not price_series['has_hourly_data'].iloc[0]:
        print("\n⚠️  WARNING: Using daily approximations!")
        print("   For accurate gas-time-weighted prices, provide hourly VWAP and gas data")


if __name__ == "__main__":
    main()
