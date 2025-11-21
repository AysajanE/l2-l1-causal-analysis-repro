#!/usr/bin/env python3
"""
Local Post-Dencun Identification (Referee Concern MC-2)
=======================================================

Implements a local post-Dencun identification strategy by estimating a
weighted local-linear slope of congestion outcomes on L2 adoption within the
observed post-Dencun support window [0.86, 0.91]. We use a triangular kernel
centered at a0 = 0.885 and report HAC-robust confidence intervals. We also
report partial-identification bounds for 5pp and 10pp adoption changes under a
monotone non-positivity sign restriction (i.e., short-run slope ≤ 0), which is
consistent with the ECM short-run findings and the congestion-relief mechanism.

Outputs
-------
  - results/local_postdencun/table_local_linear_bounds.csv / .tex
  - figures/positivity/local_linear_window.pdf

Notes
-----
  - Uses the frozen core panel (daily), post-London sample.
  - Restricts estimation to post-Dencun observations with A_t ∈ [0.86, 0.91].
  - Controls match the confirmatory levels specification: D★, is_weekend,
    is_month_end. This ensures consistency with the manuscript estimand.
  - HAC covariance uses Bartlett kernel; maxlags=7 for daily series.
  - Partial identification bounds assume slope ≤ 0 (monotone short-run relief).
    The 95% lower bound for β provides a conservative lower endpoint; the upper
    endpoint is 0 (weak sign restriction), producing an identification region
    for the semi-elasticity mapping.
"""

from __future__ import annotations

import sys

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from project_A_effects.visualization.utils.provenance import ProvenanceFooter  # noqa: E402
from project_A_effects.visualization.utils.theme import (  # noqa: E402
    set_publication_theme,
    save_figure,
    get_figure_size,
)
from src.utils.parquet_loader import load_parquet_with_date_handling  # noqa: E402


DATA_PATH = PROJECT_ROOT / "data" / "core_panel_v1" / "core_panel_v1.parquet"
RESULTS_DIR = PROJECT_ROOT / "results" / "local_postdencun"
FIG_DIR = PROJECT_ROOT / "figures" / "positivity"

LONDON = pd.Timestamp("2021-08-05")
MERGE = pd.Timestamp("2022-09-15")
DENCUN = pd.Timestamp("2024-03-13")

# Local window configuration
SUPPORT_LOW = 0.86
SUPPORT_HIGH = 0.91
A0 = 0.5 * (SUPPORT_LOW + SUPPORT_HIGH)  # 0.885 center
H = (SUPPORT_HIGH - SUPPORT_LOW) / 2.0   # bandwidth half-width = 0.025


def ensure_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_data() -> pd.DataFrame:
    df = load_parquet_with_date_handling(DATA_PATH)
    df = df[df["date"] >= LONDON].sort_values("date").reset_index(drop=True)
    # Controls to align with confirmatory levels spec
    if "is_weekend" not in df.columns:
        df["is_weekend"] = (df["date"].dt.dayofweek >= 5).astype(int)
    if "is_month_end" not in df.columns:
        df["is_month_end"] = df["date"].dt.is_month_end.astype(int)
    # Basic coercions
    for col in ["log_base_fee", "A_t_clean", "D_star", "u_t", "S_t"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["log_base_fee", "A_t_clean", "D_star"])  # primary outcome present


def triangular_kernel(u: np.ndarray) -> np.ndarray:
    w = np.clip(1.0 - np.abs(u), 0.0, None)
    return w


def design_matrix(df: pd.DataFrame, a0: float) -> Tuple[pd.DataFrame, pd.Series]:
    X = pd.DataFrame({
        "const": 1.0,
        "A_centered": df["A_t_clean"] - a0,
        "D_star": df["D_star"],
        "is_weekend": df["is_weekend"],
        "is_month_end": df["is_month_end"],
    })
    y = df["log_base_fee"]
    return X, y


@dataclass
class LocalResult:
    beta: float
    se: float
    ci_low: float
    ci_high: float
    n: int
    n_eff: float
    semi_10pp: float
    semi_10pp_ci: Tuple[float, float]
    bounds_5pp: Tuple[float, float]
    bounds_10pp: Tuple[float, float]


def effective_sample_size(series: pd.Series, max_lag: int = 7) -> float:
    s = pd.Series(series).dropna()
    N = s.shape[0]
    if N == 0:
        return np.nan
    denom = 1.0
    for h in range(1, min(max_lag, N - 1) + 1):
        rho = s.autocorr(lag=h)
        if np.isnan(rho):
            continue
        denom += 2 * rho * (1 - h / N)
    if denom <= 0:
        return float(N)
    return N / denom


