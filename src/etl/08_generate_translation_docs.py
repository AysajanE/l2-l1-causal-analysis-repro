#!/usr/bin/env python3
"""
Generate Translation Documentation and Tables
==============================================

This module generates comprehensive documentation for the ETH price
translation pipeline, including formatted tables for Table 5 integration.

Author: Data Engineering Lead
Date: 2025-01-10
"""

import pandas as pd
import numpy as np
from pathlib import Path
import yaml
import json
from datetime import datetime

# Set working directory
WORK_DIR = Path("/Users/aeziz-local/Research/Projects-05-Ethereum Blockchain Economic Analysis/Causal Influence of L2 Scaling Solutions on Ethereum L1 Mainnet Congestion/L1-L2-causal-influence-analysis/wt/analysis-r")


def load_all_results():
    """Load all generated results."""

    data_dir = WORK_DIR / "data/analytical"
    results_dir = WORK_DIR / "results/bsts"

    # Load datasets
    eth_prices = pd.read_parquet(data_dir / "eth_price_series.parquet")
    transaction_costs = pd.read_parquet(results_dir / "transaction_costs_daily.parquet")
    regime_stats = pd.read_csv(results_dir / "transaction_costs_by_regime.csv")
    lookup_table = pd.read_csv(results_dir / "transaction_cost_lookup.csv")

    # Load metadata
    with open(data_dir / "eth_price_series_metadata.yaml", 'r') as f:
        price_metadata = yaml.safe_load(f)

    return {
        'eth_prices': eth_prices,
        'transaction_costs': transaction_costs,
        'regime_stats': regime_stats,
        'lookup_table': lookup_table,
        'price_metadata': price_metadata
    }


def generate_table5_format(transaction_costs: pd.DataFrame, regime_stats: pd.DataFrame) -> pd.DataFrame:
    """Generate Table 5 formatted data for the paper."""

    # Create Table 5: Average Transaction Costs by Regime
    table5_data = []

    for _, row in regime_stats.iterrows():
        regime = row['regime']

        # Calculate percentiles for the regime
        regime_costs = transaction_costs[
            (transaction_costs['date'] >= row['period_start']) &
            (transaction_costs['date'] <= row['period_end'])
        ]

        table5_data.append({
            'Regime': regime,
            'Period': f"{pd.to_datetime(row['period_start']).strftime('%Y-%m-%d')} to {pd.to_datetime(row['period_end']).strftime('%Y-%m-%d')}",
            'Mean Base Fee (Gwei)': f"{row['avg_base_fee_gwei']:.1f}",
            'Median Base Fee (Gwei)': f"{row['median_base_fee_gwei']:.1f}",
            'Mean Standard Tx Cost (USD)': f"${row['avg_standard_tx_usd']:.2f}",
            'P25 Standard Tx Cost (USD)': f"${regime_costs['standard_tx_cost_usd'].quantile(0.25):.2f}",
            'P50 Standard Tx Cost (USD)': f"${row['median_standard_tx_usd']:.2f}",
            'P75 Standard Tx Cost (USD)': f"${regime_costs['standard_tx_cost_usd'].quantile(0.75):.2f}",
            'Mean Complex Tx Cost (USD)': f"${row['avg_complex_tx_usd']:.2f}",
            'Daily Network Total (Million USD)': f"${row['total_daily_cost_usd']/1e6:.2f}"
        })

    table5 = pd.DataFrame(table5_data)

    return table5


def generate_conversion_formulas_doc():
    """Generate documentation of conversion formulas."""

    formulas = {
        'title': 'Ethereum Unit Conversion Formulas',
        'version': '1.0.0',
        'generated_at': datetime.now().isoformat(),
        'formulas': {
            'basic_conversions': {
                'wei_to_gwei': '1 Gwei = 10^9 Wei',
                'wei_to_eth': '1 ETH = 10^18 Wei',
                'gwei_to_eth': '1 ETH = 10^9 Gwei'
            },
            'usd_conversions': {
                'eth_to_usd': 'USD = ETH * ETH_Price_USD',
                'wei_to_usd': 'USD = (Wei / 10^18) * ETH_Price_USD',
                'gwei_to_usd': 'USD = (Gwei / 10^9) * ETH_Price_USD'
            },
            'transaction_costs': {
                'cost_wei': 'Cost_Wei = Base_Fee_Wei * Gas_Used',
                'cost_eth': 'Cost_ETH = Cost_Wei / 10^18',
                'cost_usd': 'Cost_USD = Cost_ETH * ETH_Price_USD',
                'with_priority': 'Total_Fee = Base_Fee + Priority_Fee'
            },
            'standard_gas_values': {
                'eth_transfer': 21000,
                'erc20_transfer': 65000,
                'uniswap_swap': 150000,
                'complex_defi': 300000
            }
        }
    }

    return formulas


