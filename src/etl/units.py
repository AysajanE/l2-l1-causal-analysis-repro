#!/usr/bin/env python3
"""
Ethereum Units Conversion Module
=================================

Centralized unit conversions for Ethereum gas fees and prices.
Ensures consistent conversions across the entire pipeline.

Critical conversions:
- Wei <-> Gwei <-> ETH
- Gas-weighted fee calculations
- USD conversions with proper precision

Author: BSTS-to-Dollar Pipeline Specialist
Date: 2025-10-18
"""

import numpy as np
import pandas as pd
from typing import Union, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for unit conversions
WEI_PER_GWEI = 1e9
GWEI_PER_ETH = 1e9
WEI_PER_ETH = 1e18

# Standard gas amounts for reference transactions
STANDARD_TX_GAS = 21_000  # Standard ETH transfer
ERC20_TX_GAS = 65_000     # ERC20 token transfer
COMPLEX_TX_GAS = 300_000  # Complex smart contract interaction
UNISWAP_SWAP_GAS = 150_000  # Typical Uniswap V2/V3 swap


class EthereumUnits:
    """Centralized Ethereum unit conversions with validation."""

    @staticmethod
    def wei_to_gwei(wei: Union[float, np.ndarray, pd.Series]) -> Union[float, np.ndarray, pd.Series]:
        """Convert Wei to Gwei."""
        return wei / WEI_PER_GWEI

    @staticmethod
    def gwei_to_wei(gwei: Union[float, np.ndarray, pd.Series]) -> Union[float, np.ndarray, pd.Series]:
        """Convert Gwei to Wei."""
        return gwei * WEI_PER_GWEI

    @staticmethod
    def gwei_to_eth(gwei: Union[float, np.ndarray, pd.Series]) -> Union[float, np.ndarray, pd.Series]:
        """Convert Gwei to ETH."""
        return gwei / GWEI_PER_ETH

    @staticmethod
    def eth_to_gwei(eth: Union[float, np.ndarray, pd.Series]) -> Union[float, np.ndarray, pd.Series]:
        """Convert ETH to Gwei."""
        return eth * GWEI_PER_ETH

    @staticmethod
    def wei_to_eth(wei: Union[float, np.ndarray, pd.Series]) -> Union[float, np.ndarray, pd.Series]:
        """Convert Wei to ETH."""
        return wei / WEI_PER_ETH

    @staticmethod
    def eth_to_wei(eth: Union[float, np.ndarray, pd.Series]) -> Union[float, np.ndarray, pd.Series]:
        """Convert ETH to Wei."""
        return eth * WEI_PER_ETH

    @staticmethod
    def calculate_gas_cost_eth(
        gas_used: Union[float, np.ndarray, pd.Series],
        base_fee_gwei: Union[float, np.ndarray, pd.Series],
        priority_fee_gwei: Optional[Union[float, np.ndarray, pd.Series]] = None
    ) -> Union[float, np.ndarray, pd.Series]:
        """
        Calculate gas cost in ETH.

        Args:
            gas_used: Amount of gas used
            base_fee_gwei: Base fee in Gwei per gas
            priority_fee_gwei: Priority fee in Gwei per gas (optional)

        Returns:
            Cost in ETH
        """
        total_fee_gwei = base_fee_gwei
        if priority_fee_gwei is not None:
            total_fee_gwei = base_fee_gwei + priority_fee_gwei

        cost_gwei = gas_used * total_fee_gwei
        return EthereumUnits.gwei_to_eth(cost_gwei)

    @staticmethod
    def calculate_gas_cost_usd(
        gas_used: Union[float, np.ndarray, pd.Series],
        base_fee_gwei: Union[float, np.ndarray, pd.Series],
        eth_price_usd: Union[float, np.ndarray, pd.Series],
        priority_fee_gwei: Optional[Union[float, np.ndarray, pd.Series]] = None
    ) -> Union[float, np.ndarray, pd.Series]:
        """
        Calculate gas cost in USD.

        Formula:
        Cost_USD = gas_used * (base_fee + priority_fee)[Gwei/gas] * (1e-9 ETH/Gwei) * eth_price[USD/ETH]

        Args:
            gas_used: Amount of gas used
            base_fee_gwei: Base fee in Gwei per gas
            eth_price_usd: ETH price in USD
            priority_fee_gwei: Priority fee in Gwei per gas (optional)

        Returns:
            Cost in USD
        """
        cost_eth = EthereumUnits.calculate_gas_cost_eth(gas_used, base_fee_gwei, priority_fee_gwei)
        return cost_eth * eth_price_usd

    @staticmethod
    def compute_gas_weighted_fee(
        fees: Union[np.ndarray, pd.Series],
        gas_weights: Union[np.ndarray, pd.Series]
    ) -> float:
        """
        Compute gas-weighted average fee.

        Formula: weighted_fee = sum(fee_i * gas_i) / sum(gas_i)

        Args:
            fees: Fee values (e.g., base_fee_gwei per block)
            gas_weights: Gas used per block

        Returns:
            Gas-weighted average fee
        """
        # Handle any NaN values
        mask = ~(np.isnan(fees) | np.isnan(gas_weights))
        if not mask.any():
            return np.nan

        fees_clean = fees[mask] if isinstance(fees, (pd.Series, np.ndarray)) else fees
        gas_clean = gas_weights[mask] if isinstance(gas_weights, (pd.Series, np.ndarray)) else gas_weights

        total_weighted = np.sum(fees_clean * gas_clean)
        total_gas = np.sum(gas_clean)

        if total_gas == 0:
            return np.nan

        return total_weighted / total_gas

    @staticmethod
    def calculate_welfare_delta_usd(
        base_fee_counterfactual_gwei: Union[float, np.ndarray, pd.Series],
        base_fee_observed_gwei: Union[float, np.ndarray, pd.Series],
        total_gas_used: Union[float, np.ndarray, pd.Series],
        eth_price_usd: Union[float, np.ndarray, pd.Series],
        include_tip: bool = False,
        tip_counterfactual_gwei: Optional[Union[float, np.ndarray, pd.Series]] = None,
        tip_observed_gwei: Optional[Union[float, np.ndarray, pd.Series]] = None
    ) -> Union[float, np.ndarray, pd.Series]:
        """
        Calculate welfare delta in USD.

        Primary formula (base-only):
        Delta_base$_t = (BF_cf_t - BF_obs_t)[Gwei/gas] * GAS_t[gas] * (1e-9 ETH/Gwei) * P_t[USD/ETH]

        Sensitivity formula (base+tip):
        Delta_base+tip$_t = ((BF_cf_t + TIP_cf_t) - (BF_obs_t + TIP_obs_t)) * GAS_t * (1e-9) * P_t

        Args:
            base_fee_counterfactual_gwei: Counterfactual base fee (Gwei per gas)
            base_fee_observed_gwei: Observed base fee (Gwei per gas)
            total_gas_used: Total gas used
            eth_price_usd: ETH price in USD
            include_tip: Whether to include priority fees
            tip_counterfactual_gwei: Counterfactual priority fee (optional)
            tip_observed_gwei: Observed priority fee (optional)

        Returns:
            Welfare delta in USD (positive = user savings)
        """
        # Calculate fee difference in Gwei per gas
        fee_diff_gwei = base_fee_counterfactual_gwei - base_fee_observed_gwei

        if include_tip and tip_counterfactual_gwei is not None and tip_observed_gwei is not None:
            tip_diff_gwei = tip_counterfactual_gwei - tip_observed_gwei
            fee_diff_gwei = fee_diff_gwei + tip_diff_gwei

        # Convert to ETH
        fee_diff_eth = EthereumUnits.gwei_to_eth(fee_diff_gwei)

        # Calculate total delta in ETH
        delta_eth = fee_diff_eth * total_gas_used

        # Convert to USD
        delta_usd = delta_eth * eth_price_usd

        return delta_usd

    @staticmethod
    def validate_fee_bounds(
        fee_gwei: Union[float, np.ndarray, pd.Series],
        percentile_cap: float = 99.5,
        historical_fees: Optional[Union[np.ndarray, pd.Series]] = None
    ) -> tuple:
        """
        Validate and cap extreme fee values.

        Args:
            fee_gwei: Fee values to validate
            percentile_cap: Percentile for capping (default 99.5)
            historical_fees: Historical fees for computing cap threshold

        Returns:
            Tuple of (capped_fees, is_capped_mask)
        """
        if historical_fees is not None:
            cap_value = np.percentile(historical_fees, percentile_cap)
        else:
            # Use a reasonable maximum if no historical data
            cap_value = 10000  # 10,000 Gwei as emergency cap
            logger.warning(f"No historical fees provided, using default cap of {cap_value} Gwei")

        is_capped = fee_gwei > cap_value
        capped_fees = np.minimum(fee_gwei, cap_value)

        if np.any(is_capped):
            n_capped = np.sum(is_capped) if isinstance(is_capped, np.ndarray) else int(is_capped)
            logger.warning(f"Capped {n_capped} fee values exceeding {cap_value:.2f} Gwei")

        return capped_fees, is_capped

    @staticmethod
    def compute_transaction_bounds(
        base_fee_gwei: Union[float, np.ndarray, pd.Series],
        eth_price_usd: Union[float, np.ndarray, pd.Series],
        priority_fee_gwei: Optional[Union[float, np.ndarray, pd.Series]] = None
    ) -> dict:
        """
        Compute transaction cost bounds for standard transaction types.

        Args:
            base_fee_gwei: Base fee in Gwei per gas
            eth_price_usd: ETH price in USD
            priority_fee_gwei: Priority fee in Gwei per gas (optional)

        Returns:
            Dictionary with cost bounds for different transaction types
        """
        bounds = {}

        # Standard ETH transfer (21k gas)
        bounds['standard_tx_usd'] = EthereumUnits.calculate_gas_cost_usd(
            STANDARD_TX_GAS, base_fee_gwei, eth_price_usd, priority_fee_gwei
        )

        # ERC20 transfer (65k gas)
        bounds['erc20_tx_usd'] = EthereumUnits.calculate_gas_cost_usd(
            ERC20_TX_GAS, base_fee_gwei, eth_price_usd, priority_fee_gwei
        )

        # Complex contract interaction (300k gas)
        bounds['complex_tx_usd'] = EthereumUnits.calculate_gas_cost_usd(
            COMPLEX_TX_GAS, base_fee_gwei, eth_price_usd, priority_fee_gwei
        )

        # Uniswap swap (150k gas)
        bounds['uniswap_swap_usd'] = EthereumUnits.calculate_gas_cost_usd(
            UNISWAP_SWAP_GAS, base_fee_gwei, eth_price_usd, priority_fee_gwei
        )

        return bounds


