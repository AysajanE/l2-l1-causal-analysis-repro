#!/usr/bin/env python3
"""
Price Conversion Utilities for Ethereum Gas Costs
==================================================

This module provides reusable functions for converting between different
Ethereum units (Wei, Gwei, ETH) and USD values.

Conversion Formulas:
- 1 ETH = 10^18 Wei
- 1 Gwei = 10^9 Wei
- 1 ETH = 10^9 Gwei
- USD value = ETH value * ETH/USD price

Author: Data Engineering Lead
Date: 2025-01-10
"""

from typing import Union, Optional, Dict
import numpy as np
import pandas as pd
from decimal import Decimal, getcontext

# Set high precision for financial calculations
getcontext().prec = 50


class EthereumUnitConverter:
    """Converter for Ethereum units and USD values."""

    # Conversion constants
    WEI_PER_GWEI = 10**9
    WEI_PER_ETH = 10**18
    GWEI_PER_ETH = 10**9

    def __init__(self):
        """Initialize the converter."""
        self.conversions_logged = []

    @staticmethod
    def wei_to_gwei(wei: Union[float, int, np.ndarray, pd.Series]) -> Union[float, np.ndarray, pd.Series]:
        """
        Convert Wei to Gwei.

        Parameters
        ----------
        wei : Union[float, int, np.ndarray, pd.Series]
            Value in Wei

        Returns
        -------
        Union[float, np.ndarray, pd.Series]
            Value in Gwei
        """
        return wei / EthereumUnitConverter.WEI_PER_GWEI

    @staticmethod
    def gwei_to_wei(gwei: Union[float, int, np.ndarray, pd.Series]) -> Union[float, np.ndarray, pd.Series]:
        """
        Convert Gwei to Wei.

        Parameters
        ----------
        gwei : Union[float, int, np.ndarray, pd.Series]
            Value in Gwei

        Returns
        -------
        Union[float, np.ndarray, pd.Series]
            Value in Wei
        """
        return gwei * EthereumUnitConverter.WEI_PER_GWEI

    @staticmethod
    def wei_to_eth(wei: Union[float, int, np.ndarray, pd.Series]) -> Union[float, np.ndarray, pd.Series]:
        """
        Convert Wei to ETH.

        Parameters
        ----------
        wei : Union[float, int, np.ndarray, pd.Series]
            Value in Wei

        Returns
        -------
        Union[float, np.ndarray, pd.Series]
            Value in ETH
        """
        return wei / EthereumUnitConverter.WEI_PER_ETH

    @staticmethod
    def eth_to_wei(eth: Union[float, int, np.ndarray, pd.Series]) -> Union[float, np.ndarray, pd.Series]:
        """
        Convert ETH to Wei.

        Parameters
        ----------
        eth : Union[float, int, np.ndarray, pd.Series]
            Value in ETH

        Returns
        -------
        Union[float, np.ndarray, pd.Series]
            Value in Wei
        """
        return eth * EthereumUnitConverter.WEI_PER_ETH

    @staticmethod
    def gwei_to_eth(gwei: Union[float, int, np.ndarray, pd.Series]) -> Union[float, np.ndarray, pd.Series]:
        """
        Convert Gwei to ETH.

        Parameters
        ----------
        gwei : Union[float, int, np.ndarray, pd.Series]
            Value in Gwei

        Returns
        -------
        Union[float, np.ndarray, pd.Series]
            Value in ETH
        """
        return gwei / EthereumUnitConverter.GWEI_PER_ETH

    @staticmethod
    def eth_to_gwei(eth: Union[float, int, np.ndarray, pd.Series]) -> Union[float, np.ndarray, pd.Series]:
        """
        Convert ETH to Gwei.

        Parameters
        ----------
        eth : Union[float, int, np.ndarray, pd.Series]
            Value in ETH

        Returns
        -------
        Union[float, np.ndarray, pd.Series]
            Value in Gwei
        """
        return eth * EthereumUnitConverter.GWEI_PER_ETH

    @staticmethod
    def eth_to_usd(
        eth: Union[float, int, np.ndarray, pd.Series],
        eth_price_usd: Union[float, int, np.ndarray, pd.Series]
    ) -> Union[float, np.ndarray, pd.Series]:
        """
        Convert ETH to USD.

        Parameters
        ----------
        eth : Union[float, int, np.ndarray, pd.Series]
            Value in ETH
        eth_price_usd : Union[float, int, np.ndarray, pd.Series]
            ETH price in USD

        Returns
        -------
        Union[float, np.ndarray, pd.Series]
            Value in USD
        """
        return eth * eth_price_usd

    @staticmethod
    def usd_to_eth(
        usd: Union[float, int, np.ndarray, pd.Series],
        eth_price_usd: Union[float, int, np.ndarray, pd.Series]
    ) -> Union[float, np.ndarray, pd.Series]:
        """
        Convert USD to ETH.

        Parameters
        ----------
        usd : Union[float, int, np.ndarray, pd.Series]
            Value in USD
        eth_price_usd : Union[float, int, np.ndarray, pd.Series]
            ETH price in USD

        Returns
        -------
        Union[float, np.ndarray, pd.Series]
            Value in ETH
        """
        return usd / eth_price_usd

    @staticmethod
    def wei_to_usd(
        wei: Union[float, int, np.ndarray, pd.Series],
        eth_price_usd: Union[float, int, np.ndarray, pd.Series]
    ) -> Union[float, np.ndarray, pd.Series]:
        """
        Convert Wei directly to USD.

        Parameters
        ----------
        wei : Union[float, int, np.ndarray, pd.Series]
            Value in Wei
        eth_price_usd : Union[float, int, np.ndarray, pd.Series]
            ETH price in USD

        Returns
        -------
        Union[float, np.ndarray, pd.Series]
            Value in USD
        """
        eth = EthereumUnitConverter.wei_to_eth(wei)
        return EthereumUnitConverter.eth_to_usd(eth, eth_price_usd)

    @staticmethod
    def gwei_to_usd(
        gwei: Union[float, int, np.ndarray, pd.Series],
        eth_price_usd: Union[float, int, np.ndarray, pd.Series]
    ) -> Union[float, np.ndarray, pd.Series]:
        """
        Convert Gwei directly to USD.

        Parameters
        ----------
        gwei : Union[float, int, np.ndarray, pd.Series]
            Value in Gwei
        eth_price_usd : Union[float, int, np.ndarray, pd.Series]
            ETH price in USD

        Returns
        -------
        Union[float, np.ndarray, pd.Series]
            Value in USD
        """
        eth = EthereumUnitConverter.gwei_to_eth(gwei)
        return EthereumUnitConverter.eth_to_usd(eth, eth_price_usd)

    @staticmethod
    def calculate_transaction_cost_wei(
        base_fee_wei: Union[float, int],
        gas_used: Union[float, int],
        priority_fee_wei: Optional[Union[float, int]] = None
    ) -> float:
        """
        Calculate transaction cost in Wei.

        Parameters
        ----------
        base_fee_wei : Union[float, int]
            Base fee per gas in Wei
        gas_used : Union[float, int]
            Gas units used
        priority_fee_wei : Optional[Union[float, int]], default=None
            Priority fee per gas in Wei

        Returns
        -------
        float
            Total transaction cost in Wei
        """
        total_fee_wei = base_fee_wei
        if priority_fee_wei is not None:
            total_fee_wei += priority_fee_wei

        return total_fee_wei * gas_used

    @staticmethod
    def calculate_transaction_cost_usd(
        base_fee_wei: Union[float, int, np.ndarray, pd.Series],
        gas_used: Union[float, int, np.ndarray, pd.Series],
        eth_price_usd: Union[float, int, np.ndarray, pd.Series],
        priority_fee_wei: Optional[Union[float, int, np.ndarray, pd.Series]] = None
    ) -> Union[float, np.ndarray, pd.Series]:
        """
        Calculate transaction cost in USD.

        Parameters
        ----------
        base_fee_wei : Union[float, int, np.ndarray, pd.Series]
            Base fee per gas in Wei
        gas_used : Union[float, int, np.ndarray, pd.Series]
            Gas units used
        eth_price_usd : Union[float, int, np.ndarray, pd.Series]
            ETH price in USD
        priority_fee_wei : Optional[Union[float, int, np.ndarray, pd.Series]], default=None
            Priority fee per gas in Wei

        Returns
        -------
        Union[float, np.ndarray, pd.Series]
            Total transaction cost in USD
        """
        cost_wei = EthereumUnitConverter.calculate_transaction_cost_wei(
            base_fee_wei, gas_used, priority_fee_wei
        )
        return EthereumUnitConverter.wei_to_usd(cost_wei, eth_price_usd)

    def create_conversion_table(
        self,
        base_fee_gwei: float,
        gas_used: int,
        eth_prices_usd: Dict[str, float]
    ) -> pd.DataFrame:
        """
        Create a conversion table for a specific transaction.

        Parameters
        ----------
        base_fee_gwei : float
            Base fee in Gwei
        gas_used : int
            Gas units used
        eth_prices_usd : Dict[str, float]
            Dictionary of ETH prices (e.g., {'spot': 3000, 'lower_95': 2850, 'upper_95': 3150})

        Returns
        -------
        pd.DataFrame
            Conversion table with different units and price scenarios
        """
        base_fee_wei = self.gwei_to_wei(base_fee_gwei)
        cost_wei = self.calculate_transaction_cost_wei(base_fee_wei, gas_used)
        cost_gwei = self.wei_to_gwei(cost_wei)
        cost_eth = self.wei_to_eth(cost_wei)

        rows = []
        for price_type, eth_price in eth_prices_usd.items():
            cost_usd = self.eth_to_usd(cost_eth, eth_price)
            rows.append({
                'price_scenario': price_type,
                'eth_price_usd': eth_price,
                'base_fee_gwei': base_fee_gwei,
                'gas_used': gas_used,
                'cost_wei': cost_wei,
                'cost_gwei': cost_gwei,
                'cost_eth': cost_eth,
                'cost_usd': cost_usd
            })

        return pd.DataFrame(rows)


