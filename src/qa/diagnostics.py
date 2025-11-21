"""
QA Diagnostics Utilities

This module provides statistical diagnostic functions for quality gate validation.

Functions support:
- Time series diagnostics (ACF/PACF, stationarity tests)
- Regression diagnostics (VIF, influence measures)
- Residual analysis
- Outlier detection
- NULL pattern analysis

Used by: tests/gates/test_g4_diagnostics.py and other QA checks
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from scipy import stats
from scipy.stats import norm, chi2
import warnings


# ============================================================================
# Time Series Diagnostics
# ============================================================================

def compute_acf(
    x: Union[np.ndarray, pd.Series],
    nlags: int = 40,
    fft: bool = True
) -> np.ndarray:
    """
    Compute autocorrelation function (ACF).

    Args:
        x: Time series data
        nlags: Number of lags to compute
        fft: Use FFT for computation (faster for long series)

    Returns:
        Array of ACF values for lags 0 to nlags

    Note:
        ACF at lag 0 is always 1.0
    """
    if isinstance(x, pd.Series):
        x = x.values

    # Demean
    x = x - x.mean()
    n = len(x)

    if fft:
        # FFT-based computation (faster)
        # Pad with zeros to avoid circular correlation
        nfft = 2 ** int(np.ceil(np.log2(2 * n)))
        xfft = np.fft.fft(x, n=nfft)
        acf = np.fft.ifft(xfft * np.conj(xfft)).real[:n]
        acf = acf / acf[0]
    else:
        # Direct computation
        c0 = np.dot(x, x) / n
        acf = np.array([1.0] + [
            np.dot(x[:-k], x[k:]) / (n * c0)
            for k in range(1, min(nlags + 1, n))
        ])

    return acf[:nlags + 1]


def compute_pacf(
    x: Union[np.ndarray, pd.Series],
    nlags: int = 40,
    method: str = "ywunbiased"
) -> np.ndarray:
    """
    Compute partial autocorrelation function (PACF).

    Args:
        x: Time series data
        nlags: Number of lags to compute
        method: Method for computation ('ywunbiased', 'ols', 'ld')

    Returns:
        Array of PACF values for lags 0 to nlags

    Note:
        PACF at lag 0 is always 1.0
    """
    if isinstance(x, pd.Series):
        x = x.values

    x = x - x.mean()

    if method == "ywunbiased":
        # Yule-Walker equations with unbiased ACF estimates
        acf_vals = compute_acf(x, nlags=nlags, fft=True)
        pacf = np.zeros(nlags + 1)
        pacf[0] = 1.0

        for k in range(1, nlags + 1):
            if k == 1:
                pacf[k] = acf_vals[1]
            else:
                # Solve Yule-Walker equations
                R = np.array([[acf_vals[abs(i - j)] for j in range(k)] for i in range(k)])
                r = acf_vals[1:k + 1]
                try:
                    phi = np.linalg.solve(R, r)
                    pacf[k] = phi[-1]
                except np.linalg.LinAlgError:
                    pacf[k] = np.nan

    elif method == "ols":
        # OLS regression method
        pacf = np.zeros(nlags + 1)
        pacf[0] = 1.0

        for k in range(1, min(nlags + 1, len(x))):
            # Regress x[k:] on x[k-1:n-1], ..., x[0:n-k]
            # PACF is the coefficient on x[0:n-k]
            y = x[k:]
            X = np.column_stack([x[i:len(x) - k + i] for i in range(k)])

            if len(y) < k + 1:
                pacf[k] = np.nan
                continue

            try:
                beta = np.linalg.lstsq(X, y, rcond=None)[0]
                pacf[k] = beta[-1]
            except np.linalg.LinAlgError:
                pacf[k] = np.nan

    else:
        raise ValueError(f"Unknown PACF method: {method}")

    return pacf


def adf_test(
    x: Union[np.ndarray, pd.Series],
    maxlag: Optional[int] = None,
    regression: str = "c"
) -> Dict[str, float]:
    """
    Augmented Dickey-Fuller test for stationarity.

    Args:
        x: Time series data
        maxlag: Maximum lag to include in test regression
        regression: Type of regression ('c': constant, 'ct': constant+trend, 'nc': no constant)

    Returns:
        Dict with test statistic, p-value, critical values, and decision

    Note:
        H0: Series has a unit root (non-stationary)
        H1: Series is stationary
        Reject H0 if p-value < 0.05
    """
    try:
        from statsmodels.tsa.stattools import adfuller

        if isinstance(x, pd.Series):
            x = x.values

        # Remove NaNs
        x = x[~np.isnan(x)]

        result = adfuller(x, maxlag=maxlag, regression=regression)

        return {
            "test_statistic": result[0],
            "p_value": result[1],
            "n_lags": result[2],
            "n_obs": result[3],
            "critical_values": result[4],
            "stationary": result[1] < 0.05,  # Reject unit root at 5% level
        }

    except ImportError:
        warnings.warn("statsmodels not available, using simplified ADF test")
        # Simplified Dickey-Fuller (no augmentation)
        return _simple_df_test(x, regression)


def _simple_df_test(x: np.ndarray, regression: str = "c") -> Dict[str, float]:
    """
    Simplified Dickey-Fuller test (no augmentation).

    This is a fallback if statsmodels is not available.
    """
    n = len(x)
    y = np.diff(x)
    x_lag = x[:-1]

    # Build design matrix
    if regression == "c":
        X = np.column_stack([np.ones(n - 1), x_lag])
    elif regression == "ct":
        X = np.column_stack([np.ones(n - 1), np.arange(n - 1), x_lag])
    elif regression == "nc":
        X = x_lag.reshape(-1, 1)
    else:
        raise ValueError(f"Unknown regression type: {regression}")

    # OLS regression
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    residuals = y - X @ beta
    se = np.sqrt(np.sum(residuals ** 2) / (n - 1 - X.shape[1]))

    # Test statistic for coefficient on x_lag
    rho_coef = beta[-1]
    # SE calculation (simplified)
    X_var = np.var(x_lag)
    se_rho = se / np.sqrt(n * X_var)
    t_stat = rho_coef / se_rho

    # Approximate critical values (from MacKinnon 1994)
    critical_values = {"1%": -3.43, "5%": -2.86, "10%": -2.57}

    # Very rough p-value approximation
    if t_stat < critical_values["1%"]:
        p_value = 0.001
    elif t_stat < critical_values["5%"]:
        p_value = 0.03
    elif t_stat < critical_values["10%"]:
        p_value = 0.08
    else:
        p_value = 0.15

    return {
        "test_statistic": t_stat,
        "p_value": p_value,
        "n_lags": 0,
        "n_obs": n - 1,
        "critical_values": critical_values,
        "stationary": p_value < 0.05,
    }


def ljung_box_test(
    residuals: Union[np.ndarray, pd.Series],
    lags: int = 10
) -> Dict[str, float]:
    """
    Ljung-Box Q-test for residual autocorrelation.

    Args:
        residuals: Residual series
        lags: Number of lags to test

    Returns:
        Dict with Q statistic, p-value, and decision

    Note:
        H0: No autocorrelation up to lag K
        H1: Autocorrelation present
        Reject H0 if p-value < 0.05
    """
    if isinstance(residuals, pd.Series):
        residuals = residuals.values

    n = len(residuals)
    acf_vals = compute_acf(residuals, nlags=lags)[1:]  # Exclude lag 0

    # Ljung-Box statistic
    Q = n * (n + 2) * np.sum(acf_vals ** 2 / (n - np.arange(1, lags + 1)))

    # Chi-square test with lags degrees of freedom
    p_value = 1 - chi2.cdf(Q, lags)

    return {
        "Q_statistic": Q,
        "p_value": p_value,
        "lags": lags,
        "autocorrelated": p_value < 0.05,
    }


# ============================================================================
# Regression Diagnostics
# ============================================================================

def compute_vif(X: pd.DataFrame, exclude_cols: Optional[List[str]] = None) -> pd.Series:
    """
    Compute Variance Inflation Factor (VIF) for each variable.

    Args:
        X: Design matrix (DataFrame)
        exclude_cols: Columns to exclude from VIF computation (e.g., 'intercept')

    Returns:
        Series mapping variable names to VIF values

    Note:
        VIF_j = 1 / (1 - R²_j)
        where R²_j is from regressing X_j on all other X variables
        Rule of thumb: VIF > 10 indicates problematic multicollinearity
    """
    if exclude_cols is None:
        exclude_cols = ["intercept", "const"]

    # Drop excluded columns
    X = X.copy()
    for col in exclude_cols:
        if col in X.columns:
            X = X.drop(columns=col)

    vif_data = {}

    for col in X.columns:
        # Regress X[col] on all other columns
        y = X[col]
        X_others = X.drop(columns=col)

        if X_others.shape[1] == 0:
            # No other variables
            vif_data[col] = 1.0
            continue

        # OLS regression
        try:
            beta = np.linalg.lstsq(X_others.values, y.values, rcond=None)[0]
            y_pred = X_others.values @ beta
            ss_res = np.sum((y.values - y_pred) ** 2)
            ss_tot = np.sum((y.values - y.mean()) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            # VIF
            if r_squared >= 1.0:
                vif = np.inf
            else:
                vif = 1.0 / (1.0 - r_squared)

            vif_data[col] = vif

        except np.linalg.LinAlgError:
            vif_data[col] = np.inf

    return pd.Series(vif_data)


def compute_cooks_d(
    X: np.ndarray,
    y: np.ndarray,
    residuals: np.ndarray
) -> np.ndarray:
    """
    Compute Cook's distance for each observation.

    Args:
        X: Design matrix (n x p)
        y: Response variable (n,)
        residuals: OLS residuals (n,)

    Returns:
        Array of Cook's D values (n,)

    Note:
        D_i = (e_i^2 / (p * MSE)) * (h_ii / (1 - h_ii)^2)
        where h_ii is leverage (diagonal of hat matrix)
        Rule of thumb: D_i > 4/n indicates influential observation
    """
    n, p = X.shape

    # Hat matrix diagonal (leverage)
    try:
        H = X @ np.linalg.inv(X.T @ X) @ X.T
        leverage = np.diag(H)
    except np.linalg.LinAlgError:
        # Singular matrix, use pseudo-inverse
        H = X @ np.linalg.pinv(X.T @ X) @ X.T
        leverage = np.diag(H)

    # MSE (mean squared error)
    mse = np.sum(residuals ** 2) / (n - p)

    # Cook's D
    cooks_d = (residuals ** 2 / (p * mse)) * (leverage / (1 - leverage) ** 2)

    return cooks_d


def compute_dfbetas(
    X: np.ndarray,
    residuals: np.ndarray,
    var_covar_matrix: np.ndarray
) -> np.ndarray:
    """
    Compute DFBETAS for each observation and coefficient.

    Args:
        X: Design matrix (n x p)
        residuals: OLS residuals (n,)
        var_covar_matrix: Variance-covariance matrix of coefficients (p x p)

    Returns:
        Array of DFBETAS (n x p)

    Note:
        DFBETAS_ji = (β_j - β_j(-i)) / SE(β_j)
        Measures change in coefficient j when observation i is deleted
        Rule of thumb: |DFBETAS| > 2/sqrt(n) indicates influential observation
    """
    n, p = X.shape

    # Hat matrix
    try:
        H = X @ np.linalg.inv(X.T @ X) @ X.T
    except np.linalg.LinAlgError:
        H = X @ np.linalg.pinv(X.T @ X) @ X.T

    leverage = np.diag(H)

    # DFBETAS matrix (n x p)
    dfbetas = np.zeros((n, p))

    # Standard errors
    se = np.sqrt(np.diag(var_covar_matrix))

    for i in range(n):
        # Studentized residual
        stud_res = residuals[i] / np.sqrt(1 - leverage[i]) if leverage[i] < 1 else 0

        # DFBETAS for observation i
        for j in range(p):
            dfbetas[i, j] = (stud_res * np.sqrt(var_covar_matrix[j, j]) * X[i, j]) / se[j]

    return dfbetas


def compute_leverage(X: np.ndarray) -> np.ndarray:
    """
    Compute leverage values (hat values).

    Args:
        X: Design matrix (n x p)

    Returns:
        Array of leverage values (n,)

    Note:
        h_i = X_i' (X'X)^-1 X_i (diagonal of hat matrix)
        Rule of thumb: h_i > 2p/n or 3p/n indicates high leverage
    """
    try:
        H = X @ np.linalg.inv(X.T @ X) @ X.T
    except np.linalg.LinAlgError:
        H = X @ np.linalg.pinv(X.T @ X) @ X.T

    return np.diag(H)


# ============================================================================
# Outlier Detection
# ============================================================================

def detect_outliers_iqr(
    x: Union[np.ndarray, pd.Series],
    multiplier: float = 1.5
) -> Dict[str, any]:
    """
    Detect outliers using IQR method.

    Args:
        x: Data series
        multiplier: IQR multiplier (1.5 for outliers, 3.0 for extreme outliers)

    Returns:
        Dict with outlier indices, bounds, and counts
    """
    if isinstance(x, pd.Series):
        x_vals = x.values
    else:
        x_vals = x

    q1 = np.percentile(x_vals, 25)
    q3 = np.percentile(x_vals, 75)
    iqr = q3 - q1

    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr

    outlier_mask = (x_vals < lower_bound) | (x_vals > upper_bound)
    outlier_indices = np.where(outlier_mask)[0]

    return {
        "n_outliers": len(outlier_indices),
        "outlier_indices": outlier_indices.tolist(),
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
    }


def detect_outliers_zscore(
    x: Union[np.ndarray, pd.Series],
    threshold: float = 3.0
) -> Dict[str, any]:
    """
    Detect outliers using Z-score method.

    Args:
        x: Data series
        threshold: Z-score threshold (typically 3.0)

    Returns:
        Dict with outlier indices, z-scores, and counts
    """
    if isinstance(x, pd.Series):
        x_vals = x.values
    else:
        x_vals = x

    mean = np.mean(x_vals)
    std = np.std(x_vals)

    z_scores = np.abs((x_vals - mean) / std) if std > 0 else np.zeros_like(x_vals)

    outlier_mask = z_scores > threshold
    outlier_indices = np.where(outlier_mask)[0]

    return {
        "n_outliers": len(outlier_indices),
        "outlier_indices": outlier_indices.tolist(),
        "z_scores": z_scores.tolist(),
        "threshold": threshold,
        "mean": mean,
        "std": std,
    }


# ============================================================================
# NULL Pattern Analysis
# ============================================================================

def analyze_null_patterns(
    df: pd.DataFrame,
    date_col: str = "date",
    regime_cols: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Analyze NULL patterns in DataFrame.

    Args:
        df: DataFrame to analyze
        date_col: Name of date column
        regime_cols: List of regime indicator columns

    Returns:
        DataFrame with NULL counts and patterns by regime
    """
    null_summary = []

    for col in df.columns:
        if col == date_col:
            continue

        null_count = df[col].isna().sum()
        null_pct = null_count / len(df)

        row = {
            "variable": col,
            "null_count": null_count,
            "null_pct": null_pct,
        }

        # Regime-specific NULL patterns
        if regime_cols:
            for regime_col in regime_cols:
                if regime_col in df.columns:
                    regime_data = df[df[regime_col]]
                    regime_nulls = regime_data[col].isna().sum()
                    regime_total = len(regime_data)
                    regime_null_pct = regime_nulls / regime_total if regime_total > 0 else 0

                    row[f"{regime_col}_null_count"] = regime_nulls
                    row[f"{regime_col}_null_pct"] = regime_null_pct

        null_summary.append(row)

    return pd.DataFrame(null_summary)


def check_structural_nulls(
    df: pd.DataFrame,
    variable: str,
    expected_null_condition: pd.Series
) -> Dict[str, int]:
    """
    Check if NULLs match expected structural pattern.

    Args:
        df: DataFrame
        variable: Variable to check
        expected_null_condition: Boolean series indicating where NULLs are expected

    Returns:
        Dict with counts of expected/unexpected NULLs
    """
    is_null = df[variable].isna()

    return {
        "expected_nulls": (is_null & expected_null_condition).sum(),
        "unexpected_nulls": (is_null & ~expected_null_condition).sum(),
        "expected_values": (~is_null & ~expected_null_condition).sum(),
        "missing_values": (~is_null & expected_null_condition).sum(),
    }