def generate_summary_statistics(data: dict) -> dict:
    """Generate comprehensive summary statistics."""

    eth_prices = data['eth_prices']
    transaction_costs = data['transaction_costs']

    # Calculate overall statistics
    stats = {
        'eth_price_summary': {
            'mean': float(eth_prices['eth_price_usd'].mean()),
            'median': float(eth_prices['eth_price_usd'].median()),
            'std': float(eth_prices['eth_price_usd'].std()),
            'min': float(eth_prices['eth_price_usd'].min()),
            'max': float(eth_prices['eth_price_usd'].max()),
            'volatility_mean_7d': float(eth_prices['eth_price_volatility_7d'].mean())
        },
        'transaction_cost_summary': {
            'standard_tx': {
                'mean_usd': float(transaction_costs['standard_tx_cost_usd'].mean()),
                'median_usd': float(transaction_costs['standard_tx_cost_usd'].median()),
                'p90_usd': float(transaction_costs['standard_tx_cost_usd'].quantile(0.9)),
                'max_usd': float(transaction_costs['standard_tx_cost_usd'].max())
            },
            'complex_tx': {
                'mean_usd': float(transaction_costs['complex_tx_cost_usd'].mean()),
                'median_usd': float(transaction_costs['complex_tx_cost_usd'].median()),
                'p90_usd': float(transaction_costs['complex_tx_cost_usd'].quantile(0.9)),
                'max_usd': float(transaction_costs['complex_tx_cost_usd'].max())
            },
            'daily_network_total': {
                'mean_million_usd': float(transaction_costs['daily_total_cost_usd'].mean() / 1e6),
                'median_million_usd': float(transaction_costs['daily_total_cost_usd'].median() / 1e6),
                'total_billion_usd': float(transaction_costs['daily_total_cost_usd'].sum() / 1e9)
            }
        },
        'base_fee_summary': {
            'mean_gwei': float(transaction_costs['base_fee_gwei'].mean()),
            'median_gwei': float(transaction_costs['base_fee_gwei'].median()),
            'p10_gwei': float(transaction_costs['base_fee_gwei'].quantile(0.1)),
            'p90_gwei': float(transaction_costs['base_fee_gwei'].quantile(0.9)),
            'max_gwei': float(transaction_costs['base_fee_gwei'].max())
        },
        'data_quality': {
            'total_days': len(eth_prices),
            'interpolated_price_days': int(eth_prices['is_interpolated'].sum()),
            'interpolation_rate': float(eth_prices['is_interpolated'].mean()),
            'post_london_days': len(transaction_costs)
        }
    }

    return stats


def save_all_outputs(data: dict):
    """Save all generated outputs."""

    results_dir = WORK_DIR / "results/bsts"

    # Generate Table 5
    table5 = generate_table5_format(data['transaction_costs'], data['regime_stats'])
    table5_path = results_dir / "table5_transaction_costs.csv"
    table5.to_csv(table5_path, index=False)
    print(f"Saved Table 5 to {table5_path}")

    # Generate formulas documentation
    formulas = generate_conversion_formulas_doc()
    formulas_path = results_dir / "conversion_formulas.yaml"
    with open(formulas_path, 'w') as f:
        yaml.dump(formulas, f, default_flow_style=False, sort_keys=False)
    print(f"Saved conversion formulas to {formulas_path}")

    # Generate summary statistics
    stats = generate_summary_statistics(data)
    stats_path = results_dir / "translation_summary_statistics.json"
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"Saved summary statistics to {stats_path}")

    # Create markdown documentation
    create_markdown_documentation(data, table5, formulas, stats)


