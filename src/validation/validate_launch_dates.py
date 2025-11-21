"""
Launch Date Validation Script

This script validates that L2 chain launch dates in the treatment data
match the expected mainnet launch dates.

Purpose:
    - Prevent regression of launch date errors
    - Ensure no pre-mainnet activity in treatment data
    - Verify data integrity for causal analysis

Expected Launch Dates:
    - Arbitrum: 2021-08-31 (Arbitrum One mainnet launch)
    - Optimism: 2021-12-16 (Optimism mainnet launch)
    - Base: 2023-08-09 (Base mainnet launch)
    - zkSync Era: 2023-03-24 (zkSync Era mainnet launch)
    - Linea: 2023-07-11 (Linea mainnet launch)
    - Starknet: 2021-11-16 (Starknet Alpha mainnet launch)
    - Scroll: 2023-10-10 (Scroll mainnet launch)

Author: Visualization Lead
Date: 2025-10-07
"""

import pandas as pd
import sys
from pathlib import Path
from typing import Dict, Tuple

# Expected mainnet launch dates (source: official chain documentation)
EXPECTED_LAUNCH_DATES = {
    'arbitrum': pd.Timestamp('2021-08-31'),
    'optimism': pd.Timestamp('2021-12-16'),
    'base': pd.Timestamp('2023-08-09'),
    'zksync': pd.Timestamp('2023-03-24'),
    'linea': pd.Timestamp('2023-07-11'),
    'starknet': pd.Timestamp('2021-11-16'),  # Starknet Alpha mainnet
    'scroll': pd.Timestamp('2023-10-10')
}

# Tolerance (days) - allow for data aggregation edge cases
DATE_TOLERANCE_DAYS = 1


def validate_launch_dates(csv_path: str, verbose: bool = True) -> Tuple[bool, Dict]:
    """
    Validate L2 chain launch dates in treatment data.

    Parameters
    ----------
    csv_path : str
        Path to treatment CSV file
    verbose : bool
        Print detailed validation output

    Returns
    -------
    tuple
        (all_valid: bool, results: dict)
    """
    # Load data
    df = pd.read_csv(csv_path, parse_dates=['date'])

    results = {}
    all_valid = True

    if verbose:
        print("=" * 80)
        print("L2 CHAIN LAUNCH DATE VALIDATION")
        print("=" * 80)
        print(f"\nData source: {csv_path}")
        print(f"Total rows: {len(df)}")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}\n")

    # Check each chain
    for chain, expected_date in EXPECTED_LAUNCH_DATES.items():
        # Try both column naming conventions
        col_clean = f'A_{chain}_clean'
        col_raw = f'A_{chain}'

        col = col_clean if col_clean in df.columns else col_raw if col_raw in df.columns else None

        if col is None:
            if verbose:
                print(f"⚠️  {chain.capitalize():<15} SKIPPED (column not found)")
            results[chain] = {'status': 'SKIPPED', 'reason': 'Column not found'}
            continue

        # Find first non-zero date
        chain_data = df[df[col] > 0]

        if len(chain_data) == 0:
            if verbose:
                print(f"⚠️  {chain.capitalize():<15} SKIPPED (no activity found)")
            results[chain] = {'status': 'SKIPPED', 'reason': 'No activity'}
            continue

        actual_date = chain_data['date'].min()
        date_diff = (actual_date - expected_date).days

        # Check if within tolerance
        is_valid = abs(date_diff) <= DATE_TOLERANCE_DAYS

        if is_valid:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            all_valid = False

        results[chain] = {
            'status': 'PASS' if is_valid else 'FAIL',
            'expected': expected_date,
            'actual': actual_date,
            'diff_days': date_diff,
            'column': col
        }

        if verbose:
            print(f"{status}  {chain.capitalize():<15} "
                  f"Expected: {expected_date.date()}  "
                  f"Actual: {actual_date.date()}  "
                  f"Diff: {date_diff:+3d} days")

    # Check for pre-mainnet activity (any activity before earliest expected launch)
    earliest_launch = min(EXPECTED_LAUNCH_DATES.values())
    pre_mainnet_activity = df[df['date'] < earliest_launch]['A_t_clean'].sum() if 'A_t_clean' in df.columns else 0

    if verbose:
        print("\n" + "=" * 80)
        print("PRE-MAINNET ACTIVITY CHECK")
        print("=" * 80)
        print(f"Earliest expected launch: {earliest_launch.date()}")
        print(f"Total A_t_clean before {earliest_launch.date()}: {pre_mainnet_activity:.6f}")

        if pre_mainnet_activity > 0:
            print("❌ FAIL: Pre-mainnet activity detected!")
            all_valid = False
        else:
            print("✅ PASS: No pre-mainnet activity")

    results['pre_mainnet_check'] = {
        'status': 'PASS' if pre_mainnet_activity == 0 else 'FAIL',
        'total_activity': pre_mainnet_activity
    }

    if verbose:
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        if all_valid:
            print("✅ ALL CHECKS PASSED")
        else:
            print("❌ VALIDATION FAILED - Fix launch dates before proceeding")
        print("=" * 80 + "\n")

    return all_valid, results


def main():
    """Command-line interface."""
    # Default path to corrected CSV
    default_path = Path(__file__).parent.parent.parent / 'docs' / 'treatment_timeseries_full_CORRECTED.csv'

    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = str(default_path)

    # Validate
    all_valid, results = validate_launch_dates(csv_path, verbose=True)

    # Exit with appropriate code
    sys.exit(0 if all_valid else 1)


if __name__ == '__main__':
    main()