def fit_local_linear(df: pd.DataFrame, a0: float, h: float) -> LocalResult:
    # Restrict to window and compute weights
    window = df[(df["A_t_clean"] >= (a0 - h)) & (df["A_t_clean"] <= (a0 + h))].copy()
    if window.empty:
        raise ValueError("No observations in the specified local window.")

    u = (window["A_t_clean"] - a0) / h
    w = triangular_kernel(u.values)

    X, y = design_matrix(window, a0)

    # Weighted least squares, then HAC on the weighted fit
    wls = sm.WLS(y, X, weights=w)
    res = wls.fit()
    hac = res.get_robustcov_results(cov_type="HAC", maxlags=7)

    # Extract slope on centered A
    try:
        idx = list(res.params.index).index("A_centered")
    except Exception:
        # Fallback by name on HAC wrapper
        idx = list(hac.params.index).index("A_centered")

    beta = float(hac.params[idx])
    se = float(hac.bse[idx])
    ci_low = beta - 1.96 * se
    ci_high = beta + 1.96 * se

    # Semi-elasticity mapping for 10pp
    semi_10pp = (np.exp(0.10 * beta) - 1.0) * 100.0
    semi_10pp_ci = (
        (np.exp(0.10 * ci_low) - 1.0) * 100.0,
        (np.exp(0.10 * ci_high) - 1.0) * 100.0,
    )

    # Partial identification bounds under β ≤ 0 (monotone non-positivity)
    beta_lower95 = ci_low
    beta_upper_restricted = 0.0
    def effect_bounds(delta: float) -> Tuple[float, float]:
        lower = (np.exp(delta * beta_lower95) - 1.0) * 100.0
        upper = (np.exp(delta * beta_upper_restricted) - 1.0) * 100.0
        return (lower, upper)

    n_eff = effective_sample_size(hac.resid.squeeze(), max_lag=7)

    return LocalResult(
        beta=beta,
        se=se,
        ci_low=ci_low,
        ci_high=ci_high,
        n=int(window.shape[0]),
        n_eff=float(n_eff),
        semi_10pp=semi_10pp,
        semi_10pp_ci=semi_10pp_ci,
        bounds_5pp=effect_bounds(0.05),
        bounds_10pp=effect_bounds(0.10),
    )


def bandwidth_sensitivity(df: pd.DataFrame, a0: float, h_list: Tuple[float, ...]) -> pd.DataFrame:
    rows = []
    for h in h_list:
        try:
            local = fit_local_linear(df, a0, h)
        except Exception:
            continue
        rows.append({
            "Bandwidth h": h,
            r"$\hat{\beta}$": local.beta,
            "HAC SE": local.se,
            "95% CI": f"[{local.ci_low:.3f}, {local.ci_high:.3f}]",
            "N (window)": local.n,
            r"$N_{\text{eff}}$": f"{local.n_eff:.1f}",
            "Semi (10pp)": f"{local.semi_10pp:.2f}\\%",
        })
    return pd.DataFrame(rows)


def save_sensitivity_table(df: pd.DataFrame) -> None:
    footer = ProvenanceFooter()
    csv_path = RESULTS_DIR / "table_local_bandwidth_sensitivity.csv"
    tex_path = RESULTS_DIR / "table_local_bandwidth_sensitivity.tex"
    df.to_csv(csv_path, index=False)
    # Escape header percents
    df.rename(columns={"95% CI": "95\\% CI"}, inplace=True)
    latex = footer.add_to_dataframe_latex(
        df,
        index=False,
        caption=(
            "Local post-Dencun bandwidth sensitivity (triangular kernel, centered at $A=0.885$). "
            "HAC SEs use Bartlett kernel with 7 lags."
        ),
        label="tab:local_postdencun_bw",
        float_format="%.4f",
        escape=False,
    )
    with open(tex_path, "w") as f:
        f.write(latex)


