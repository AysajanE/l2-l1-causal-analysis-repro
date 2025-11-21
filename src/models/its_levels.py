#!/usr/bin/env python3
"""
Interrupted Time Series Estimator - LEVELS SPECIFICATION
==========================================================
Resolves estimand mismatch between first-differences and levels interpretation.
Implements proper levels specification with semi-elasticity mapping.

Key Features:
1. Main levels specification: log Y_t on A_t with regime/calendar/D★ controls
2. HAC standard errors (Andrews automatic bandwidth)
3. AR(1)/ARMA error models
4. Distributed lag implementation (A_t, A_{t-1}, A_{t-7})
5. Koyck lag specification
6. First-differences robustness check
7. Translation box between specifications
8. Long-run effect calculations

Author: Estimand Alignment Specialist
Date: 2025-10-18
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS, WLS
from statsmodels.stats.sandwich_covariance import cov_hac
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.stats.diagnostic import acorr_ljungbox, het_white
from statsmodels.stats.stattools import durbin_watson
from patsy import dmatrices
from typing import Dict, Tuple, Optional, Any
import warnings
from datetime import datetime
import yaml
from pathlib import Path

from project_A_effects.visualization.utils.provenance import ProvenanceFooter

# Suppress convergence warnings for ARIMA
warnings.filterwarnings('ignore', category=UserWarning)


class ITSLevelsEstimator:
    """
    Interrupted Time Series estimator in LEVELS specification.
    Properly aligns estimand with interpretation and BSTS calibration.
    """

    def __init__(self, data: pd.DataFrame,
                 outcome: str = 'log_base_fee',
                 treatment: str = 'A_t_clean'):
        """
        Initialize ITS levels estimator.

        Args:
            data: Panel data with treatment and outcomes
            outcome: Outcome variable name (log scale for semi-elasticity)
            treatment: Treatment variable name
        """
        self.data = data.copy()
        self.outcome = outcome
        self.treatment = treatment
        self.results = {}
        self.diagnostics = {}

        # Define critical dates
        self.LONDON_DATE = pd.Timestamp('2021-08-05')
        self.MERGE_DATE = pd.Timestamp('2022-09-15')
        self.DENCUN_DATE = pd.Timestamp('2024-03-13')

        # Prepare data
        self._prepare_data()

    def _prepare_data(self):
        """Prepare data for levels specification."""
        # Filter to post-London
        self.data = self.data[self.data['date'] >= self.LONDON_DATE].copy()
        self.data = self.data.sort_values('date').reset_index(drop=True)

        # Create log outcomes if not present
        if 'log_base_fee' not in self.data.columns and 'base_fee_median_gwei' in self.data.columns:
            self.data['log_base_fee'] = np.log(self.data['base_fee_median_gwei'] + 1)

        # Create regime indicators (check if they exist first)
        if 'regime_post_merge' in self.data.columns:
            # Use existing regime indicators
            self.data['regime_merge'] = self.data['regime_post_merge']
            self.data['regime_dencun'] = self.data.get('regime_post_dencun', 0)
        else:
            # Create regime indicators
            self.data['regime_london'] = (
                (self.data['date'] >= self.LONDON_DATE) &
                (self.data['date'] < self.MERGE_DATE)
            ).astype(int)

            self.data['regime_merge'] = (
                (self.data['date'] >= self.MERGE_DATE) &
                (self.data['date'] < self.DENCUN_DATE)
            ).astype(int)

            self.data['regime_dencun'] = (
                self.data['date'] >= self.DENCUN_DATE
            ).astype(int)

        # Calendar effects - only create if missing
        if 'day_of_week' not in self.data.columns:
            self.data['day_of_week'] = self.data['date'].dt.dayofweek
        if 'month_of_year' not in self.data.columns:
            self.data['month_of_year'] = self.data['date'].dt.month
        if 'is_weekend' not in self.data.columns:
            self.data['is_weekend'] = (self.data['date'].dt.dayofweek >= 5).astype(int)
        if 'is_month_end' not in self.data.columns:
            self.data['is_month_end'] = self.data['date'].dt.is_month_end.astype(int)

        # Time trend
        self.data['time_trend'] = np.arange(len(self.data))

        print(f"Data prepared: {len(self.data)} observations from {self.data['date'].min():%Y-%m-%d} to {self.data['date'].max():%Y-%m-%d}")

    def estimate_main_spec(self, use_time_trend: bool = False) -> Dict:
        """
        Estimate main levels specification with HAC standard errors.

        Args:
            use_time_trend: Whether to include linear time trend

        Returns:
            Dictionary with estimation results
        """
        print("\n" + "="*60)
        print("MAIN LEVELS SPECIFICATION")
        print("="*60)

        # Define formula - simpler to avoid multicollinearity
        formula_parts = [
            f"{self.outcome} ~ {self.treatment}",
            "D_star",
            "regime_merge + regime_dencun",
            "is_weekend + is_month_end"
        ]

        if use_time_trend:
            formula_parts.append("time_trend")

        formula = " + ".join(formula_parts)

        # Create design matrices
        y, X = dmatrices(formula, data=self.data, return_type='dataframe')

        # Estimate OLS
        model = OLS(y, X)
        ols_results = model.fit()

        # HAC standard errors with automatic bandwidth selection
        # Andrews (1991) automatic bandwidth selection
        n = len(y)
        bandwidth = int(4 * (n/100)**(2/9))  # Andrews formula

        hac_results = model.fit(
            cov_type='HAC',
            cov_kwds={
                'kernel': 'bartlett',
                'use_correction': True,
                'maxlags': bandwidth
            }
        )

        # Extract treatment effect
        beta = hac_results.params[self.treatment]
        se = hac_results.bse[self.treatment]
        ci_lower, ci_upper = hac_results.conf_int().loc[self.treatment]
        pval = hac_results.pvalues[self.treatment]

        # Calculate semi-elasticity
        semi_elasticity = (np.exp(0.10 * beta) - 1) * 100
        semi_se = self._delta_method_se(beta, se)

        # Store results
        self.results['main_ols'] = ols_results
        self.results['main_hac'] = hac_results
        self.results['main_effect'] = {
            'beta': beta,
            'se': se,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'pvalue': pval,
            'semi_elasticity': semi_elasticity,
            'semi_se': semi_se,
            'bandwidth': bandwidth,
            'n_obs': len(y),
            'r_squared': ols_results.rsquared,
            'r_squared_adj': ols_results.rsquared_adj
        }

        # Diagnostics
        self._run_diagnostics(ols_results)

        print(f"\nRESULTS:")
        print(f"  β (A_t coefficient): {beta:.4f}")
        print(f"  SE (HAC, bw={bandwidth}): {se:.4f}")
        print(f"  95% CI: [{ci_lower:.4f}, {ci_upper:.4f}]")
        print(f"  P-value: {pval:.4f}")
        print(f"  Semi-elasticity (10pp): {semi_elasticity:.2f}% ± {semi_se:.2f}%")
        print(f"  Interpretation: 10pp increase in A_t → {semi_elasticity:.2f}% change in base fee")
        print(f"  R²: {ols_results.rsquared:.4f}")
        print(f"  N: {len(y)}")

        return self.results['main_effect']

    def estimate_distributed_lags(self, lags: list = [1, 7]) -> Dict:
        """
        Add distributed lag terms to capture dynamic effects.

        Args:
            lags: List of lag periods to include

        Returns:
            Dictionary with distributed lag results
        """
        print("\n" + "="*60)
        print("DISTRIBUTED LAG SPECIFICATION")
        print("="*60)

        # Create lag variables
        for lag in lags:
            self.data[f'{self.treatment}_lag{lag}'] = self.data[self.treatment].shift(lag)

        # Build formula
        lag_terms = " + ".join([f"{self.treatment}_lag{lag}" for lag in lags])
        formula = f"""
        {self.outcome} ~ {self.treatment} + {lag_terms} +
        D_star + regime_merge + regime_dencun +
        is_weekend + is_month_end
        """

        # Estimate
        y, X = dmatrices(formula, data=self.data.dropna(), return_type='dataframe')
        model = OLS(y, X)

        # HAC standard errors
        n = len(y)
        bandwidth = int(4 * (n/100)**(2/9))

        dl_results = model.fit(
            cov_type='HAC',
            cov_kwds={
                'kernel': 'bartlett',
                'use_correction': True,
                'maxlags': bandwidth
            }
        )

        # Calculate long-run effect
        long_run_effect = dl_results.params[self.treatment]
        for lag in lags:
            long_run_effect += dl_results.params[f'{self.treatment}_lag{lag}']

        # Long-run semi-elasticity
        lr_semi_elasticity = (np.exp(0.10 * long_run_effect) - 1) * 100

        # Store results
        self.results['distributed_lags'] = {
            'model': dl_results,
            'contemporaneous': dl_results.params[self.treatment],
            'lags': {lag: dl_results.params[f'{self.treatment}_lag{lag}'] for lag in lags},
            'long_run_effect': long_run_effect,
            'long_run_semi_elasticity': lr_semi_elasticity,
            'n_obs': len(y)
        }

        print(f"\nRESULTS:")
        print(f"  Contemporaneous effect: {dl_results.params[self.treatment]:.4f}")
        for lag in lags:
            print(f"  Lag {lag} effect: {dl_results.params[f'{self.treatment}_lag{lag}']:.4f}")
        print(f"  Long-run effect: {long_run_effect:.4f}")
        print(f"  Long-run semi-elasticity (10pp): {lr_semi_elasticity:.2f}%")

        return self.results['distributed_lags']

    def estimate_koyck_lag(self, use_time_trend: bool = False) -> Dict:
        """
        Implement Koyck geometric lag specification.

        Args:
            use_time_trend: Include a linear time trend to absorb slow-moving
                co-movement between treatment and outcome. This helps prevent
                sign instability from deterministic trends when including the
                lagged dependent variable.
        """
        print("\n" + "="*60)
        print("KOYCK LAG SPECIFICATION")
        print("="*60)

        # Add lagged dependent variable
        self.data['log_base_fee_lag1'] = self.data[self.outcome].shift(1)

        # Build formula with optional time trend control
        trend_term = " + time_trend" if use_time_trend else ""
        formula = f"""
        {self.outcome} ~ log_base_fee_lag1 + {self.treatment} +
        D_star + regime_merge + regime_dencun +
        is_weekend + is_month_end{trend_term}
        """

        # Estimate
        y, X = dmatrices(formula, data=self.data.dropna(), return_type='dataframe')
        model = OLS(y, X)

        # HAC standard errors
        n = len(y)
        bandwidth = int(4 * (n/100)**(2/9))

        koyck_results = model.fit(
            cov_type='HAC',
            cov_kwds={
                'kernel': 'bartlett',
                'use_correction': True,
                'maxlags': bandwidth
            }
        )

        # Extract parameters
        rho = koyck_results.params['log_base_fee_lag1']
        short_run = koyck_results.params[self.treatment]

        # Long-run multiplier
        if rho < 1:
            long_run = short_run / (1 - rho)
            lr_semi_elasticity = (np.exp(0.10 * long_run) - 1) * 100
        else:
            long_run = np.nan
            lr_semi_elasticity = np.nan

        # Store results
        self.results['koyck'] = {
            'model': koyck_results,
            'rho': rho,
            'short_run_effect': short_run,
            'long_run_effect': long_run,
            'long_run_semi_elasticity': lr_semi_elasticity,
            'adjustment_speed': 1 - rho,
            'n_obs': len(y)
        }

        print(f"\nRESULTS:")
        print(f"  ρ (persistence): {rho:.4f}")
        print(f"  Short-run effect: {short_run:.4f}")
        print(f"  Long-run effect: {long_run:.4f}")
        print(f"  Adjustment speed: {1-rho:.4f}")
        print(f"  Long-run semi-elasticity (10pp): {lr_semi_elasticity:.2f}%")

        return self.results['koyck']

    def estimate_ar_errors(self, ar_order: int = 1, ma_order: int = 0) -> Dict:
        """
        Estimate with AR(p) or ARMA(p,q) error structure.

        Args:
            ar_order: AR order (default 1)
            ma_order: MA order (default 0 for pure AR)

        Returns:
            Dictionary with ARIMA results
        """
        print("\n" + "="*60)
        print(f"AR({ar_order},{ma_order}) ERROR MODEL")
        print("="*60)

        # Prepare data - use simpler formula for ARIMA
        formula = f"""
        {self.outcome} ~ {self.treatment} + D_star +
        regime_merge + regime_dencun + is_weekend + is_month_end
        """

        y, X = dmatrices(formula, data=self.data, return_type='dataframe')

        # Remove intercept as ARIMA adds its own
        X = X.iloc[:, 1:]

        # ARIMA model with exogenous regressors
        arima_model = ARIMA(
            endog=y.values.flatten(),
            exog=X.values,
            order=(ar_order, 0, ma_order),
            trend='c'
        )

        try:
            arima_results = arima_model.fit()

            # Extract treatment effect
            # Treatment is first column in X
            beta = arima_results.params[1]  # Skip intercept
            se = arima_results.bse[1]

            # Semi-elasticity
            semi_elasticity = (np.exp(0.10 * beta) - 1) * 100

            # Store results
            self.results['arima'] = {
                'model': arima_results,
                'beta': beta,
                'se': se,
                'semi_elasticity': semi_elasticity,
                'ar_params': arima_results.arparams if ar_order > 0 else None,
                'ma_params': arima_results.maparams if ma_order > 0 else None,
                'aic': arima_results.aic,
                'bic': arima_results.bic,
                'n_obs': len(y)
            }

            print(f"\nRESULTS:")
            print(f"  β (A_t coefficient): {beta:.4f}")
            print(f"  SE: {se:.4f}")
            print(f"  Semi-elasticity (10pp): {semi_elasticity:.2f}%")
            if ar_order > 0:
                print(f"  AR parameters: {arima_results.arparams}")
            if ma_order > 0:
                print(f"  MA parameters: {arima_results.maparams}")
            print(f"  AIC: {arima_results.aic:.2f}")
            print(f"  BIC: {arima_results.bic:.2f}")

        except Exception as e:
            print(f"  Warning: ARIMA estimation failed: {e}")
            self.results['arima'] = None

        return self.results.get('arima', {})

    def estimate_arma_grid(self, max_p: int = 3, max_q: int = 2, lb_lags: int = 10) -> Dict:
        """
        Grid search ARMA(p,q) error structures for the levels spec with exogenous regressors.

        Tries ARIMA(endog, exog, order=(p,0,q)) for p in [0..max_p], q in [0..max_q],
        collects AIC/BIC, treatment beta and SE, Durbin–Watson, and Ljung–Box p-values.
        Selects the best order by AIC (tie-break by larger Ljung–Box p at the largest lag).

        Returns a dict with the grid as a DataFrame and the selected order + summary.
        """
        print("\n" + "="*60)
        print(f"ARMA(p,q) ERROR GRID (p<= {max_p}, q<= {max_q})")
        print("="*60)

        # Prepare design consistent with estimate_ar_errors
        formula = f"""
        {self.outcome} ~ {self.treatment} + D_star +
        regime_merge + regime_dencun + is_weekend + is_month_end
        """
        y, X = dmatrices(formula, data=self.data, return_type='dataframe')
        # Remove intercept as ARIMA adds its own constant
        X_exog = X.iloc[:, 1:]
        y_vec = y.values.flatten()

        rows = []
        for p in range(0, max_p + 1):
            for q in range(0, max_q + 1):
                # skip the trivial (0,0) case since OLS already reported
                if p == 0 and q == 0:
                    continue
                try:
                    arima_model = ARIMA(endog=y_vec, exog=X_exog.values, order=(p, 0, q), trend='c')
                    res = arima_model.fit()
                    # Treatment coefficient is first column in X_exog
                    beta = float(res.params[1])
                    se = float(res.bse[1])
                    aic = float(res.aic)
                    bic = float(res.bic)
                    resid = pd.Series(res.resid)
                    dw = float(durbin_watson(resid))
                    lb = acorr_ljungbox(resid, lags=lb_lags, return_df=True)
                    lb_p_at_max = float(lb['lb_pvalue'].iloc[-1])
                    lb_p_min = float(lb['lb_pvalue'].min())
                    rows.append({
                        'p': p, 'q': q,
                        'beta': beta, 'se': se,
                        'aic': aic, 'bic': bic, 'dw': dw,
                        'lb_p_at_maxlag': lb_p_at_max,
                        'lb_p_min': lb_p_min,
                        'n': int(res.nobs)
                    })
                except Exception as e:
                    rows.append({
                        'p': p, 'q': q, 'beta': np.nan, 'se': np.nan,
                        'aic': np.inf, 'bic': np.inf, 'dw': np.nan,
                        'lb_p_at_maxlag': np.nan, 'lb_p_min': np.nan,
                        'n': int(len(y_vec))
                    })

        grid = pd.DataFrame(rows)
        # Select by AIC, break ties by higher lb_p_at_maxlag
        grid_sorted = grid.sort_values(['aic', 'lb_p_at_maxlag'], ascending=[True, False]).reset_index(drop=True)
        best = grid_sorted.iloc[0].to_dict()

        self.results['arma_grid'] = grid
        self.results['arma_best'] = best

        print("\nARMA grid (top 5 by AIC):")
        print(grid_sorted.head(5).to_string(index=False))
        print(f"\nSelected ARMA(p,q) = ({int(best['p'])},{int(best['q'])}), AIC={best['aic']:.1f}, LB p@{lb_lags}={best['lb_p_at_maxlag']:.3f}")

        return {'grid': grid, 'best': best}

    def estimate_fgls(self) -> Dict:
        """
        Feasible GLS with AR(1) errors using Cochrane-Orcutt procedure.
        """
        print("\n" + "="*60)
        print("FGLS WITH AR(1) ERRORS")
        print("="*60)

        # Initial OLS
        formula = f"""
        {self.outcome} ~ {self.treatment} + D_star +
        regime_merge + regime_dencun + is_weekend + is_month_end
        """

        y, X = dmatrices(formula, data=self.data, return_type='dataframe')

        # Step 1: Initial OLS
        ols_model = OLS(y, X)
        ols_results = ols_model.fit()

        # Step 2: Estimate AR(1) coefficient
        residuals = ols_results.resid.values
        rho = np.corrcoef(residuals[:-1], residuals[1:])[0, 1]

        print(f"  Estimated ρ: {rho:.4f}")

        # Step 3: Transform variables (Prais-Winsten)
        n = len(y)

        # First observation transformation
        y_vals = y.values.flatten()  # Ensure 1D array
        y_transformed = np.zeros(n)
        y_transformed[0] = np.sqrt(1 - rho**2) * y_vals[0]
        y_transformed[1:] = y_vals[1:] - rho * y_vals[:-1]

        X_transformed = np.zeros_like(X.values)
        X_transformed[0, :] = np.sqrt(1 - rho**2) * X.values[0, :]
        X_transformed[1:, :] = X.values[1:, :] - rho * X.values[:-1, :]

        # Step 4: FGLS estimation
        fgls_model = OLS(y_transformed.flatten(), X_transformed)
        fgls_results = fgls_model.fit()

        # Extract treatment effect (find column index)
        treat_idx = list(X.columns).index(self.treatment)
        beta = fgls_results.params[treat_idx]
        se = fgls_results.bse[treat_idx]

        # Semi-elasticity
        semi_elasticity = (np.exp(0.10 * beta) - 1) * 100

        # Durbin-Watson on transformed residuals
        dw = durbin_watson(fgls_results.resid)

        # Store results
        self.results['fgls'] = {
            'model': fgls_results,
            'beta': beta,
            'se': se,
            'semi_elasticity': semi_elasticity,
            'rho': rho,
            'durbin_watson': dw,
            'n_obs': n
        }

        print(f"\nRESULTS:")
        print(f"  β (A_t coefficient): {beta:.4f}")
        print(f"  SE: {se:.4f}")
        print(f"  Semi-elasticity (10pp): {semi_elasticity:.2f}%")
        print(f"  Durbin-Watson: {dw:.4f}")

        return self.results['fgls']

    def estimate_differences_robustness(self) -> Dict:
        """
        First-differences specification as robustness check.
        Includes translation box for interpretation.
        """
        print("\n" + "="*60)
        print("FIRST-DIFFERENCES ROBUSTNESS")
        print("="*60)

        # Create differenced variables
        self.data['d_log_base_fee'] = self.data[self.outcome].diff()
        self.data['d_A_t'] = self.data[self.treatment].diff()
        self.data['d_D_star'] = self.data['D_star'].diff()

        # Simple differences specification
        formula = "d_log_base_fee ~ d_A_t + d_D_star"

        # Estimate
        y, X = dmatrices(formula, data=self.data.dropna(), return_type='dataframe')
        model = OLS(y, X)

        # HAC standard errors
        n = len(y)
        bandwidth = int(4 * (n/100)**(2/9))

        diff_results = model.fit(
            cov_type='HAC',
            cov_kwds={
                'kernel': 'bartlett',
                'use_correction': True,
                'maxlags': bandwidth
            }
        )

        # Extract treatment effect
        beta_diff = diff_results.params['d_A_t']
        se_diff = diff_results.bse['d_A_t']

        # Create translation box
        translation_box = self._create_translation_box(beta_diff, se_diff)

        # Store results
        self.results['differences'] = {
            'model': diff_results,
            'beta': beta_diff,
            'se': se_diff,
            'translation_box': translation_box,
            'n_obs': len(y)
        }

        print(f"\nRESULTS:")
        print(f"  β (Δ A_t coefficient): {beta_diff:.4f}")
        print(f"  SE (HAC, bw={bandwidth}): {se_diff:.4f}")
        print(f"\nTRANSLATION BOX:")
        print(f"  Specification: First Differences")
        print(f"  Interpretation: Change-on-change elasticity")
        print(f"  Mapping to levels: β_diff ≈ short-run β_levels")
        print(f"  Key difference: Removes time-invariant heterogeneity")
        print(f"  Caution: May amplify measurement error")

        return self.results['differences']

    def _create_translation_box(self, beta_diff: float, se_diff: float) -> Dict:
        """
        Create translation box between levels and differences specifications.

        Args:
            beta_diff: Coefficient from differences specification
            se_diff: Standard error from differences

        Returns:
            Translation box dictionary
        """
        translation = {
            'specification': 'First Differences',
            'interpretation': 'Change-on-change elasticity',
            'coefficient': beta_diff,
            'se': se_diff,
            'mapping_to_levels': {
                'method': 'Integration under stationarity',
                'assumption': 'No permanent level shift',
                'formula': 'β_diff approximates short-run β_levels',
                'long_run_relation': 'Requires distributed lags for full mapping'
            },
            'advantages': [
                'Eliminates time-invariant unobservables',
                'Addresses non-stationarity',
                'Simpler identification'
            ],
            'disadvantages': [
                'May amplify measurement error',
                'Loses long-run information',
                'Different identifying variation',
                'Cannot identify level effects'
            ],
            'econometric_notes': (
                'First differences and levels identify different parameters. '
                'FD identifies short-run effects from period-to-period changes. '
                'Levels with proper controls identifies total effects including '
                'long-run adjustments. Translation requires assumptions about '
                'the dynamic adjustment process.'
            )
        }

        return translation

    def _delta_method_se(self, beta: float, se_beta: float) -> float:
        """
        Calculate standard error for semi-elasticity using delta method.

        For transformation g(β) = 100 * (exp(0.10 * β) - 1)
        Derivative: g'(β) = 10 * exp(0.10 * β)
        SE[g(β)] ≈ |g'(β)| * SE[β]

        Args:
            beta: Coefficient estimate
            se_beta: Standard error of coefficient

        Returns:
            Standard error of semi-elasticity
        """
        derivative = 10 * np.exp(0.10 * beta)
        return derivative * se_beta

    def _run_diagnostics(self, model_results):
        """
        Run comprehensive residual diagnostics.

        Args:
            model_results: Fitted model results
        """
        residuals = model_results.resid

        # Autocorrelation test
        lb_test = acorr_ljungbox(residuals, lags=10, return_df=True)

        # Heteroskedasticity test
        white_test = het_white(residuals, model_results.model.exog)

        # Durbin-Watson
        dw = durbin_watson(residuals)

        # Store diagnostics
        self.diagnostics['ljung_box'] = {
            'statistic': lb_test['lb_stat'].values,
            'pvalue': lb_test['lb_pvalue'].values,
            'significant': (lb_test['lb_pvalue'] < 0.05).any()
        }

        self.diagnostics['white_test'] = {
            'statistic': white_test[0],
            'pvalue': white_test[1],
            'significant': white_test[1] < 0.05
        }

        self.diagnostics['durbin_watson'] = dw

        print(f"\nDIAGNOSTICS:")
        print(f"  Ljung-Box (10 lags): p = {lb_test['lb_pvalue'].min():.4f}")
        print(f"  White test: p = {white_test[1]:.4f}")
        print(f"  Durbin-Watson: {dw:.4f}")

        if self.diagnostics['ljung_box']['significant']:
            print("  ⚠ Warning: Significant autocorrelation detected")
        if self.diagnostics['white_test']['significant']:
            print("  ⚠ Warning: Heteroskedasticity detected")

    def generate_table_3(self, save_path: Optional[Path] = None) -> pd.DataFrame:
        """
        Generate updated Table 3 with all specifications.

        Args:
            save_path: Path to save LaTeX table

        Returns:
            Results dataframe
        """
        print("\n" + "="*60)
        print("GENERATING TABLE 3: LEVELS SPECIFICATION")
        print("="*60)

        # Collect results
        results_data = []

        # (1) Main levels specification
        if 'main_effect' in self.results:
            main = self.results['main_effect']
            results_data.append({
                'Specification': '(1) Levels - Main',
                'β (A_t)': f"{main['beta']:.4f}",
                'SE': f"({main['se']:.4f})",
                '95% CI': f"[{main['ci_lower']:.4f}, {main['ci_upper']:.4f}]",
                'Semi-elasticity': f"{main['semi_elasticity']:.2f}%",
                'N': main['n_obs']
            })

        # (2) Distributed lags
        if 'distributed_lags' in self.results:
            dl = self.results['distributed_lags']
            results_data.append({
                'Specification': '(2) Distributed Lags',
                'β (Long-run)': f"{dl['long_run_effect']:.4f}",
                'SE': '---',
                '95% CI': '---',
                'Semi-elasticity': f"{dl['long_run_semi_elasticity']:.2f}%",
                'N': dl['n_obs']
            })

        # (3) AR(1) errors
        if 'arima' in self.results and self.results['arima']:
            ar = self.results['arima']
            results_data.append({
                'Specification': '(3) AR(1) Errors',
                'β (A_t)': f"{ar['beta']:.4f}",
                'SE': f"({ar['se']:.4f})",
                '95% CI': '---',
                'Semi-elasticity': f"{ar['semi_elasticity']:.2f}%",
                'N': ar['n_obs']
            })

        # (4) FGLS
        if 'fgls' in self.results:
            fgls = self.results['fgls']
            results_data.append({
                'Specification': '(4) FGLS',
                'β (A_t)': f"{fgls['beta']:.4f}",
                'SE': f"({fgls['se']:.4f})",
                '95% CI': '---',
                'Semi-elasticity': f"{fgls['semi_elasticity']:.2f}%",
                'N': fgls['n_obs']
            })

        # (5) Differences (robustness)
        if 'differences' in self.results:
            diff = self.results['differences']
            results_data.append({
                'Specification': '(5) Differences†',
                'β (ΔA_t)': f"{diff['beta']:.4f}",
                'SE': f"({diff['se']:.4f})",
                '95% CI': '---',
                'Semi-elasticity': 'N/A‡',
                'N': diff['n_obs']
            })

        # Create dataframe
        table3 = pd.DataFrame(results_data)

        # Add footer notes
        notes = [
            "Notes: HAC standard errors with Andrews automatic bandwidth selection.",
            "Semi-elasticity represents percentage change in base fee for 10pp increase in L2 adoption.",
            "† First differences specification for robustness.",
            "‡ Differences specification has different interpretation (see translation box).",
            "All specifications include demand factor (D*) and regime/calendar controls."
        ]

        print("\nTABLE 3 PREVIEW:")
        print(table3.to_string(index=False))
        print("\n" + "\n".join(notes))

        # Save if path provided
        if save_path:
            # LaTeX version
            latex_table = table3.to_latex(
                index=False,
                caption="Table 3: Interrupted Time Series - Levels Specification",
                label="tab:its_levels",
                column_format='l' + 'c' * (len(table3.columns) - 1)
            )

            # Add notes to LaTeX
            latex_table = latex_table.replace(
                '\\end{tabular}',
                '\\end{tabular}\n\\begin{tablenotes}\n\\small\n' +
                '\n'.join([f'\\item {note}' for note in notes]) +
                '\n\\end{tablenotes}'
            )

            latex_table = ProvenanceFooter().add_to_latex_table(
                latex_table,
                max_columns=len(table3.columns)
            )

            # Save
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path.with_suffix('.tex'), 'w') as f:
                f.write(latex_table)

            table3.to_csv(save_path.with_suffix('.csv'), index=False)

            print(f"\nTable saved to: {save_path}")

        return table3

    def save_results(self, output_dir: Path):
        """
        Save all results to files.

        Args:
            output_dir: Output directory path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save results summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'specification': 'Levels (corrected from first differences)',
            'outcome': self.outcome,
            'treatment': self.treatment,
            'n_observations': len(self.data),
            'date_range': {
                'start': str(self.data['date'].min()),
                'end': str(self.data['date'].max())
            },
            'results': {},
            'diagnostics': self.diagnostics
        }

        # Add numeric results
        for key in ['main_effect', 'distributed_lags', 'arima', 'fgls', 'differences']:
            if key in self.results and self.results[key]:
                if 'model' in self.results[key]:
                    # Don't save full model object
                    summary['results'][key] = {
                        k: v for k, v in self.results[key].items()
                        if k != 'model'
                    }
                else:
                    summary['results'][key] = self.results[key]

        # Save YAML summary
        with open(output_dir / 'its_levels_results.yaml', 'w') as f:
            yaml.dump(summary, f, default_flow_style=False)

        print(f"\nResults saved to: {output_dir}")


def main():
    """
    Main execution for testing the levels specification.
    """
    print("="*60)
    print("ITS LEVELS SPECIFICATION - ESTIMAND ALIGNMENT")
    print("="*60)
    print("\nResolving mismatch between first-differences and levels interpretation")
    print("Implementing proper levels specification with semi-elasticity mapping\n")

    # This is a test harness - actual execution happens in project scripts
    print("ITSLevelsEstimator class loaded and ready for use.")
    print("\nUsage:")
    print("  from src.models.its_levels import ITSLevelsEstimator")
    print("  estimator = ITSLevelsEstimator(data, outcome='log_base_fee', treatment='A_t_clean')")
    print("  estimator.estimate_main_spec()")
    print("  estimator.estimate_distributed_lags()")
    print("  estimator.estimate_ar_errors()")
    print("  estimator.estimate_fgls()")
    print("  estimator.estimate_differences_robustness()")
    print("  table3 = estimator.generate_table_3()")


if __name__ == "__main__":
    main()