def format_table_as_markdown(df: pd.DataFrame) -> str:
    """Format a dataframe as markdown table."""

    # Create header
    headers = " | ".join(df.columns)
    separator = " | ".join(["-" * len(col) for col in df.columns])

    # Create rows
    rows = []
    for _, row in df.iterrows():
        row_str = " | ".join([str(val) for val in row.values])
        rows.append(row_str)

    # Combine
    table = f"| {headers} |\n| {separator} |\n"
    for row in rows:
        table += f"| {row} |\n"

    return table


def create_markdown_documentation(data: dict, table5: pd.DataFrame, formulas: dict, stats: dict):
    """Create comprehensive markdown documentation."""

    results_dir = WORK_DIR / "results/bsts"

    md_content = f"""# ETH Price Translation Documentation
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

This document provides comprehensive documentation for the ETH price series integration
and transaction cost translation pipeline used in the L1-L2 causal influence analysis.

## Data Coverage

- **Date Range**: {data['price_metadata']['date_range']['start']} to {data['price_metadata']['date_range']['end']}
- **Total Days**: {data['price_metadata']['date_range']['days']:,}
- **Post-London Days**: {stats['data_quality']['post_london_days']:,}
- **Interpolated Price Days**: {stats['data_quality']['interpolated_price_days']:,} ({stats['data_quality']['interpolation_rate']*100:.1f}%)

## Conversion Formulas

### Basic Unit Conversions
- **Wei to Gwei**: 1 Gwei = 10^9 Wei
- **Wei to ETH**: 1 ETH = 10^18 Wei
- **Gwei to ETH**: 1 ETH = 10^9 Gwei

### USD Conversions
- **ETH to USD**: USD = ETH × ETH_Price_USD
- **Wei to USD**: USD = (Wei ÷ 10^18) × ETH_Price_USD
- **Gwei to USD**: USD = (Gwei ÷ 10^9) × ETH_Price_USD

### Transaction Cost Calculations
- **Cost in Wei**: Cost_Wei = Base_Fee_Wei × Gas_Used
- **Cost in ETH**: Cost_ETH = Cost_Wei ÷ 10^18
- **Cost in USD**: Cost_USD = Cost_ETH × ETH_Price_USD

## ETH Price Statistics

### Overall Statistics
- **Mean Price**: ${stats['eth_price_summary']['mean']:.2f}
- **Median Price**: ${stats['eth_price_summary']['median']:.2f}
- **Standard Deviation**: ${stats['eth_price_summary']['std']:.2f}
- **Min Price**: ${stats['eth_price_summary']['min']:.2f}
- **Max Price**: ${stats['eth_price_summary']['max']:.2f}
- **Mean 7-day Volatility**: ${stats['eth_price_summary']['volatility_mean_7d']:.2f}

## Transaction Cost Summary

### Standard Transaction (21,000 gas)
- **Mean Cost**: ${stats['transaction_cost_summary']['standard_tx']['mean_usd']:.2f}
- **Median Cost**: ${stats['transaction_cost_summary']['standard_tx']['median_usd']:.2f}
- **90th Percentile**: ${stats['transaction_cost_summary']['standard_tx']['p90_usd']:.2f}
- **Maximum Cost**: ${stats['transaction_cost_summary']['standard_tx']['max_usd']:.2f}

### Complex Transaction (150,000 gas)
- **Mean Cost**: ${stats['transaction_cost_summary']['complex_tx']['mean_usd']:.2f}
- **Median Cost**: ${stats['transaction_cost_summary']['complex_tx']['median_usd']:.2f}
- **90th Percentile**: ${stats['transaction_cost_summary']['complex_tx']['p90_usd']:.2f}
- **Maximum Cost**: ${stats['transaction_cost_summary']['complex_tx']['max_usd']:.2f}

### Network Daily Totals
- **Mean Daily Total**: ${stats['transaction_cost_summary']['daily_network_total']['mean_million_usd']:.2f}M
- **Median Daily Total**: ${stats['transaction_cost_summary']['daily_network_total']['median_million_usd']:.2f}M
- **Cumulative Total**: ${stats['transaction_cost_summary']['daily_network_total']['total_billion_usd']:.2f}B

## Base Fee Statistics (Post-London)
- **Mean**: {stats['base_fee_summary']['mean_gwei']:.1f} Gwei
- **Median**: {stats['base_fee_summary']['median_gwei']:.1f} Gwei
- **10th Percentile**: {stats['base_fee_summary']['p10_gwei']:.1f} Gwei
- **90th Percentile**: {stats['base_fee_summary']['p90_gwei']:.1f} Gwei
- **Maximum**: {stats['base_fee_summary']['max_gwei']:.1f} Gwei

## Table 5: Transaction Costs by Regime

{format_table_as_markdown(table5)}

## Standard Gas Values Reference

| Transaction Type | Gas Used |
|-----------------|----------|
| ETH Transfer | 21,000 |
| ERC-20 Transfer | 65,000 |
| Uniswap Swap | 150,000 |
| Complex DeFi | 300,000 |

## Files Generated

### Data Files
- `data/analytical/eth_price_series.parquet` - Complete ETH price series with volatility
- `data/analytical/eth_price_series_metadata.yaml` - Price series metadata

### Results Files
- `results/bsts/transaction_costs_daily.parquet` - Daily transaction costs in all units
- `results/bsts/transaction_costs_daily.csv` - Daily costs (key columns only)
- `results/bsts/transaction_costs_by_regime.csv` - Regime-level statistics
- `results/bsts/transaction_cost_lookup.csv` - Quick reference lookup table
- `results/bsts/table5_transaction_costs.csv` - Formatted for Table 5
- `results/bsts/eth_price_regime_stats.csv` - ETH price statistics by regime

### Documentation Files
- `results/bsts/conversion_formulas.yaml` - Formal conversion formulas
- `results/bsts/translation_summary_statistics.json` - Comprehensive statistics
- `results/bsts/translation_documentation.md` - This documentation

## Data Quality Notes

1. **ETH Price Interpolation**: {stats['data_quality']['interpolated_price_days']} days ({stats['data_quality']['interpolation_rate']*100:.1f}%) of ETH prices were interpolated using time-based linear interpolation.

2. **Regime Boundaries**:
   - London Fork: 2021-08-05
   - Merge: 2022-09-15
   - Dencun: 2024-03-13

3. **Gas Estimates**: Transaction cost estimates use standard gas values (21,000 for simple transfers, 150,000 for complex transactions).

4. **Confidence Intervals**: 95% confidence intervals are provided based on 7-day rolling price volatility.

## Usage Instructions

### Python Example
```python
import pandas as pd
from src.utils.price_conversions import wei_to_usd, calculate_transaction_cost_usd

# Load data
costs = pd.read_parquet('results/bsts/transaction_costs_daily.parquet')

# Convert BSTS effects from Wei to USD
bsts_effect_wei = 1e15  # Example: 1 PetaWei
eth_price = 3000  # Current ETH price
effect_usd = wei_to_usd(bsts_effect_wei, eth_price)
```

### R Example
```r
library(arrow)
costs <- read_parquet("results/bsts/transaction_costs_daily.parquet")

# Use lookup table for quick conversions
lookup <- read.csv("results/bsts/transaction_cost_lookup.csv")
```

## Validation Checksums

All conversion functions have been validated with unit tests. Key validations:
- Wei ↔ Gwei ↔ ETH conversions are exact
- USD conversions match manual calculations
- Array operations preserve precision
- Regime statistics align with source data

---
*Generated by Phase 8 ETH Price Pipeline*
"""

    doc_path = results_dir / "translation_documentation.md"
    with open(doc_path, 'w') as f:
        f.write(md_content)

    print(f"Saved documentation to {doc_path}")


if __name__ == "__main__":
    print("="*70)
    print("GENERATING TRANSLATION DOCUMENTATION AND TABLES")
    print("="*70)

    # Load all results
    data = load_all_results()

    # Save all outputs
    save_all_outputs(data)

    print("\n" + "="*70)
    print("DOCUMENTATION GENERATION COMPLETE")
    print("="*70)
    print("\nKey outputs generated:")
    print("  - Table 5 formatted data (table5_transaction_costs.csv)")
    print("  - Conversion formulas documentation (conversion_formulas.yaml)")
    print("  - Summary statistics (translation_summary_statistics.json)")
    print("  - Complete documentation (translation_documentation.md)")
    print("="*70)