# Convenience functions for direct use
converter = EthereumUnitConverter()

# Export the most commonly used functions
wei_to_gwei = converter.wei_to_gwei
gwei_to_wei = converter.gwei_to_wei
wei_to_eth = converter.wei_to_eth
eth_to_wei = converter.eth_to_wei
gwei_to_eth = converter.gwei_to_eth
eth_to_gwei = converter.eth_to_gwei
eth_to_usd = converter.eth_to_usd
usd_to_eth = converter.usd_to_eth
wei_to_usd = converter.wei_to_usd
gwei_to_usd = converter.gwei_to_usd
calculate_transaction_cost_wei = converter.calculate_transaction_cost_wei
calculate_transaction_cost_usd = converter.calculate_transaction_cost_usd


def validate_conversions():
    """Run validation tests for all conversion functions."""

    print("Running conversion validation tests...")
    print("=" * 60)

    # Test Wei <-> Gwei
    wei_val = 1_000_000_000
    gwei_val = wei_to_gwei(wei_val)
    assert gwei_val == 1.0, f"Wei to Gwei failed: {gwei_val}"
    assert gwei_to_wei(gwei_val) == wei_val, "Gwei to Wei failed"
    print("✓ Wei <-> Gwei conversions validated")

    # Test Wei <-> ETH
    wei_val = 1_000_000_000_000_000_000
    eth_val = wei_to_eth(wei_val)
    assert eth_val == 1.0, f"Wei to ETH failed: {eth_val}"
    assert eth_to_wei(eth_val) == wei_val, "ETH to Wei failed"
    print("✓ Wei <-> ETH conversions validated")

    # Test Gwei <-> ETH
    gwei_val = 1_000_000_000
    eth_val = gwei_to_eth(gwei_val)
    assert eth_val == 1.0, f"Gwei to ETH failed: {eth_val}"
    assert eth_to_gwei(eth_val) == gwei_val, "ETH to Gwei failed"
    print("✓ Gwei <-> ETH conversions validated")

    # Test USD conversions
    eth_val = 1.0
    eth_price = 3000.0
    usd_val = eth_to_usd(eth_val, eth_price)
    assert usd_val == 3000.0, f"ETH to USD failed: {usd_val}"
    assert usd_to_eth(usd_val, eth_price) == eth_val, "USD to ETH failed"
    print("✓ ETH <-> USD conversions validated")

    # Test transaction cost calculation
    base_fee_gwei = 50.0
    gas_used = 21_000
    eth_price = 3000.0

    base_fee_wei = gwei_to_wei(base_fee_gwei)
    cost_wei = calculate_transaction_cost_wei(base_fee_wei, gas_used)
    cost_usd = calculate_transaction_cost_usd(base_fee_wei, gas_used, eth_price)

    expected_cost_wei = base_fee_wei * gas_used
    expected_cost_eth = wei_to_eth(expected_cost_wei)
    expected_cost_usd = expected_cost_eth * eth_price

    assert cost_wei == expected_cost_wei, f"Transaction cost in Wei failed: {cost_wei}"
    assert abs(cost_usd - expected_cost_usd) < 0.01, f"Transaction cost in USD failed: {cost_usd}"
    print(f"✓ Transaction cost calculations validated")
    print(f"  Example: {base_fee_gwei} Gwei base fee, {gas_used:,} gas = ${cost_usd:.2f}")

    # Test array/Series operations
    import numpy as np
    wei_array = np.array([1e18, 2e18, 3e18])
    eth_array = wei_to_eth(wei_array)
    assert np.allclose(eth_array, [1.0, 2.0, 3.0]), "Array conversion failed"
    print("✓ Array/Series conversions validated")

    print("=" * 60)
    print("All conversion tests passed successfully!")


if __name__ == "__main__":
    # Run validation tests
    validate_conversions()

    print("\n" + "=" * 60)
    print("EXAMPLE CONVERSION TABLE")
    print("=" * 60)

    # Create example conversion table
    example_base_fee = 50.0  # Gwei
    example_gas = 21_000  # Standard ETH transfer
    example_prices = {
        'spot': 3000.0,
        'lower_95': 2850.0,
        'upper_95': 3150.0
    }

    table = converter.create_conversion_table(
        example_base_fee,
        example_gas,
        example_prices
    )

    print(f"\nTransaction: {example_base_fee} Gwei base fee, {example_gas:,} gas used")
    print("\n" + table.to_string(index=False))
    print("=" * 60)