def test_conversions():
    """Test unit conversions for correctness."""
    units = EthereumUnits()

    # Test basic conversions
    assert abs(units.wei_to_gwei(1e9) - 1.0) < 1e-10, "Wei to Gwei conversion failed"
    assert abs(units.gwei_to_eth(1e9) - 1.0) < 1e-10, "Gwei to ETH conversion failed"
    assert abs(units.wei_to_eth(1e18) - 1.0) < 1e-10, "Wei to ETH conversion failed"

    # Test gas cost calculation
    gas_used = 21_000
    base_fee_gwei = 30
    priority_fee_gwei = 2
    eth_price_usd = 2000

    cost_eth = units.calculate_gas_cost_eth(gas_used, base_fee_gwei, priority_fee_gwei)
    expected_eth = 21_000 * 32 / 1e9  # 0.000672 ETH
    assert abs(cost_eth - expected_eth) < 1e-10, f"ETH cost calculation failed: {cost_eth} vs {expected_eth}"

    cost_usd = units.calculate_gas_cost_usd(gas_used, base_fee_gwei, eth_price_usd, priority_fee_gwei)
    expected_usd = expected_eth * 2000  # $1.344
    assert abs(cost_usd - expected_usd) < 1e-6, f"USD cost calculation failed: {cost_usd} vs {expected_usd}"

    # Test gas-weighted average
    fees = np.array([10, 20, 30])
    gas_weights = np.array([1000, 2000, 3000])
    weighted_avg = units.compute_gas_weighted_fee(fees, gas_weights)
    expected_avg = (10*1000 + 20*2000 + 30*3000) / 6000  # 23.33...
    assert abs(weighted_avg - expected_avg) < 1e-10, f"Gas-weighted average failed: {weighted_avg} vs {expected_avg}"

    logger.info("All unit conversion tests passed!")


if __name__ == "__main__":
    test_conversions()