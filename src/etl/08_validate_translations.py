#!/usr/bin/env python3
"""
Validate ETH Price Translation Pipeline
========================================

This module validates the accuracy of all conversions and data quality
in the ETH price translation pipeline.

Author: Data Engineering Lead
Date: 2025-01-10
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from typing import Dict, List, Tuple

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.price_conversions import (
    wei_to_gwei, gwei_to_wei,
    wei_to_eth, eth_to_wei,
    gwei_to_eth, eth_to_gwei,
    wei_to_usd, calculate_transaction_cost_usd
)

# Set working directory
WORK_DIR = Path("/Users/aeziz-local/Research/Projects-05-Ethereum Blockchain Economic Analysis/Causal Influence of L2 Scaling Solutions on Ethereum L1 Mainnet Congestion/L1-L2-causal-influence-analysis/wt/analysis-r")


def validate_unit_conversions() -> Dict[str, bool]:
    """Validate all unit conversion functions."""

    results = {}
    tolerance = 1e-10  # Numerical tolerance

    # Test Wei <-> Gwei
    test_wei = 1_234_567_890_000
    converted_gwei = wei_to_gwei(test_wei)
    back_to_wei = gwei_to_wei(converted_gwei)
    results['wei_gwei_roundtrip'] = abs(back_to_wei - test_wei) < tolerance

    # Test Wei <-> ETH
    test_wei = 1_234_567_890_123_456_789
    converted_eth = wei_to_eth(test_wei)
    back_to_wei = eth_to_wei(converted_eth)
    results['wei_eth_roundtrip'] = abs(back_to_wei - test_wei) < tolerance

    # Test Gwei <-> ETH
    test_gwei = 1_234_567_890
    converted_eth = gwei_to_eth(test_gwei)
    back_to_gwei = eth_to_gwei(converted_eth)
    results['gwei_eth_roundtrip'] = abs(back_to_gwei - test_gwei) < tolerance

    # Test array operations
    test_array = np.array([1e18, 2e18, 3e18])
    converted_array = wei_to_eth(test_array)
    expected_array = np.array([1.0, 2.0, 3.0])
    results['array_conversion'] = np.allclose(converted_array, expected_array)

    return results


def validate_transaction_costs() -> Dict[str, bool]:
    """Validate transaction cost calculations."""

    results = {}

    # Load generated costs
    costs_df = pd.read_parquet(WORK_DIR / "results/bsts/transaction_costs_daily.parquet")

    # Sample validation: Recalculate some costs
    sample_idx = 100
    sample_row = costs_df.iloc[sample_idx]

    # Recalculate standard transaction cost
    base_fee_wei = sample_row['base_fee_wei']
    standard_gas = 21_000
    recalc_cost_wei = base_fee_wei * standard_gas
    recalc_cost_usd = wei_to_usd(recalc_cost_wei, sample_row['eth_price_usd'])

    results['standard_tx_wei_match'] = abs(
        recalc_cost_wei - sample_row['standard_tx_cost_wei']
    ) < 1  # Within 1 Wei

    results['standard_tx_usd_match'] = abs(
        recalc_cost_usd - sample_row['standard_tx_cost_usd']
    ) < 0.01  # Within 1 cent

    # Check that all costs are non-negative
    results['all_costs_non_negative'] = (
        (costs_df['standard_tx_cost_usd'] >= 0).all() and
        (costs_df['complex_tx_cost_usd'] >= 0).all()
    )

    # Check that complex costs > standard costs
    results['complex_greater_than_standard'] = (
        costs_df['complex_tx_cost_usd'] > costs_df['standard_tx_cost_usd']
    ).all()

    return results


def validate_eth_prices() -> Dict[str, bool]:
    """Validate ETH price data quality."""

    results = {}

    # Load ETH prices
    eth_prices = pd.read_parquet(WORK_DIR / "data/analytical/eth_price_series.parquet")

    # Check for reasonable price range
    results['price_range_reasonable'] = (
        (eth_prices['eth_price_usd'] > 50).all() and  # Min reasonable price
        (eth_prices['eth_price_usd'] < 10000).all()   # Max reasonable price
    )

    # Check that moving averages are smoother than spot
    spot_volatility = eth_prices['eth_price_usd'].std()
    ma7_volatility = eth_prices['eth_price_usd_7d_ma'].std()
    ma30_volatility = eth_prices['eth_price_usd_30d_ma'].std()

    results['ma7_smoother_than_spot'] = ma7_volatility < spot_volatility
    results['ma30_smoother_than_ma7'] = ma30_volatility < ma7_volatility

    # Check confidence intervals
    results['ci_contains_spot'] = (
        (eth_prices['eth_price_usd'] >= eth_prices['eth_price_usd_lower_95']) &
        (eth_prices['eth_price_usd'] <= eth_prices['eth_price_usd_upper_95'])
    ).mean() > 0.90  # At least 90% of spot prices within CI

    # Check temporal continuity
    date_diffs = eth_prices['date'].diff().dt.days.dropna()
    results['no_date_gaps'] = (date_diffs == 1).all()

    return results


def validate_regime_statistics() -> Dict[str, bool]:
    """Validate regime-based statistics."""

    results = {}

    # Load regime stats
    regime_stats = pd.read_csv(WORK_DIR / "results/bsts/transaction_costs_by_regime.csv")

    # Check that regimes are in chronological order
    regime_order = ['London-Merge', 'Merge-Dencun', 'Post-Dencun']
    actual_order = regime_stats['regime'].tolist()
    results['regime_order_correct'] = actual_order == regime_order

    # Check that costs decreased over time (expected trend)
    london_avg = regime_stats[regime_stats['regime'] == 'London-Merge']['avg_standard_tx_usd'].iloc[0]
    dencun_avg = regime_stats[regime_stats['regime'] == 'Post-Dencun']['avg_standard_tx_usd'].iloc[0]
    results['costs_decreased_over_time'] = dencun_avg < london_avg

    # Check that all statistics are non-negative
    numeric_cols = regime_stats.select_dtypes(include=[np.number]).columns
    results['all_stats_non_negative'] = (regime_stats[numeric_cols] >= 0).all().all()

    return results


def validate_lookup_table() -> Dict[str, bool]:
    """Validate the lookup table accuracy."""

    results = {}

    # Load lookup table
    lookup = pd.read_csv(WORK_DIR / "results/bsts/transaction_cost_lookup.csv")

    # Spot check a calculation
    test_row = lookup[
        (lookup['base_fee_gwei'] == 50) &
        (lookup['gas_used'] == 21_000) &
        (lookup['regime'] == 'Post-Dencun')
    ].iloc[0]

    # Recalculate
    base_fee_wei = gwei_to_wei(test_row['base_fee_gwei'])
    cost_wei_recalc = base_fee_wei * test_row['gas_used']
    cost_usd_recalc = wei_to_usd(cost_wei_recalc, test_row['eth_price_usd'])

    results['lookup_calculation_accurate'] = abs(
        cost_usd_recalc - test_row['cost_usd']
    ) < 0.01

    # Check that costs scale linearly with gas
    base_50_gas_21k = lookup[
        (lookup['base_fee_gwei'] == 50) &
        (lookup['gas_used'] == 21_000) &
        (lookup['regime'] == 'Post-Dencun')
    ]['cost_usd'].iloc[0]

    base_50_gas_42k = lookup[
        (lookup['base_fee_gwei'] == 50) &
        (lookup['gas_used'] == 50_000) &
        (lookup['regime'] == 'Post-Dencun')
    ]['cost_usd'].iloc[0]

    # Since 50k is not in our standard values, check 100k vs 200k
    base_50_gas_100k = lookup[
        (lookup['base_fee_gwei'] == 50) &
        (lookup['gas_used'] == 100_000) &
        (lookup['regime'] == 'Post-Dencun')
    ]['cost_usd'].iloc[0]

    base_50_gas_200k = lookup[
        (lookup['base_fee_gwei'] == 50) &
        (lookup['gas_used'] == 200_000) &
        (lookup['regime'] == 'Post-Dencun')
    ]['cost_usd'].iloc[0]

    # Should be exactly 2x
    results['costs_scale_linearly'] = abs(
        base_50_gas_200k / base_50_gas_100k - 2.0
    ) < 0.001

    return results


def generate_validation_report(validation_results: Dict[str, Dict[str, bool]]):
    """Generate a validation report."""

    report = []
    report.append("="*70)
    report.append("ETH PRICE TRANSLATION PIPELINE VALIDATION REPORT")
    report.append("="*70)
    report.append("")

    all_passed = True

    for category, results in validation_results.items():
        report.append(f"\n{category.replace('_', ' ').title()}:")
        report.append("-" * 40)

        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            report.append(f"  {test_name.replace('_', ' ').title()}: {status}")

            if not passed:
                all_passed = False

    report.append("\n" + "="*70)

    if all_passed:
        report.append("OVERALL STATUS: ✓ ALL VALIDATIONS PASSED")
    else:
        report.append("OVERALL STATUS: ✗ SOME VALIDATIONS FAILED")

    report.append("="*70)

    return "\n".join(report), all_passed


def save_validation_report(report: str, all_passed: bool):
    """Save the validation report to file."""

    results_dir = WORK_DIR / "results/bsts"
    report_path = results_dir / "validation_report.txt"

    with open(report_path, 'w') as f:
        f.write(report)

    print(f"\nValidation report saved to: {report_path}")

    # Also save a JSON summary
    import json
    summary = {
        'validation_passed': all_passed,
        'timestamp': pd.Timestamp.now().isoformat(),
        'report_path': str(report_path)
    }

    summary_path = results_dir / "validation_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"Validation summary saved to: {summary_path}")


if __name__ == "__main__":
    print("Running ETH Price Translation Pipeline Validation...")
    print("="*70)

    # Run all validations
    validation_results = {
        'unit_conversions': validate_unit_conversions(),
        'transaction_costs': validate_transaction_costs(),
        'eth_prices': validate_eth_prices(),
        'regime_statistics': validate_regime_statistics(),
        'lookup_table': validate_lookup_table()
    }

    # Generate report
    report, all_passed = generate_validation_report(validation_results)

    # Print report
    print(report)

    # Save report
    save_validation_report(report, all_passed)

    # Exit with appropriate code
    if not all_passed:
        print("\n⚠️  WARNING: Some validations failed. Please review the report.")
        sys.exit(1)
    else:
        print("\n✅ All validations passed successfully!")
        sys.exit(0)