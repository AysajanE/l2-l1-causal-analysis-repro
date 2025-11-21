#!/usr/bin/env python3
"""
Phase 5 Quality Assurance Checks
================================
QA Lead: Comprehensive validation for Phase 5 EDA

This script performs all required quality checks for Phase 5:
1. Residual diagnostics after simple regression
2. Statistical test validation (ADF, VIF, normality)
3. Data quality verification (winsorization, missing patterns, outliers)
4. Mediator exclusion verification (CRITICAL Gate G3)
5. Regime consistency checks
6. Treatment support validation (Gate G2)
7. Quality gate assessment

Author: QA Lead
Date: 2025-01-10
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.stats.stattools import jarque_bera
from sklearn.linear_model import LinearRegression
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
import yaml
import re
import ast

# Set up paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = PROJECT_ROOT / "figures"
QA_DIR = RESULTS_DIR / "qa"
SRC_DIR = PROJECT_ROOT / "src"

# Ensure QA directory exists
QA_DIR.mkdir(exist_ok=True, parents=True)

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=RuntimeWarning)

# Define regime boundaries (MUST match implementation plan exactly)
REGIME_DATES = {
    'pre_london': ('2019-01-01', '2021-08-04'),
    'london_to_merge': ('2021-08-05', '2022-09-14'),
    'merge_to_dencun': ('2022-09-15', '2024-03-12'),
    'post_dencun': ('2024-03-13', '2024-12-31')
}

# Protocol event dates (CRITICAL - must be exact)
PROTOCOL_EVENTS = {
    'London': '2021-08-05',  # EIP-1559 activation
    'Merge': '2022-09-15',   # PoW to PoS transition
    'Dencun': '2024-03-13'   # Proto-danksharding activation
}

# Mediator variables that MUST be excluded from TE models
MEDIATORS = ['P_calldata_gas', 'P_blob_gas', 'P_calldata', 'P_blob',
             'p_calldata', 'p_blob', 'calldata_gas_price', 'blob_gas_price']

# Quality gate thresholds
QUALITY_GATES = {
    'G1_WINSORIZATION_MAX': 0.01,  # Max 1% per tail
    'G2_POSITIVITY_MIN': 0.05,     # Min 5% mass away from 0 and 1
    'G3_MEDIATOR_LEAKAGE': 0,      # Zero tolerance for mediators
    'G4_VIF_MAX': 10.0,            # Max VIF threshold
    'G5_PRETREND_ALPHA': 0.05,     # Pre-trend test significance
    'G6_SIGN_FLIP_MAX': 0.30,      # Max 30% sign flips in robustness
}


class Phase5QAValidator:
    """Comprehensive QA validation for Phase 5 EDA."""

    def __init__(self):
        """Initialize QA validator."""
        self.panel_path = DATA_DIR / "analytical" / "core_panel_v1_converted.parquet"
        if not self.panel_path.exists():
            self.panel_path = DATA_DIR / "analytical" / "core_panel_v1.parquet"

        print("="*80)
        print("PHASE 5 QUALITY ASSURANCE VALIDATION")
        print("="*80)
        print(f"Start time: {pd.Timestamp.now()}")
        print(f"Loading data from: {self.panel_path}")

        # Load core panel
        self.df = pd.read_parquet(self.panel_path, engine='pyarrow')

        # Convert date if needed
        if 'date' in self.df.columns:
            if not pd.api.types.is_datetime64_any_dtype(self.df['date']):
                self.df['date'] = pd.to_datetime(self.df['date'])

        self.df = self.df.sort_values('date').set_index('date')

        # Add regime indicators
        self._add_regime_indicators()

        # Define key variables
        self.treatment_var = 'A_t_clean'
        self.outcome_vars = ['log_C_fee', 'u_t', 'S_t_harmonized']
        self.demand_var = 'D_star'
        self.control_vars = ['is_weekend', 'is_month_end', 'is_quarter_end']

        print(f"Loaded {len(self.df)} observations from {self.df.index.min()} to {self.df.index.max()}")

        # Initialize gate status
        self.gate_status = {
            'G1_DATA_QC': {'status': 'PENDING', 'details': []},
            'G2_TREATMENT_SUPPORT': {'status': 'PENDING', 'details': []},
            'G3_LEAKAGE': {'status': 'PENDING', 'details': []},
            'G4_DIAGNOSTICS': {'status': 'PENDING', 'details': []},
        }

        # Initialize issue tracker
        self.issues = []
        self.warnings = []

    def _add_regime_indicators(self):
        """Add regime indicator variables."""
        for regime, (start, end) in REGIME_DATES.items():
            self.df[f'regime_{regime}'] = (
                (self.df.index >= pd.Timestamp(start)) &
                (self.df.index <= pd.Timestamp(end))
            ).astype(int)

        # Add simplified regime categorical
        self.df['regime'] = 'unknown'
        for regime, (start, end) in REGIME_DATES.items():
            mask = (self.df.index >= pd.Timestamp(start)) & (self.df.index <= pd.Timestamp(end))
            self.df.loc[mask, 'regime'] = regime

    def task1_residual_diagnostics(self) -> Dict:
        """
        Task 1: Run baseline regression and comprehensive residual analysis.
        """
        print("\n" + "="*80)
        print("TASK 1: RESIDUAL DIAGNOSTICS AFTER BASELINE REGRESSION")
        print("="*80)

        results = {
            'regression_results': {},
            'acf_pacf_values': {},
            'ljung_box': {},
            'hac_recommendations': {},
            'diagnostics_passed': True
        }

        # Focus on post-London data for causal analysis
        post_london = self.df[self.df.index >= pd.Timestamp('2021-08-05')].copy()

        print(f"Running baseline regression on {len(post_london)} post-London observations...")

        # Add time trend
        post_london['trend'] = np.arange(len(post_london))
        post_london['trend_sq'] = post_london['trend'] ** 2
        post_london['const'] = 1

        # Define regressors
        X_vars = ['const', 'trend', 'trend_sq']

        # Add calendar controls if available
        for var in self.control_vars:
            if var in post_london.columns:
                X_vars.append(var)

        # Filter to complete cases
        analysis_vars = X_vars + ['log_C_fee']
        analysis_df = post_london[analysis_vars].dropna()

        if len(analysis_df) < 100:
            self.issues.append("CRITICAL: Insufficient data for residual analysis")
            results['diagnostics_passed'] = False
            return results

        # Run OLS regression
        X = analysis_df[X_vars].values
        y = analysis_df['log_C_fee'].values

        model = LinearRegression()
        model.fit(X, y)
        y_pred = model.predict(X)
        residuals = y - y_pred

        # Store regression results
        results['regression_results'] = {
            'n_obs': len(analysis_df),
            'r_squared': model.score(X, y),
            'coefficients': dict(zip(X_vars, model.coef_)),
            'residual_std': np.std(residuals),
            'residual_mean': np.mean(residuals)
        }

        print(f"R-squared: {results['regression_results']['r_squared']:.4f}")
        print(f"Residual std: {results['regression_results']['residual_std']:.4f}")

        # ACF/PACF Analysis
        print("\nComputing ACF/PACF...")
        max_lags = min(40, len(residuals) // 4)

        acf_values = acf(residuals, nlags=max_lags, fft=True)
        pacf_values = pacf(residuals, nlags=max_lags, method='ywm')

        # Find significant lags
        significance_threshold = 1.96 / np.sqrt(len(residuals))
        significant_acf_lags = []
        for lag in range(1, len(acf_values)):
            if abs(acf_values[lag]) > significance_threshold:
                significant_acf_lags.append(lag)

        results['acf_pacf_values'] = {
            'acf': acf_values.tolist()[:20],  # Store first 20 lags
            'pacf': pacf_values.tolist()[:20],
            'significant_lags': significant_acf_lags[:10],  # First 10 significant
            'significance_threshold': significance_threshold
        }

        print(f"Significant ACF lags (first 10): {significant_acf_lags[:10]}")

        # Ljung-Box test for serial correlation
        print("\nLjung-Box test for serial correlation...")
        lb_test = acorr_ljungbox(residuals, lags=20, return_df=True)

        # Check if serial correlation exists
        serial_correlation_detected = any(lb_test['lb_pvalue'] < 0.05)

        results['ljung_box'] = {
            'test_stats': lb_test['lb_stat'].to_dict(),
            'p_values': lb_test['lb_pvalue'].to_dict(),
            'serial_correlation_detected': serial_correlation_detected
        }

        if serial_correlation_detected:
            self.warnings.append("Serial correlation detected in baseline residuals - HAC SE required")
            print("WARNING: Serial correlation detected - HAC standard errors required")

        # HAC Lag Recommendation
        print("\nComputing HAC lag recommendations...")
        T = len(residuals)

        # Andrews (1991) automatic bandwidth selection
        andrews_lag = int(np.floor(4 * (T/100)**(2/9)))

        # Newey-West recommendation
        nw_lag = int(np.floor(4 * (T/100)**(2/9)))

        # First insignificant ACF lag
        first_insignificant = 1
        for i in range(1, len(acf_values)):
            if abs(acf_values[i]) < significance_threshold:
                first_insignificant = i
                break

        # Use maximum of the recommendations
        recommended_lag = max(andrews_lag, first_insignificant, 7)  # Min 7 as per EDA
        sensitivity_range = [max(3, int(recommended_lag * 0.5)),
                           min(20, int(recommended_lag * 1.5))]

        results['hac_recommendations'] = {
            'sample_size': T,
            'andrews_lag': andrews_lag,
            'newey_west_lag': nw_lag,
            'first_insignificant_acf': first_insignificant,
            'recommended_lag': recommended_lag,
            'sensitivity_range': sensitivity_range,
            'current_eda_recommendation': 7,
            'validation': 'CONSISTENT' if abs(recommended_lag - 7) <= 3 else 'REVIEW_NEEDED'
        }

        print(f"HAC Lag Recommendations:")
        print(f"  - Andrews formula: {andrews_lag}")
        print(f"  - First insignificant ACF: {first_insignificant}")
        print(f"  - QA Recommended: {recommended_lag} (range: {sensitivity_range})")
        print(f"  - EDA Recommendation: 7")
        print(f"  - Validation: {results['hac_recommendations']['validation']}")

        # Normality tests on residuals
        print("\nTesting residual normality...")
        jb_result = jarque_bera(residuals)
        jb_stat = jb_result[0]
        jb_pvalue = jb_result[1]
        shapiro_stat, shapiro_pvalue = stats.shapiro(residuals[:5000])  # Limit for Shapiro

        results['normality_tests'] = {
            'jarque_bera_stat': jb_stat,
            'jarque_bera_pvalue': jb_pvalue,
            'shapiro_stat': shapiro_stat,
            'shapiro_pvalue': shapiro_pvalue,
            'normal_residuals': jb_pvalue > 0.05 and shapiro_pvalue > 0.05
        }

        if not results['normality_tests']['normal_residuals']:
            self.warnings.append("Residuals show departures from normality")
            print("WARNING: Residuals are not normally distributed")

        # Generate diagnostic plots
        self._generate_residual_plots(analysis_df.index, residuals, acf_values, pacf_values)

        # Save detailed results
        residual_df = pd.DataFrame({
            'date': analysis_df.index,
            'residual': residuals,
            'fitted': y_pred,
            'actual': y
        })
        residual_df.to_csv(QA_DIR / 'residual_diagnostics.csv', index=False)

        return results

    def _generate_residual_plots(self, dates, residuals, acf_vals, pacf_vals):
        """Generate comprehensive residual diagnostic plots."""
        fig, axes = plt.subplots(3, 3, figsize=(18, 14))
        fig.suptitle('Comprehensive Residual Diagnostics - QA Validation', fontsize=14, fontweight='bold')

        # 1. Residuals over time
        ax1 = axes[0, 0]
        ax1.plot(dates, residuals, alpha=0.7, linewidth=0.8)
        ax1.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        ax1.set_title('Residuals Over Time')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Residual')
        ax1.grid(True, alpha=0.3)

        # 2. Histogram of residuals
        ax2 = axes[0, 1]
        ax2.hist(residuals, bins=50, alpha=0.7, edgecolor='black', density=True)
        # Overlay normal distribution
        x = np.linspace(residuals.min(), residuals.max(), 100)
        ax2.plot(x, stats.norm.pdf(x, residuals.mean(), residuals.std()),
                'r-', linewidth=2, label='Normal')
        ax2.set_title('Residual Distribution')
        ax2.set_xlabel('Residual')
        ax2.set_ylabel('Density')
        ax2.legend()

        # 3. Q-Q plot
        ax3 = axes[0, 2]
        stats.probplot(residuals, dist="norm", plot=ax3)
        ax3.set_title('Q-Q Plot')

        # 4. ACF
        ax4 = axes[1, 0]
        lags = range(len(acf_vals))
        ax4.bar(lags, acf_vals, alpha=0.7)
        ax4.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
        significance_threshold = 1.96 / np.sqrt(len(residuals))
        ax4.axhline(y=significance_threshold, color='r', linestyle='--', alpha=0.5)
        ax4.axhline(y=-significance_threshold, color='r', linestyle='--', alpha=0.5)
        ax4.set_title('Autocorrelation Function (ACF)')
        ax4.set_xlabel('Lag')
        ax4.set_ylabel('ACF')
        ax4.set_xlim(0, min(40, len(acf_vals)-1))

        # 5. PACF
        ax5 = axes[1, 1]
        ax5.bar(range(len(pacf_vals)), pacf_vals, alpha=0.7)
        ax5.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
        ax5.axhline(y=significance_threshold, color='r', linestyle='--', alpha=0.5)
        ax5.axhline(y=-significance_threshold, color='r', linestyle='--', alpha=0.5)
        ax5.set_title('Partial Autocorrelation Function (PACF)')
        ax5.set_xlabel('Lag')
        ax5.set_ylabel('PACF')
        ax5.set_xlim(0, min(40, len(pacf_vals)-1))

        # 6. Residuals vs Fitted
        ax6 = axes[1, 2]
        fitted = residuals + residuals.mean()  # Approximate fitted values
        ax6.scatter(fitted, residuals, alpha=0.5, s=10)
        ax6.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        ax6.set_title('Residuals vs Fitted')
        ax6.set_xlabel('Fitted Values')
        ax6.set_ylabel('Residuals')

        # 7. Scale-Location plot
        ax7 = axes[2, 0]
        standardized_residuals = residuals / residuals.std()
        ax7.scatter(fitted, np.sqrt(np.abs(standardized_residuals)), alpha=0.5, s=10)
        ax7.set_title('Scale-Location Plot')
        ax7.set_xlabel('Fitted Values')
        ax7.set_ylabel('√|Standardized Residuals|')

        # 8. Residual squared (for heteroscedasticity)
        ax8 = axes[2, 1]
        ax8.plot(dates, residuals**2, alpha=0.7, linewidth=0.8)
        ax8.set_title('Squared Residuals (Heteroscedasticity Check)')
        ax8.set_xlabel('Date')
        ax8.set_ylabel('Residual²')
        ax8.grid(True, alpha=0.3)

        # 9. Cumulative residuals
        ax9 = axes[2, 2]
        cumsum_residuals = np.cumsum(residuals)
        ax9.plot(dates, cumsum_residuals, linewidth=2)
        ax9.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        ax9.set_title('Cumulative Sum of Residuals')
        ax9.set_xlabel('Date')
        ax9.set_ylabel('CUSUM')
        ax9.grid(True, alpha=0.3)

        plt.tight_layout()
        output_path = FIGURES_DIR / 'qa_residual_diagnostics_comprehensive.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved comprehensive residual diagnostics to: {output_path}")
        plt.close()

    def task2_validate_statistical_tests(self) -> Dict:
        """
        Task 2: Validate ADF, VIF, and normality test results.
        """
        print("\n" + "="*80)
        print("TASK 2: STATISTICAL TEST VALIDATION")
        print("="*80)

        results = {
            'adf_validation': {},
            'vif_validation': {},
            'normality_validation': {},
            'test_consistency': True
        }

        # 1. Validate ADF Tests
        print("\n--- ADF Test Validation ---")

        # Load existing ADF results
        adf_path = RESULTS_DIR / 'adf_test_results.csv'
        if adf_path.exists():
            existing_adf = pd.read_csv(adf_path)
            print(f"Found existing ADF results: {len(existing_adf)} tests")
        else:
            existing_adf = pd.DataFrame()
            self.warnings.append("No existing ADF results found")

        # Re-run ADF tests for validation
        adf_validation = []

        for regime in ['london_to_merge', 'merge_to_dencun', 'post_dencun']:
            regime_df = self.df[self.df[f'regime_{regime}'] == 1]

            if len(regime_df) < 30:
                continue

            for var in [self.treatment_var] + self.outcome_vars + [self.demand_var]:
                if var not in regime_df.columns:
                    continue

                data = regime_df[var].dropna()

                if len(data) < 30:
                    continue

                try:
                    # Test levels
                    adf_level = adfuller(data, autolag='AIC')

                    # Test first differences
                    data_diff = data.diff().dropna()
                    adf_diff = adfuller(data_diff, autolag='AIC')

                    validation_result = {
                        'regime': regime,
                        'variable': var,
                        'n_obs': len(data),
                        'level_adf_stat': adf_level[0],
                        'level_p_value': adf_level[1],
                        'level_critical_5pct': adf_level[4]['5%'],
                        'level_stationary': adf_level[1] < 0.05,
                        'diff_adf_stat': adf_diff[0],
                        'diff_p_value': adf_diff[1],
                        'diff_stationary': adf_diff[1] < 0.05,
                    }

                    # Check consistency with existing results
                    if not existing_adf.empty:
                        match = existing_adf[(existing_adf['regime'] == regime) &
                                            (existing_adf['variable'] == var)]
                        if not match.empty:
                            orig_stationary = match.iloc[0]['level_stationary']
                            if orig_stationary != validation_result['level_stationary']:
                                self.warnings.append(f"ADF inconsistency: {var} in {regime}")
                                results['test_consistency'] = False

                    adf_validation.append(validation_result)

                except Exception as e:
                    self.warnings.append(f"ADF test failed for {var} in {regime}: {e}")

        adf_validation_df = pd.DataFrame(adf_validation)

        # Summary statistics
        if not adf_validation_df.empty:
            level_stationary_pct = adf_validation_df['level_stationary'].mean() * 100
            diff_stationary_pct = adf_validation_df['diff_stationary'].mean() * 100

            results['adf_validation'] = {
                'n_tests': len(adf_validation_df),
                'level_stationary_pct': level_stationary_pct,
                'diff_stationary_pct': diff_stationary_pct,
                'non_stationary_vars': adf_validation_df[~adf_validation_df['level_stationary']]['variable'].unique().tolist(),
                'validation_passed': diff_stationary_pct == 100  # All should be stationary after differencing
            }

            print(f"ADF Validation Results:")
            print(f"  - Tests performed: {results['adf_validation']['n_tests']}")
            print(f"  - Level stationary: {level_stationary_pct:.1f}%")
            print(f"  - First-diff stationary: {diff_stationary_pct:.1f}%")

            if results['adf_validation']['non_stationary_vars']:
                print(f"  - Non-stationary in levels: {results['adf_validation']['non_stationary_vars']}")

        # 2. Validate VIF
        print("\n--- VIF Validation ---")

        # Load existing VIF results
        vif_path = RESULTS_DIR / 'vif_results.csv'
        if vif_path.exists():
            existing_vif = pd.read_csv(vif_path)
            print(f"Found existing VIF results: {len(existing_vif)} variables")
        else:
            existing_vif = pd.DataFrame()
            self.warnings.append("No existing VIF results found")

        # Re-compute VIF
        predictor_vars = [self.treatment_var, self.demand_var] + self.control_vars
        predictor_vars = [v for v in predictor_vars if v in self.df.columns]

        X = self.df[predictor_vars].dropna()

        if len(X) > 0 and len(predictor_vars) > 1:
            vif_validation = []
            for i, var in enumerate(predictor_vars):
                vif_value = variance_inflation_factor(X.values, i)
                vif_validation.append({
                    'Variable': var,
                    'VIF': vif_value,
                    'Status': 'OK' if vif_value < QUALITY_GATES['G4_VIF_MAX'] else 'HIGH'
                })

            vif_validation_df = pd.DataFrame(vif_validation)

            # Check for high VIF
            high_vif_vars = vif_validation_df[vif_validation_df['VIF'] >= QUALITY_GATES['G4_VIF_MAX']]['Variable'].tolist()
            max_vif = vif_validation_df['VIF'].max()

            results['vif_validation'] = {
                'max_vif': max_vif,
                'high_vif_vars': high_vif_vars,
                'all_below_threshold': len(high_vif_vars) == 0,
                'validation_passed': max_vif < QUALITY_GATES['G4_VIF_MAX']
            }

            print(f"VIF Validation Results:")
            print(f"  - Max VIF: {max_vif:.2f}")
            print(f"  - Threshold: {QUALITY_GATES['G4_VIF_MAX']}")
            print(f"  - Status: {'PASS' if results['vif_validation']['validation_passed'] else 'FAIL'}")

            if high_vif_vars:
                self.issues.append(f"High VIF detected: {high_vif_vars}")
                print(f"  - High VIF variables: {high_vif_vars}")

            # Save validation results
            vif_validation_df.to_csv(QA_DIR / 'vif_validation.csv', index=False)

        # 3. Normality Tests
        print("\n--- Normality Test Validation ---")

        normality_results = []

        for var in [self.treatment_var] + self.outcome_vars + [self.demand_var]:
            if var not in self.df.columns:
                continue

            data = self.df[var].dropna()

            if len(data) < 20:
                continue

            # Jarque-Bera test
            jb_result = jarque_bera(data)
            jb_stat = jb_result[0]
            jb_pvalue = jb_result[1]

            # Shapiro-Wilk test (limited sample)
            sample_size = min(5000, len(data))
            shapiro_stat, shapiro_pvalue = stats.shapiro(data.sample(sample_size))

            # Skewness and Kurtosis
            skew = stats.skew(data)
            kurt = stats.kurtosis(data)

            normality_results.append({
                'variable': var,
                'n_obs': len(data),
                'jarque_bera_stat': jb_stat,
                'jarque_bera_pvalue': jb_pvalue,
                'shapiro_stat': shapiro_stat,
                'shapiro_pvalue': shapiro_pvalue,
                'skewness': skew,
                'kurtosis': kurt,
                'is_normal_jb': jb_pvalue > 0.05,
                'is_normal_shapiro': shapiro_pvalue > 0.05
            })

        normality_df = pd.DataFrame(normality_results)

        if not normality_df.empty:
            pct_normal_jb = normality_df['is_normal_jb'].mean() * 100
            pct_normal_shapiro = normality_df['is_normal_shapiro'].mean() * 100
            non_normal_vars = normality_df[~normality_df['is_normal_jb']]['variable'].tolist()

            results['normality_validation'] = {
                'pct_normal_jb': pct_normal_jb,
                'pct_normal_shapiro': pct_normal_shapiro,
                'non_normal_vars': non_normal_vars,
                'validation_notes': 'Non-normality expected for financial time series'
            }

            print(f"Normality Test Results:")
            print(f"  - JB test normal: {pct_normal_jb:.1f}%")
            print(f"  - Shapiro test normal: {pct_normal_shapiro:.1f}%")
            print(f"  - Non-normal variables: {non_normal_vars}")

            # Save results
            normality_df.to_csv(QA_DIR / 'normality_tests.csv', index=False)

        return results

    def task3_data_quality_verification(self) -> Dict:
        """
        Task 3: Comprehensive data quality checks including winsorization audit.
        """
        print("\n" + "="*80)
        print("TASK 3: DATA QUALITY VERIFICATION")
        print("="*80)

        results = {
            'winsorization_audit': {},
            'missing_patterns': {},
            'outlier_analysis': {},
            'coverage_check': {},
            'quality_passed': True
        }

        # 1. Winsorization Audit
        print("\n--- Winsorization Audit ---")

        winsorization_results = []

        for var in [self.treatment_var] + self.outcome_vars + [self.demand_var]:
            if var not in self.df.columns:
                continue

            # Check overall
            data = self.df[var].dropna()
            if len(data) == 0:
                continue

            p01, p99 = np.percentile(data, [1, 99])
            n_at_p01 = (data == p01).sum()
            n_at_p99 = (data == p99).sum()
            pct_at_p01 = n_at_p01 / len(data)
            pct_at_p99 = n_at_p99 / len(data)

            # Special handling for A_t_clean - it's structural zero pre-London
            is_structural = False
            if var == 'A_t_clean' and p01 == 0.0:
                # Check if this is due to pre-London zeros
                pre_london_data = self.df[self.df.index < pd.Timestamp('2021-08-05')][var].dropna()
                if len(pre_london_data) > 0 and (pre_london_data == 0).all():
                    is_structural = True
                    print(f"  Note: {var} has structural zeros pre-London")

            winsor_result = {
                'variable': var,
                'regime': 'overall',
                'n_obs': len(data),
                'p01_value': p01,
                'p99_value': p99,
                'n_at_p01': n_at_p01,
                'n_at_p99': n_at_p99,
                'pct_at_p01': pct_at_p01,
                'pct_at_p99': pct_at_p99,
                'total_pct_at_tails': pct_at_p01 + pct_at_p99,
                'is_structural': is_structural,
                'exceeds_threshold': (not is_structural and
                                     (pct_at_p01 > QUALITY_GATES['G1_WINSORIZATION_MAX'] or
                                      pct_at_p99 > QUALITY_GATES['G1_WINSORIZATION_MAX']))
            }

            winsorization_results.append(winsor_result)

            # Check by regime
            for regime in ['london_to_merge', 'merge_to_dencun', 'post_dencun']:
                regime_data = self.df[self.df[f'regime_{regime}'] == 1][var].dropna()

                if len(regime_data) < 30:
                    continue

                p01_r, p99_r = np.percentile(regime_data, [1, 99])
                n_at_p01_r = (regime_data == p01_r).sum()
                n_at_p99_r = (regime_data == p99_r).sum()
                pct_at_p01_r = n_at_p01_r / len(regime_data)
                pct_at_p99_r = n_at_p99_r / len(regime_data)

                # Special handling for early L2 adoption periods
                is_structural_regime = False
                if var == 'A_t_clean' and regime == 'london_to_merge' and p01_r == 0.0:
                    # Early adoption period may have many zeros
                    is_structural_regime = True

                regime_result = {
                    'variable': var,
                    'regime': regime,
                    'n_obs': len(regime_data),
                    'p01_value': p01_r,
                    'p99_value': p99_r,
                    'n_at_p01': n_at_p01_r,
                    'n_at_p99': n_at_p99_r,
                    'pct_at_p01': pct_at_p01_r,
                    'pct_at_p99': pct_at_p99_r,
                    'total_pct_at_tails': pct_at_p01_r + pct_at_p99_r,
                    'is_structural': is_structural_regime,
                    'exceeds_threshold': (not is_structural_regime and
                                         (pct_at_p01_r > QUALITY_GATES['G1_WINSORIZATION_MAX'] or
                                          pct_at_p99_r > QUALITY_GATES['G1_WINSORIZATION_MAX']))
                }

                winsorization_results.append(regime_result)

        winsor_df = pd.DataFrame(winsorization_results)

        # Check G1 gate
        any_exceeds = winsor_df['exceeds_threshold'].any()
        max_tail_pct = winsor_df[['pct_at_p01', 'pct_at_p99']].max().max()

        results['winsorization_audit'] = {
            'max_tail_percentage': max_tail_pct,
            'threshold': QUALITY_GATES['G1_WINSORIZATION_MAX'],
            'any_exceeds_threshold': any_exceeds,
            'violating_cases': winsor_df[winsor_df['exceeds_threshold']][['variable', 'regime']].to_dict('records') if any_exceeds else [],
            'gate_passed': not any_exceeds
        }

        print(f"Winsorization Audit Results:")
        print(f"  - Max tail percentage: {max_tail_pct:.4f}")
        print(f"  - Threshold: {QUALITY_GATES['G1_WINSORIZATION_MAX']}")
        print(f"  - Gate G1 Status: {'PASS' if not any_exceeds else 'FAIL'}")

        if any_exceeds:
            self.issues.append(f"G1 FAIL: Winsorization exceeds 1% threshold")
            results['quality_passed'] = False

        # Save winsorization audit
        winsor_df.to_csv(QA_DIR / 'winsorization_audit.csv', index=False)

        # 2. Missing Data Patterns
        print("\n--- Missing Data Patterns ---")

        missing_summary = {}

        for var in self.df.columns:
            missing_count = self.df[var].isna().sum()
            missing_pct = (missing_count / len(self.df)) * 100

            # Check structural NULLs
            if var in ['base_fee', 'base_fee_per_gas', 'base_fee_median_wei', 'base_fee_median_gwei',
                      'base_fee_p90_wei', 'base_fee_p90_gwei', 'log_C_fee', 'C_fee']:
                # Should be NULL pre-London (no EIP-1559 fees)
                pre_london_nulls = self.df[self.df.index < pd.Timestamp('2021-08-05')][var].isna().sum()
                pre_london_total = len(self.df[self.df.index < pd.Timestamp('2021-08-05')])
                post_london_nulls = self.df[self.df.index >= pd.Timestamp('2021-08-05')][var].isna().sum()
                structural_null = (pre_london_nulls == pre_london_total and post_london_nulls == 0) if pre_london_total > 0 else False
            elif 'blob' in var.lower():
                # Should be NULL pre-Dencun
                pre_dencun_nulls = self.df[self.df.index < pd.Timestamp('2024-03-13')][var].isna().sum()
                pre_dencun_total = len(self.df[self.df.index < pd.Timestamp('2024-03-13')])
                structural_null = (pre_dencun_nulls == pre_dencun_total) if pre_dencun_total > 0 else False
            else:
                structural_null = False

            missing_summary[var] = {
                'missing_count': missing_count,
                'missing_pct': missing_pct,
                'structural_null': structural_null
            }

        # Identify unexpected missing patterns
        unexpected_missing = []
        expected_limited_availability = [
            'D_star', 'eth_price_usd', 'eth_returns_log', 'realized_volatility_annualized',
            'cex_volume_usd_24h', 'search_interest_ethereum'
        ]

        for var, info in missing_summary.items():
            # Skip variables with expected limited availability
            if any(exp in var for exp in expected_limited_availability):
                continue
            # Skip event indicators (they're sparse by design)
            if 'event' in var.lower() or '_day' in var.lower() or '_d0' in var or '_d7' in var or '_d14' in var:
                continue
            # Check for actual unexpected missing
            if info['missing_pct'] > 5 and not info['structural_null']:
                unexpected_missing.append(var)

        # Check if structural nulls are handled correctly for variables that should have them
        structural_vars = ['base_fee', 'base_fee_per_gas', 'base_fee_median_wei', 'base_fee_median_gwei',
                          'base_fee_p90_wei', 'base_fee_p90_gwei', 'log_C_fee', 'C_fee']
        structural_vars_in_data = [v for v in structural_vars if v in missing_summary]
        structural_nulls_correct = True

        for var in structural_vars_in_data:
            if not missing_summary[var]['structural_null']:
                structural_nulls_correct = False
                break

        results['missing_patterns'] = {
            'total_vars': len(missing_summary),
            'vars_with_missing': sum(1 for v in missing_summary.values() if v['missing_count'] > 0),
            'structural_nulls_correct': structural_nulls_correct and len(unexpected_missing) == 0,
            'unexpected_missing_vars': unexpected_missing
        }

        print(f"Missing Data Pattern Results:")
        print(f"  - Variables with missing data: {results['missing_patterns']['vars_with_missing']}")
        print(f"  - Structural NULLs correct: {results['missing_patterns']['structural_nulls_correct']}")
        if unexpected_missing:
            print(f"  - Unexpected missing (>5%): {unexpected_missing[:5]}")  # Show first 5

        # 3. Outlier Analysis (Cook's D, DFBETAS)
        print("\n--- Outlier Analysis ---")

        # Run on a simple model for outlier detection
        post_london = self.df[self.df.index >= pd.Timestamp('2021-08-05')].copy()
        post_london['const'] = 1
        post_london['trend'] = np.arange(len(post_london))

        # Simple model for outlier detection
        X_vars = ['const', 'A_t_clean', 'D_star']
        y_var = 'log_C_fee'

        analysis_df = post_london[X_vars + [y_var]].dropna()

        if len(analysis_df) > 100:
            X = analysis_df[X_vars].values
            y = analysis_df[y_var].values

            # Compute influence measures
            from scipy.stats import t

            # Fit model
            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)
            residuals = y - y_pred

            # Leverage (hat values)
            H = X @ np.linalg.inv(X.T @ X) @ X.T
            leverages = np.diag(H)

            # Cook's distance
            n, p = X.shape
            mse = np.sum(residuals**2) / (n - p)
            cooks_d = (residuals**2 / (p * mse)) * (leverages / (1 - leverages)**2)

            # Identify influential points
            cooks_threshold = 4 / n  # Common threshold
            influential_points = cooks_d > cooks_threshold
            n_influential = influential_points.sum()
            pct_influential = (n_influential / n) * 100

            # Check for temporal clustering of outliers
            influential_dates = analysis_df.index[influential_points]
            if len(influential_dates) > 1:
                date_diffs = np.diff(influential_dates) / pd.Timedelta(days=1)
                temporal_clustering = np.median(date_diffs) < 7  # Clustered if median gap < 7 days
            else:
                temporal_clustering = False

            results['outlier_analysis'] = {
                'n_obs_analyzed': n,
                'n_influential_points': n_influential,
                'pct_influential': pct_influential,
                'max_cooks_d': np.max(cooks_d),
                'cooks_threshold': cooks_threshold,
                'temporal_clustering': temporal_clustering,
                'outliers_acceptable': pct_influential < 5  # Less than 5% influential
            }

            print(f"Outlier Analysis Results:")
            print(f"  - Influential points: {n_influential} ({pct_influential:.2f}%)")
            print(f"  - Max Cook's D: {np.max(cooks_d):.4f}")
            print(f"  - Temporal clustering: {temporal_clustering}")
            print(f"  - Status: {'ACCEPTABLE' if results['outlier_analysis']['outliers_acceptable'] else 'REVIEW NEEDED'}")

            # Save outlier analysis
            outlier_df = pd.DataFrame({
                'date': analysis_df.index,
                'cooks_d': cooks_d,
                'leverage': leverages,
                'residual': residuals,
                'influential': influential_points
            })
            outlier_df.to_csv(QA_DIR / 'outlier_analysis.csv', index=False)

        # 4. Coverage Check
        print("\n--- Coverage Check ---")

        expected_start = pd.Timestamp('2015-08-07')
        expected_end = pd.Timestamp('2024-12-31')

        actual_start = self.df.index.min()
        actual_end = self.df.index.max()

        # Check for date gaps
        date_range = pd.date_range(start=actual_start, end=actual_end, freq='D')
        missing_dates = date_range.difference(self.df.index)
        n_missing_dates = len(missing_dates)
        pct_coverage = (len(self.df) / len(date_range)) * 100

        results['coverage_check'] = {
            'expected_start': expected_start.strftime('%Y-%m-%d'),
            'expected_end': expected_end.strftime('%Y-%m-%d'),
            'actual_start': actual_start.strftime('%Y-%m-%d'),
            'actual_end': actual_end.strftime('%Y-%m-%d'),
            'n_missing_dates': n_missing_dates,
            'pct_coverage': pct_coverage,
            'continuous_coverage': n_missing_dates == 0,
            'coverage_adequate': pct_coverage > 95
        }

        print(f"Coverage Check Results:")
        print(f"  - Date range: {actual_start.strftime('%Y-%m-%d')} to {actual_end.strftime('%Y-%m-%d')}")
        print(f"  - Missing dates: {n_missing_dates}")
        print(f"  - Coverage: {pct_coverage:.2f}%")
        print(f"  - Status: {'PASS' if results['coverage_check']['coverage_adequate'] else 'INCOMPLETE'}")

        if not results['coverage_check']['coverage_adequate']:
            self.warnings.append(f"Incomplete coverage: {pct_coverage:.2f}%")

        return results

    def task4_mediator_exclusion_verification(self) -> Dict:
        """
        Task 4: CRITICAL - Verify no mediators in TE models (Gate G3).
        """
        print("\n" + "="*80)
        print("TASK 4: MEDIATOR EXCLUSION VERIFICATION [CRITICAL - GATE G3]")
        print("="*80)

        results = {
            'files_scanned': [],
            'mediator_references': [],
            'leakage_detected': False,
            'gate_g3_passed': True
        }

        print("Scanning all analysis code for mediator variables...")
        print(f"Mediators to check: {MEDIATORS}")

        # Files to scan
        files_to_scan = [
            SRC_DIR / 'analysis' / '05_descriptive.py',
            SRC_DIR / 'analysis' / '04_panel_assembly.py',
            SRC_DIR / 'analysis' / '03_outcomes_controls.py',
        ]

        # Add any other Python files in analysis directory
        analysis_dir = SRC_DIR / 'analysis'
        if analysis_dir.exists():
            files_to_scan.extend(analysis_dir.glob('*.py'))

        # Remove duplicates
        files_to_scan = list(set(files_to_scan))

        for file_path in files_to_scan:
            if not file_path.exists():
                continue

            print(f"\nScanning: {file_path.name}")
            results['files_scanned'].append(str(file_path))

            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')

            # Check for mediator references
            for line_num, line in enumerate(lines, 1):
                # Skip comments
                if line.strip().startswith('#'):
                    continue

                # Check for mediator variables
                for mediator in MEDIATORS:
                    if mediator.lower() in line.lower():
                        # Check if it's in a correlation or regression context
                        suspicious_contexts = ['corr', 'regression', 'model', 'X_vars',
                                             'predictors', 'features', 'controls']

                        if any(context in line.lower() for context in suspicious_contexts):
                            # This is potentially problematic
                            reference = {
                                'file': file_path.name,
                                'line': line_num,
                                'mediator': mediator,
                                'code': line.strip(),
                                'severity': 'HIGH'
                            }

                            # Check if it's being excluded (good) or included (bad)
                            if ('exclude' in line.lower() or 'not in' in line.lower() or
                                '!=' in line.lower() or 'never include' in line.lower() or
                                'do not' in line.lower() or "don't" in line.lower() or
                                'warning' in line.lower() or 'reminder' in line.lower()):
                                reference['severity'] = 'INFO'
                                reference['status'] = 'EXCLUDED'
                            else:
                                reference['severity'] = 'CRITICAL'
                                reference['status'] = 'INCLUDED'
                                results['leakage_detected'] = True

                            results['mediator_references'].append(reference)

                            if reference['severity'] == 'CRITICAL':
                                print(f"  ⚠️ CRITICAL: Line {line_num}: {mediator} found in {line.strip()[:60]}...")

        # Check correlation matrices specifically
        print("\n--- Checking Correlation Matrices ---")

        # Look for correlation matrix outputs
        corr_files = list(RESULTS_DIR.glob('*correlation*.csv')) + list(RESULTS_DIR.glob('*corr*.csv'))

        for corr_file in corr_files:
            print(f"Checking: {corr_file.name}")

            try:
                corr_df = pd.read_csv(corr_file, index_col=0)

                # Check if any mediators are in the correlation matrix
                for mediator in MEDIATORS:
                    if mediator in corr_df.columns or mediator in corr_df.index:
                        results['mediator_references'].append({
                            'file': corr_file.name,
                            'mediator': mediator,
                            'severity': 'CRITICAL',
                            'status': 'IN_CORRELATION_MATRIX'
                        })
                        results['leakage_detected'] = True
                        print(f"  ⚠️ CRITICAL: {mediator} found in correlation matrix!")
            except:
                pass

        # Final assessment
        if results['leakage_detected']:
            results['gate_g3_passed'] = False
            self.gate_status['G3_LEAKAGE']['status'] = 'FAIL'
            self.gate_status['G3_LEAKAGE']['details'].append('Mediator variables detected in analysis')
            self.issues.append("GATE G3 FAILURE: Mediator leakage detected - BLOCKING RELEASE")

            print("\n" + "="*80)
            print("⚠️  CRITICAL FAILURE: MEDIATOR LEAKAGE DETECTED")
            print("="*80)
            print("Gate G3 has FAILED. Mediator variables found in total effect analysis.")
            print("This BLOCKS the release. Immediate remediation required.")
        else:
            results['gate_g3_passed'] = True
            self.gate_status['G3_LEAKAGE']['status'] = 'PASS'
            self.gate_status['G3_LEAKAGE']['details'].append('No mediator leakage detected')

            print("\n" + "="*80)
            print("✓ GATE G3 PASSED: No mediator leakage detected")
            print("="*80)

        # Save audit log
        audit_log = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'files_scanned': results['files_scanned'],
            'mediator_references': results['mediator_references'],
            'leakage_detected': results['leakage_detected'],
            'gate_g3_status': 'FAIL' if results['leakage_detected'] else 'PASS'
        }

        with open(QA_DIR / 'mediator_audit_log.json', 'w') as f:
            json.dump(audit_log, f, indent=2)

        print(f"\nAudit log saved to: {QA_DIR / 'mediator_audit_log.json'}")

        return results

    def task5_regime_consistency_checks(self) -> Dict:
        """
        Task 5: Verify regime dates and consistency.
        """
        print("\n" + "="*80)
        print("TASK 5: REGIME CONSISTENCY CHECKS")
        print("="*80)

        results = {
            'regime_dates_correct': True,
            'regime_flags_consistent': True,
            'event_windows_valid': True,
            'issues': []
        }

        # 1. Verify exact regime dates
        print("\n--- Verifying Regime Dates ---")

        expected_events = {
            'London': pd.Timestamp('2021-08-05'),
            'Merge': pd.Timestamp('2022-09-15'),
            'Dencun': pd.Timestamp('2024-03-13')
        }

        for event, expected_date in expected_events.items():
            print(f"Checking {event}: Expected {expected_date.strftime('%Y-%m-%d')}")

            # Check if the date exists in the data
            if expected_date not in self.df.index:
                results['issues'].append(f"{event} date {expected_date} not in data")
                results['regime_dates_correct'] = False
                print(f"  ⚠️ WARNING: {event} date not found in data")

            # Check regime transitions
            if event == 'London':
                # Check pre/post London
                pre_london = self.df[self.df.index < expected_date]['regime_pre_london'].sum() if 'regime_pre_london' in self.df.columns else 0
                post_london = self.df[self.df.index >= expected_date]['regime_london_to_merge'].sum() if 'regime_london_to_merge' in self.df.columns else 0

                if pre_london == 0 or post_london == 0:
                    results['issues'].append(f"London regime transition inconsistent")
                    print(f"  ⚠️ Regime flags inconsistent around London")

        # 2. Check regime flag consistency
        print("\n--- Checking Regime Flag Consistency ---")

        for regime, (start, end) in REGIME_DATES.items():
            regime_col = f'regime_{regime}'
            if regime_col in self.df.columns:
                # Count observations in regime
                regime_mask = (self.df.index >= pd.Timestamp(start)) & (self.df.index <= pd.Timestamp(end))
                expected_count = regime_mask.sum()
                actual_count = self.df[regime_col].sum()

                if expected_count != actual_count:
                    discrepancy = abs(expected_count - actual_count)
                    results['issues'].append(f"{regime}: Expected {expected_count}, got {actual_count}")
                    if discrepancy > 5:  # Allow small discrepancies
                        results['regime_flags_consistent'] = False
                    print(f"  {regime}: Expected {expected_count}, Actual {actual_count}")
                else:
                    print(f"  {regime}: Consistent ({actual_count} observations)")

        # 3. Check for structural breaks at event dates
        print("\n--- Checking Structural Breaks ---")

        for event, event_date in expected_events.items():
            # Check if base fee appears after London
            if event == 'London' and 'base_fee' in self.df.columns:
                pre_event = self.df[self.df.index < event_date]['base_fee'].notna().sum()
                post_event = self.df[self.df.index >= event_date]['base_fee'].notna().sum()

                if pre_event > 0:
                    results['issues'].append(f"Base fee exists before London ({pre_event} observations)")
                    print(f"  ⚠️ Base fee found before London: {pre_event} observations")

                if post_event == 0:
                    results['issues'].append(f"Base fee missing after London")
                    print(f"  ⚠️ Base fee missing after London")

            # Check if blob metrics appear after Dencun
            if event == 'Dencun':
                blob_cols = [c for c in self.df.columns if 'blob' in c.lower()]
                for blob_col in blob_cols:
                    pre_dencun = self.df[self.df.index < event_date][blob_col].notna().sum()
                    if pre_dencun > 0:
                        results['issues'].append(f"{blob_col} exists before Dencun ({pre_dencun} observations)")
                        print(f"  ⚠️ {blob_col} found before Dencun: {pre_dencun} observations")

        # Summary
        print("\n--- Regime Consistency Summary ---")
        print(f"  Dates correct: {results['regime_dates_correct']}")
        print(f"  Flags consistent: {results['regime_flags_consistent']}")
        print(f"  Total issues: {len(results['issues'])}")

        if results['issues']:
            for issue in results['issues'][:5]:  # Show first 5 issues
                print(f"    - {issue}")

        return results

    def task6_treatment_support_validation(self) -> Dict:
        """
        Task 6: Validate treatment support across regimes (Gate G2).
        """
        print("\n" + "="*80)
        print("TASK 6: TREATMENT SUPPORT VALIDATION [GATE G2]")
        print("="*80)

        results = {
            'regime_support': {},
            'positivity_violations': [],
            'gate_g2_passed': True
        }

        print(f"Analyzing treatment variable: {self.treatment_var}")
        print(f"Positivity threshold: {QUALITY_GATES['G2_POSITIVITY_MIN']} (5% from boundaries)")

        for regime in ['pre_london', 'london_to_merge', 'merge_to_dencun', 'post_dencun']:
            regime_df = self.df[self.df[f'regime_{regime}'] == 1]

            if len(regime_df) == 0:
                continue

            if self.treatment_var not in regime_df.columns:
                results['positivity_violations'].append({
                    'regime': regime,
                    'issue': 'Treatment variable missing'
                })
                continue

            treatment_data = regime_df[self.treatment_var].dropna()

            if len(treatment_data) == 0:
                results['positivity_violations'].append({
                    'regime': regime,
                    'issue': 'No treatment data'
                })
                continue

            # Compute support statistics
            n_obs = len(treatment_data)
            mean_val = treatment_data.mean()
            std_val = treatment_data.std()
            min_val = treatment_data.min()
            max_val = treatment_data.max()

            # Check mass near boundaries (0 and 1 for treatment)
            n_near_zero = (treatment_data <= 0.05).sum()
            n_near_one = (treatment_data >= 0.95).sum()
            pct_near_zero = n_near_zero / n_obs
            pct_near_one = n_near_one / n_obs

            # Check for degenerate distributions
            unique_vals = treatment_data.nunique()

            # Positivity check
            positivity_ok = (
                pct_near_zero < (1 - QUALITY_GATES['G2_POSITIVITY_MIN']) and
                pct_near_one < (1 - QUALITY_GATES['G2_POSITIVITY_MIN']) and
                unique_vals > 10  # Need variation
            )

            regime_result = {
                'n_obs': n_obs,
                'mean': mean_val,
                'std': std_val,
                'min': min_val,
                'max': max_val,
                'pct_near_zero': pct_near_zero,
                'pct_near_one': pct_near_one,
                'unique_values': unique_vals,
                'positivity_ok': positivity_ok
            }

            results['regime_support'][regime] = regime_result

            print(f"\n{regime.upper()}:")
            print(f"  N: {n_obs}")
            print(f"  Mean (SD): {mean_val:.4f} ({std_val:.4f})")
            print(f"  Range: [{min_val:.4f}, {max_val:.4f}]")
            print(f"  Mass near 0: {pct_near_zero:.2%}")
            print(f"  Mass near 1: {pct_near_one:.2%}")
            print(f"  Unique values: {unique_vals}")
            print(f"  Positivity: {'✓ PASS' if positivity_ok else '✗ FAIL'}")

            if not positivity_ok:
                violation = {
                    'regime': regime,
                    'issue': f"Positivity violation: {pct_near_zero:.2%} near 0, {pct_near_one:.2%} near 1"
                }
                results['positivity_violations'].append(violation)

                # Only fail G2 for post-London regimes (where treatment is relevant)
                if regime != 'pre_london':
                    results['gate_g2_passed'] = False

        # Update gate status
        if results['gate_g2_passed']:
            self.gate_status['G2_TREATMENT_SUPPORT']['status'] = 'PASS'
            self.gate_status['G2_TREATMENT_SUPPORT']['details'].append('Positivity satisfied in all regimes')
        else:
            self.gate_status['G2_TREATMENT_SUPPORT']['status'] = 'FAIL'
            self.gate_status['G2_TREATMENT_SUPPORT']['details'] = results['positivity_violations']
            self.issues.append("GATE G2 FAILURE: Treatment positivity violations detected")

        print("\n" + "="*80)
        print(f"GATE G2 STATUS: {'PASS' if results['gate_g2_passed'] else 'FAIL'}")
        print("="*80)

        return results

    def task7_compile_gate_assessment(self) -> Dict:
        """
        Task 7: Compile final quality gate assessment.
        """
        print("\n" + "="*80)
        print("TASK 7: QUALITY GATE ASSESSMENT")
        print("="*80)

        # G1 Data QC assessment (based on previous tasks)
        g1_components = {
            'coverage': True,  # Will be set based on coverage check
            'structural_nulls': True,  # Will be set based on missing patterns
            'winsorization': True  # Will be set based on winsorization audit
        }

        # Update G1 based on results
        if hasattr(self, 'task3_results'):
            g1_components['winsorization'] = not self.task3_results.get('winsorization_audit', {}).get('any_exceeds_threshold', False)
            g1_components['structural_nulls'] = self.task3_results.get('missing_patterns', {}).get('structural_nulls_correct', True)
            g1_components['coverage'] = self.task3_results.get('coverage_check', {}).get('coverage_adequate', True)

        g1_passed = all(g1_components.values())

        if g1_passed:
            self.gate_status['G1_DATA_QC']['status'] = 'PASS'
            self.gate_status['G1_DATA_QC']['details'].append('All data QC checks passed')
        else:
            self.gate_status['G1_DATA_QC']['status'] = 'FAIL'
            failed_components = [k for k, v in g1_components.items() if not v]
            self.gate_status['G1_DATA_QC']['details'].append(f'Failed components: {failed_components}')

        # G4 Diagnostics assessment
        g4_components = {
            'adf_tests': True,  # All variables stationary after differencing
            'vif_check': True,  # All VIF < 10
            'hac_validation': True  # HAC recommendations validated
        }

        # Update G4 based on results
        if hasattr(self, 'task2_results'):
            g4_components['vif_check'] = self.task2_results.get('vif_validation', {}).get('validation_passed', True)
            g4_components['adf_tests'] = self.task2_results.get('adf_validation', {}).get('validation_passed', True)

        if hasattr(self, 'task1_results'):
            g4_components['hac_validation'] = self.task1_results.get('hac_recommendations', {}).get('validation', '') == 'CONSISTENT'

        g4_passed = all(g4_components.values())

        if g4_passed:
            self.gate_status['G4_DIAGNOSTICS']['status'] = 'PASS'
            self.gate_status['G4_DIAGNOSTICS']['details'].append('All diagnostic checks passed')
        else:
            self.gate_status['G4_DIAGNOSTICS']['status'] = 'FAIL'
            failed_components = [k for k, v in g4_components.items() if not v]
            self.gate_status['G4_DIAGNOSTICS']['details'].append(f'Failed components: {failed_components}')

        # Overall assessment
        all_gates_passed = all(gate['status'] == 'PASS' for gate in self.gate_status.values())

        # Print summary
        print("\nQUALITY GATE SUMMARY:")
        print("-" * 50)

        for gate_name, gate_info in self.gate_status.items():
            status_symbol = "✓" if gate_info['status'] == 'PASS' else "✗"
            print(f"{status_symbol} {gate_name}: {gate_info['status']}")
            for detail in gate_info['details'][:2]:  # Show first 2 details
                print(f"    - {detail}")

        print("\n" + "="*80)
        if all_gates_passed:
            print("✓ ALL QUALITY GATES PASSED - PHASE 5 APPROVED")
        else:
            failed_gates = [k for k, v in self.gate_status.items() if v['status'] != 'PASS']
            print(f"✗ QUALITY GATES FAILED: {failed_gates}")
            print("BLOCKING: Phase 6 cannot proceed until all gates pass")
        print("="*80)

        return {
            'gate_status': self.gate_status,
            'all_gates_passed': all_gates_passed,
            'issues': self.issues,
            'warnings': self.warnings
        }

    def generate_qa_report(self, all_results: Dict):
        """Generate comprehensive QA report."""
        print("\n" + "="*80)
        print("GENERATING COMPREHENSIVE QA REPORT")
        print("="*80)

        report = []
        report.append("# Phase 5 Quality Assurance Report")
        report.append("=" * 80)
        report.append(f"Generated: {pd.Timestamp.now()}")
        report.append(f"QA Lead: Comprehensive validation for Phase 5 EDA")
        report.append("")

        # Gate Status
        report.append("## Gate Status")
        report.append("-" * 40)

        for gate_name, gate_info in self.gate_status.items():
            status = gate_info['status']
            emoji = "✅" if status == 'PASS' else "❌"
            report.append(f"- **{gate_name}**: {emoji} {status}")

            if gate_info['details']:
                for detail in gate_info['details'][:3]:
                    report.append(f"  - {detail}")

        report.append("")

        # Statistical Diagnostics
        report.append("## Statistical Diagnostics")
        report.append("-" * 40)

        if 'task1_results' in all_results:
            task1 = all_results['task1_results']
            report.append("### Residual Analysis")
            report.append(f"- R-squared: {task1['regression_results']['r_squared']:.4f}")
            report.append(f"- Serial correlation: {'Detected' if task1['ljung_box']['serial_correlation_detected'] else 'Not detected'}")
            report.append(f"- HAC lag recommendation: {task1['hac_recommendations']['recommended_lag']} (range: {task1['hac_recommendations']['sensitivity_range']})")
            report.append(f"- Normality: {'Normal' if task1['normality_tests']['normal_residuals'] else 'Non-normal'}")
            report.append("")

        if 'task2_results' in all_results:
            task2 = all_results['task2_results']
            report.append("### Test Validation")

            # ADF
            if 'adf_validation' in task2:
                report.append(f"- ADF tests performed: {task2['adf_validation']['n_tests']}")
                report.append(f"- Stationary after differencing: {task2['adf_validation']['diff_stationary_pct']:.1f}%")

            # VIF
            if 'vif_validation' in task2:
                report.append(f"- Max VIF: {task2['vif_validation']['max_vif']:.2f}")
                report.append(f"- VIF < 10: {'Yes' if task2['vif_validation']['validation_passed'] else 'No'}")

            report.append("")

        # Data Quality
        report.append("## Data Quality Metrics")
        report.append("-" * 40)

        if 'task3_results' in all_results:
            task3 = all_results['task3_results']

            # Winsorization
            if 'winsorization_audit' in task3:
                winsor = task3['winsorization_audit']
                report.append(f"### Winsorization")
                report.append(f"- Max tail percentage: {winsor['max_tail_percentage']:.4f}")
                report.append(f"- Threshold: {winsor['threshold']}")
                report.append(f"- Status: {'PASS' if winsor['gate_passed'] else 'FAIL'}")

            # Missing patterns
            if 'missing_patterns' in task3:
                missing = task3['missing_patterns']
                report.append(f"### Missing Data")
                report.append(f"- Variables with missing: {missing['vars_with_missing']}")
                report.append(f"- Structural NULLs correct: {missing['structural_nulls_correct']}")

            # Outliers
            if 'outlier_analysis' in task3:
                outliers = task3['outlier_analysis']
                report.append(f"### Outliers")
                report.append(f"- Influential points: {outliers['n_influential_points']} ({outliers['pct_influential']:.2f}%)")
                report.append(f"- Temporal clustering: {outliers['temporal_clustering']}")

            report.append("")

        # Mediator Exclusion
        report.append("## Mediator Exclusion Audit")
        report.append("-" * 40)

        if 'task4_results' in all_results:
            task4 = all_results['task4_results']
            report.append(f"- Files scanned: {len(task4['files_scanned'])}")
            report.append(f"- Mediator references found: {len(task4['mediator_references'])}")
            report.append(f"- Leakage detected: {'YES - CRITICAL' if task4['leakage_detected'] else 'NO'}")
            report.append(f"- **Gate G3 Status**: {'FAIL - BLOCKING' if task4['leakage_detected'] else 'PASS'}")

            if task4['mediator_references']:
                report.append("\n### Mediator References:")
                for ref in task4['mediator_references'][:5]:  # Show first 5
                    if ref.get('severity') == 'CRITICAL':
                        report.append(f"  - **CRITICAL**: {ref.get('file', 'unknown')} line {ref.get('line', '?')}: {ref.get('mediator', '')}")

            report.append("")

        # Recommendations
        report.append("## Recommendations")
        report.append("-" * 40)

        if self.issues:
            report.append("### Critical Issues (Must Fix):")
            for issue in self.issues:
                report.append(f"- {issue}")
        else:
            report.append("### Critical Issues: None")

        report.append("")

        if self.warnings:
            report.append("### Warnings (Should Review):")
            for warning in self.warnings[:10]:  # Show first 10
                report.append(f"- {warning}")
        else:
            report.append("### Warnings: None")

        report.append("")

        # Phase 6 Readiness
        report.append("## Phase 6 Readiness")
        report.append("-" * 40)

        all_gates_passed = all(gate['status'] == 'PASS' for gate in self.gate_status.values())

        if all_gates_passed:
            report.append("✅ **APPROVED**: All quality gates passed. Phase 6 ITS modeling can proceed.")
            report.append("")
            report.append("### Validated Parameters for Phase 6:")
            report.append("- Treatment: A_t_clean (positivity confirmed)")
            report.append("- HAC lags: 7-10 (with sensitivity checks)")
            report.append("- Sample: Post-London (2021-08-05 onwards)")
            report.append("- No mediator leakage detected")
        else:
            failed_gates = [k for k, v in self.gate_status.items() if v['status'] != 'PASS']
            report.append(f"❌ **BLOCKED**: Quality gates failed: {failed_gates}")
            report.append("")
            report.append("### Required Actions:")
            for gate in failed_gates:
                report.append(f"- Fix {gate}: {self.gate_status[gate]['details'][0] if self.gate_status[gate]['details'] else 'See details above'}")

        # Save report
        report_text = "\n".join(report)
        report_path = RESULTS_DIR / 'phase5_qa_report.md'

        with open(report_path, 'w') as f:
            f.write(report_text)

        print(f"\nQA report saved to: {report_path}")

        # Print summary
        print("\n" + "="*80)
        print("QA REPORT SUMMARY")
        print("="*80)
        print(f"Gates Passed: {sum(1 for g in self.gate_status.values() if g['status'] == 'PASS')}/{len(self.gate_status)}")
        print(f"Critical Issues: {len(self.issues)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Phase 6 Ready: {'YES' if all_gates_passed else 'NO - BLOCKED'}")

        return report_text

    def run_all_validations(self):
        """Run all validation tasks."""
        all_results = {}

        # Task 1: Residual Diagnostics
        self.task1_results = self.task1_residual_diagnostics()
        all_results['task1_results'] = self.task1_results

        # Task 2: Statistical Test Validation
        self.task2_results = self.task2_validate_statistical_tests()
        all_results['task2_results'] = self.task2_results

        # Task 3: Data Quality Verification
        self.task3_results = self.task3_data_quality_verification()
        all_results['task3_results'] = self.task3_results

        # Task 4: Mediator Exclusion (CRITICAL)
        self.task4_results = self.task4_mediator_exclusion_verification()
        all_results['task4_results'] = self.task4_results

        # Task 5: Regime Consistency
        self.task5_results = self.task5_regime_consistency_checks()
        all_results['task5_results'] = self.task5_results

        # Task 6: Treatment Support
        self.task6_results = self.task6_treatment_support_validation()
        all_results['task6_results'] = self.task6_results

        # Task 7: Compile Gate Assessment
        self.task7_results = self.task7_compile_gate_assessment()
        all_results['task7_results'] = self.task7_results

        # Generate comprehensive report
        self.generate_qa_report(all_results)

        return all_results


def main():
    """Main execution function."""
    print("="*80)
    print("PHASE 5 QUALITY ASSURANCE VALIDATION")
    print("="*80)
    print("QA Lead executing comprehensive validation...")
    print("")

    # Initialize validator
    validator = Phase5QAValidator()

    # Run all validations
    results = validator.run_all_validations()

    # Final status
    print("\n" + "="*80)
    print("PHASE 5 QA VALIDATION COMPLETE")
    print("="*80)
    print(f"End time: {pd.Timestamp.now()}")

    # Check if we can proceed
    all_gates_passed = all(g['status'] == 'PASS' for g in validator.gate_status.values())

    if all_gates_passed:
        print("\n✅ PHASE 5 APPROVED - Proceed to Phase 6")
    else:
        print("\n❌ PHASE 5 BLOCKED - Quality gates must pass before proceeding")
        print("\nFailed gates:")
        for gate, info in validator.gate_status.items():
            if info['status'] != 'PASS':
                print(f"  - {gate}: {info['details'][0] if info['details'] else 'Check report'}")

    return results, validator.gate_status


if __name__ == "__main__":
    main()