def save_table(local: LocalResult) -> None:
    # Build a compact table with local slope and partial-ID bounds
    rows: Dict[str, Dict[str, object]] = {}
    rows["Local slope (β at A=0.885)"] = {
        "Estimate": local.beta,
        "HAC SE": local.se,
        "95% CI": f"[{local.ci_low:.3f}, {local.ci_high:.3f}]",
        "Semi (10pp)": f"{local.semi_10pp:.2f}\\%",
        "Semi 95% CI": f"[{local.semi_10pp_ci[0]:.1f}\\%, {local.semi_10pp_ci[1]:.1f}\\%]",
        "N (window)": local.n,
        r"$N_{\text{eff}}$": f"{local.n_eff:.1f}",
    }
    # If 95% CI is entirely > 0, the (β ≤ 0) restriction is incompatible at 95%.
    # Encode this as an empty identification set at 95% under the sign restriction.
    if local.ci_low > 0:
        bound_5pp_str = "$\\emptyset$ ($\\beta\\le 0$ rejected at 95\\%)"
        bound_10pp_str = "$\\emptyset$ ($\\beta\\le 0$ rejected at 95\\%)"
    else:
        bound_5pp_str = f"[{local.bounds_5pp[0]:.1f}\\%, {local.bounds_5pp[1]:.1f}\\%]"
        bound_10pp_str = f"[{local.bounds_10pp[0]:.1f}\\%, {local.bounds_10pp[1]:.1f}\\%]"

    rows["Partial-ID bound ($\\Delta A=5\\,\\mathrm{pp}$)"] = {
        "Estimate": np.nan,
        "HAC SE": np.nan,
        "95% CI": "--",
        "Semi (10pp)": "--",
        "Semi 95% CI": "--",
        "N (window)": "--",
        r"$N_{\text{eff}}$": "--",
        "Bound %": bound_5pp_str,
    }
    rows["Partial-ID bound ($\\Delta A=10\\,\\mathrm{pp}$)"] = {
        "Estimate": np.nan,
        "HAC SE": np.nan,
        "95% CI": "--",
        "Semi (10pp)": "--",
        "Semi 95% CI": "--",
        "N (window)": "--",
        r"$N_{\text{eff}}$": "--",
        "Bound %": bound_10pp_str,
    }

    df = pd.DataFrame.from_dict(rows, orient="index").reset_index().rename(columns={"index": "Quantity"})
    # Escape percent signs in headers for LaTeX
    df.rename(
        columns={
            "95% CI": "95\\% CI",
            "Semi 95% CI": "Semi 95\\% CI",
            "Bound %": "Bound \\%",
        },
        inplace=True,
    )

    footer = ProvenanceFooter()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = RESULTS_DIR / "table_local_linear_bounds.csv"
    tex_path = RESULTS_DIR / "table_local_linear_bounds.tex"

    df.to_csv(csv_path, index=False)

    latex = footer.add_to_dataframe_latex(
        df,
        index=False,
        caption=(
            "Local Post-Dencun Slope and Partial-Identification Bounds. "
            "Local-linear estimate within $A_t \in [0.86,0.91]$ (triangular kernel, "
            "$h=0.025$, centered at $A=0.885$) with Bartlett HAC SEs (7 lags). "
            "Bounds impose a weak sign restriction ($\\beta \le 0$)."
        ),
        label="tab:local_postdencun",
        float_format="%.4f",
        escape=False,
    )
    with open(tex_path, "w") as f:
        f.write(latex)


def plot_local_fit(df: pd.DataFrame, local: LocalResult) -> None:
    import matplotlib.pyplot as plt

    # Apply publication theme for Management Science-style figures
    set_publication_theme()

    # Restrict and compute partial residuals in-window for a simple visualization
    window = df[(df["A_t_clean"] >= (A0 - H)) & (df["A_t_clean"] <= (A0 + H))].copy()
    X, y = design_matrix(window, A0)
    # Unweighted OLS to obtain partial residuals for visualization only
    ols = sm.OLS(y, X).fit()
    beta = ols.params["A_centered"]
    partial = ols.resid + beta * (window["A_t_clean"] - A0)

    fig, ax = plt.subplots(figsize=get_figure_size("single"))
    ax.scatter(window["A_t_clean"], partial, s=18, alpha=0.4, color="#d62728", edgecolor="none")
    # Draw local-linear line through the window using the estimated HAC β
    a_grid = np.linspace(A0 - H, A0 + H, 50)
    y_line = local.beta * (a_grid - A0) + np.median(partial)
    ax.plot(a_grid, y_line, color="#aa0000", linewidth=2.0, label="Local linear fit")
    ax.axvline(A0, color="gray", linestyle="--", linewidth=1)
    ax.set_xlabel("L2 adoption share ($A_t$)")
    ax.set_ylabel("Partial residual of log base fee")
    ax.set_title("Local Post-Dencun Fit within [0.86, 0.91]")
    ax.legend(loc="best", frameon=False)
    ax.grid(alpha=0.2)

    fig.tight_layout()
    out_base = FIG_DIR / "local_linear_window"
    save_figure(fig, str(out_base), formats=["pdf", "png"], include_provenance=False)
    plt.close(fig)


def main() -> None:
    ensure_dirs()
    df = load_data()
    post = df[df["date"] >= DENCUN].copy()

    local = fit_local_linear(post, A0, H)
    save_table(local)
    plot_local_fit(post, local)

    # Bandwidth sensitivity across narrower windows inside [0.86, 0.91]
    bw_df = bandwidth_sensitivity(post, A0, h_list=(0.015, 0.020, 0.025))
    if not bw_df.empty:
        save_sensitivity_table(bw_df)

    print(
        "✓ Local post-Dencun slope estimated (A∈[0.86,0.91]). "
        f"β={local.beta:.3f}, SE={local.se:.3f}, N={local.n}, N_eff={local.n_eff:.1f}"
    )


if __name__ == "__main__":
    main()
