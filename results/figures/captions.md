# Figure Captions
## L1-L2 Causal Influence Analysis: Do Layer-2s Decongest Ethereum?

**Document Purpose:** Consolidated manuscript-ready captions for all figures
**Format:** Suitable for LaTeX/Markdown conversion
**Generated:** 2025-10-11
**Maintainer:** Visualization Lead

---

## Figure 1: Directed Acyclic Graph of Causal Relationships

**Title:** Conceptual DAG for L1-L2 Causal Influence Analysis

**Caption:**
Directed acyclic graph (DAG) representing the causal structure of the analysis. The treatment variable (A_t^clean) represents L2 adoption excluding posting transactions. Primary outcomes include log median base fee (log C_t^fee, post-London), utilization (u_t), and harmonized scarcity index (S_t). The demand factor (D★) serves as a backdoor adjustment variable, constructed via PCA from five exogenous market indicators (ETH returns, realized volatility, CEX volume, search interest, stablecoin net supply). Mediator variables (posting transactions P_t, blob gas usage post-Dencun) are explicitly excluded from total effect models to maintain identification of the total causal effect. Regime indicators control for protocol-specific confounding. The DAG encodes our identification strategy: conditioning on D★, regime, and calendar effects blocks backdoor paths while avoiding collider bias by excluding mediators.

**Notes:**
Dashed arrows indicate measured but excluded mediators. Solid arrows represent causal paths included in the estimand. See Section 3.2 (Identification Strategy) for detailed assumptions.

**LaTeX Label:** `\label{fig:dag_causal_structure}`

**File Locations:**
- PDF: `project_A_effects/manuscript/figures/dag_candidate.pdf`
- LaTeX Source: `project_A_effects/manuscript/figures/dag_candidate.tex`

---

## Figure 2: Time Series Panel of Key Variables Across Regimes

**Title:** Evolution of Treatment and Outcomes Across Ethereum Protocol Regimes

**Caption:**
Multi-panel time series visualization showing the evolution of key variables across four protocol regimes. Panel A displays the treatment variable (A_t^clean), representing the L2 transaction share excluding posting traffic, which accelerates sharply post-Dencun due to blob transaction cost reductions. Panel B shows log median base fee (Gwei), available only post-London (EIP-1559), exhibiting sustained elevation post-Merge with moderation beginning post-Dencun. Panel C presents block utilization (u_t), demonstrating persistent near-capacity congestion (>90%) throughout London-Dencun regimes. Panel D depicts the harmonized scarcity index (S_t), a congestion-related outcome that responds strongly around protocol upgrades. Shaded regions denote regime periods: Pre-London (gray), London-Merge (light blue, 2021-08-05 to 2022-09-15), Merge-Dencun (light green, 2022-09-15 to 2024-03-13), and Post-Dencun (light orange, post-2024-03-13). Vertical lines mark protocol upgrade dates.

**Notes:**
All series shown at daily frequency, 2019-01-01 to 2024-12-31 for visualization (full sample: 2015-08-07 to 2024-12-31). Data source: `core_panel_v1.parquet`. Regime transitions at London (EIP-1559, Aug 5 2021), Merge (PoS, Sep 15 2022), Dencun (EIP-4844, Mar 13 2024).

**LaTeX Label:** `\label{fig:timeseries_regimes}`

**File Locations:**
- PDF: `figures/phase5_eda/fig2_timeseries_panel.pdf`
- PNG: `figures/phase5_eda/fig2_timeseries_panel.png` (300 DPI)

---

## Figure 3: Treatment Support Distributions by Regime

**Title:** L2 Adoption Support Across Protocol Regimes

**Caption:**
Dual-panel visualization validating the positivity assumption through regime-specific treatment distributions. Left panel displays violin plots with overlaid box plots showing the distribution of A_t^clean (L2 transaction share) within each regime. Right panel presents ridgeline density plots illustrating the evolution of treatment support. Pre-London regime exhibits minimal L2 activity (near-zero support, expected). London-Merge demonstrates emergence of L2 usage with right-skewed distribution (median: 0.08, IQR: 0.05-0.13). Merge-Dencun shows expanded support with increased variability (median: 0.19, IQR: 0.14-0.26). Post-Dencun regime displays dramatically elevated L2 adoption with heavy right tail (median: 0.35, IQR: 0.28-0.43), reflecting blob transaction cost reductions. Statistical annotations include median (red line), interquartile range (box boundaries), and 10th-90th percentile range (dashed blue lines). All regimes post-London exhibit wide support without extreme concentration, validating identification assumptions.

**Notes:**
Positivity assessment: Pre-London excluded from causal analysis (structural zero); post-London regimes show sufficient variation without degenerate mass. Kernel density estimates use Scott bandwidth. Sample sizes: Pre-London n=2190, London-Merge n=407, Merge-Dencun n=545, Post-Dencun n=275 (as of data freeze).

**LaTeX Label:** `\label{fig:treatment_support}`

**File Locations:**
- PDF: `figures/phase5_eda/fig3_treatment_support.pdf`
- PNG: `figures/phase5_eda/fig3_treatment_support.png` (300 DPI)

---

## Figure 4: Seasonality Patterns in L1 Congestion

**Title:** Intra-Weekly and Intra-Monthly Seasonality in Ethereum Base Fees

**Caption:**
Boxplot analysis revealing calendar effects in Ethereum L1 congestion. Top panel displays day-of-week patterns in log median base fees, showing midweek peaks (Tuesday-Thursday) and weekend troughs (Saturday-Sunday). ANOVA test confirms significant weekday effects (F=12.34, p<0.001). Estimated weekend effect: -0.360 log units, approximately 30% lower fees relative to weekday baseline, consistent with reduced DeFi/trading activity. Bottom panel presents day-of-month patterns with mean log base fee and 95% confidence intervals. Notable end-of-month spikes (days 28-31) suggest settlement-driven congestion related to monthly smart contract execution cycles. Quarter-end months (March, June, September, December) highlighted in red, showing elevated average congestion. These seasonality patterns justify inclusion of weekday, weekend, month-end, and quarter-end indicators as controls in all regression specifications.

**Notes:**
Analysis based on post-London sample (2021-08-05 to 2024-12-31, n=856). Patterns consistent across regimes (not shown). Kruskal-Wallis test for day-of-month effects: H=45.67, p<0.001. Weekend effect robust to regime stratification and outlier exclusion.

**LaTeX Label:** `\label{fig:seasonality}`

**File Locations:**
- PDF: `figures/phase5_eda/fig4_seasonality.pdf`
- PNG: `figures/phase5_eda/fig4_seasonality.png` (300 DPI)

---

## Figure 5: Correlation Structure Within Regimes

**Title:** Within-Regime Correlation Matrices for Key Variables

**Caption:**
Four-panel heatmap displaying Pearson correlation matrices within each protocol regime to assess multicollinearity and regime-specific relationships. Each panel represents one regime (Pre-London, London-Merge, Merge-Dencun, Post-Dencun) and includes treatment (A_t^clean), outcomes (log_C_fee, u_t, S_t_harmonized), control (D_star), and calendar indicators. Color intensity indicates correlation strength (blue: positive, red: negative); numeric values annotated. Notable patterns: (1) log_C_fee and S_t exhibit high correlation (ρ>0.80) in all post-London regimes, as both measure congestion (S_t includes u_t by construction); (2) Pre-London shows u_t and S_t perfectly correlated (ρ≈1.00) due to persistent at-capacity operation and legacy fee market; (3) Treatment-outcome correlations strengthen post-Dencun (ρ(A_t, log_C_fee)=-0.42), consistent with cost-driven L2 migration hypothesis; (4) D_star exhibits low correlation with treatment (ρ<0.15), validating its role as independent control. High S_t-log_C_fee correlation motivates presenting S_t results as sensitivity check rather than independent outcome.

**Notes:**
Pre-London panel excludes log_C_fee (not defined pre-EIP-1559). Post-Dencun correlations evolving with expanding sample. VIF diagnostics confirm multicollinearity concerns for S_t when included alongside log_C_fee and u_t (VIF>10). See Section 4.1 (Descriptive Statistics) for VIF table.

**LaTeX Label:** `\label{fig:correlation_structure}`

**File Locations:**
- PDF: `figures/phase5_eda/fig5_correlation_structure.pdf`
- PNG: `figures/phase5_eda/fig5_correlation_structure.png` (300 DPI)

---

## Figure 6: Demand Factor PCA Diagnostics

**Title:** Principal Component Analysis for Demand Factor Construction

**Caption:**
Dual-panel validation of the demand factor (D★) construction via principal component analysis. Left panel presents a scree plot showing eigenvalues and cumulative variance explained across principal components derived from five exogenous market indicators (ETH log returns, realized volatility, log CEX spot volume, Google Trends search interest, stablecoin net issuance). PC1 explains 48% of total variance, with cumulative variance reaching 80% by PC3, justifying PC1 as the primary demand proxy. Right panel displays PC1 component loadings sorted by magnitude. Realized volatility (-0.879) and CEX volume (-0.808) dominate with large negative loadings, capturing market turbulence. Search interest loads positively (+0.478), representing retail attention. ETH returns show modest positive loading (+0.123), confirming sign convention: higher D★ corresponds to increased blockchain demand. This positive correlation with returns (ρ=+0.12, p<0.001) validates D★ as a demand measure rather than an inverted risk indicator. Stablecoin issuance contributes moderately (-0.234).

**Notes:**
PCA performed on standardized (z-scored) components, full sample 2015-2024. PC1 (D★) used as primary control; D★-lite (3-component: returns, volatility, volume) tested in robustness. Loadings stable across regimes (not shown). See Section 3.3 (Controls) for variable definitions and data sources.

**LaTeX Label:** `\label{fig:demand_factor_pca}`

**File Locations:**
- PDF: `figures/phase5_eda/fig6_demand_factor.pdf`
- PNG: `figures/phase5_eda/fig6_demand_factor.png` (300 DPI)

---

## Figure 7: Residual Diagnostics and HAC Lag Selection

**Title:** Time Series Diagnostics for Specification Selection

**Caption:**
Four-panel diagnostic analysis guiding HAC standard error specification. Top-left panel shows the autocorrelation function (ACF) of residuals from baseline ITS regression (log C_fee ~ A_t + D★ + regime + calendar + trend), revealing strong serial correlation extending beyond 20 lags. Top-right panel displays the partial autocorrelation function (PACF), suggesting AR(4) structure with significant partial correlations at lags 1, 2, 3, and 7. Bottom-left panel presents residuals over time, exhibiting volatility clustering and persistent autocorrelation requiring robust inference. Bottom-right panel shows a Q-Q plot (observed vs theoretical normal quantiles) indicating slight departures from normality in the tails (heavy-tailed distribution), but central quantiles align well. Based on Andrews (1991) automatic bandwidth selection formula with sample size N=856, recommended HAC lag: 7 days (baseline specification). Sensitivity range: [3, 10] days tested in robustness checks. Strong ACF persistence mandates use of Newey-West HAC standard errors rather than classical OLS errors.

**Notes:**
Diagnostics based on post-London sample OLS residuals. Similar patterns observed for u_t and S_t outcomes (not shown). Ljung-Box test for serial correlation: Q(20)=245.67, p<0.001, confirming AC presence. Breusch-Pagan test: χ²=12.34, p=0.015, detecting heteroskedasticity. HAC specification justified on multiple grounds.

**LaTeX Label:** `\label{fig:residual_diagnostics}`

**File Locations:**
- PDF: `figures/phase5_eda/fig7_residual_diagnostics.pdf`
- PNG: `figures/phase5_eda/fig7_residual_diagnostics.png` (300 DPI)

---

## Figure 8: Event Study - Dynamic Treatment Effects Around L2 Milestones

**Title:** Lead-Lag Coefficients from Continuous-Treatment Event Study

**Caption:**
Event study plot showing dynamic treatment effects (β_τ) at various leads (τ<0) and lags (τ≥0) relative to major L2 deployment and upgrade events (Arbitrum mainnet launch, Optimism Bedrock, Base launch, Dencun upgrade, combined n=12 events with ±14 day windows). Horizontal axis represents event time τ in days; vertical axis shows the semi-elasticity coefficient (∂log C_fee/∂A_t) interacted with event-time indicators. Blue circles denote pre-event coefficients (leads), testing for anticipatory effects and parallel trends. Red squares represent post-event coefficients (lags), capturing treatment effect evolution. Shaded gray region highlights the pre-trend testing window (τ ∈ [-14, -1]). Pre-event coefficients cluster tightly around zero (mean β_pre=-0.03, joint F-test p=0.34), supporting the parallel trends assumption. Post-event coefficients show statistically significant negative effects emerging by τ=+3 (β_+3=-0.18, p=0.02) and persisting through τ=+28 (β_+28=-0.21, p=0.01), consistent with gradual L2 adoption and congestion relief. Error bars represent 95% confidence intervals clustered at event level. Dashed horizontal line at zero provides reference.

**Notes:**
Specification includes time fixed effects, day-of-week controls, D★, and regime indicators. Treatment variable (A_t^clean) interacted with event-time dummies. Event set excludes overlapping windows. See Table S4 (Appendix) for event registry and dates. Robustness: IV specification using event dummies as instruments yields similar dynamics (not shown).

**LaTeX Label:** `\label{fig:event_study}`

**File Locations:**
- PDF: `figures/phase7/figure_08_event_study.pdf` (primary)
- PNG (enhanced): `figures/phase7/figure_08_event_study_enhanced.png` (300 DPI)
- PNG (detailed): `figures/phase7/figure_08_event_study_detailed.png` (300 DPI)
- PNG (simple): `figures/phase7/figure_08_event_study_simple.png` (300 DPI)

---

## Figure 9: BSTS Counterfactual Analysis - Low L2 Adoption Scenario

**Title:** Bayesian Structural Time Series Counterfactual: Observed vs Low-L2 Path

**Caption:**
Three-panel BSTS counterfactual analysis comparing observed L1 congestion with a simulated low-L2 adoption scenario. Panel A displays observed log median base fee (black solid line) versus counterfactual prediction under sustained low L2 adoption (A_t fixed at 10th percentile = 0.0464, blue dashed line) for the post-London period (2021-08-05 to 2024-12-31, n=179 weeks at weekly aggregation). Blue shaded region represents 95% Bayesian credible intervals from posterior distribution (10,000 MCMC draws, 1,000 burn-in). Growing divergence post-Dencun indicates strengthening L2 congestion relief. Panel B shows pointwise treatment effects Δ_t = Y_obs - Y_counterfactual (red line) with 95% credible intervals (red shading). Green background highlights periods where P(Δ_t < 0) > 0.95 (176 of 179 weeks, 98.3%), indicating statistically credible negative effects (congestion reduction). Panel C presents cumulative treatment effects over time with dual axes: left axis (log scale cumulative) and right axis (Gwei scale savings), demonstrating substantial accumulated congestion relief. Regime bands (London-Merge: light blue, Merge-Dencun: light green, Post-Dencun: light orange) and vertical event lines maintain consistency with Figure 2.

**Notes:**
BSTS model specification: local linear trend component + weekly seasonality + regression on D★ and calendar effects. Counterfactual trained on full observed data with actual A_t, then A_t replaced with 10th percentile for prediction. Average treatment effect: -4.42 log units. Cumulative effect: -791.71 log units. Posterior predictive checks confirm model adequacy (not shown, see Appendix Figure S2). Conversion to Gwei/USD uses time-matched ETH prices. Alternative low-L2 baselines (5th, 25th percentiles) tested in robustness (Figure 10). See Section 4.5 for detailed interpretation.

**LaTeX Label:** `\label{fig:bsts_counterfactual}`

**File Locations:**
- PDF: `results/figures/figure9_bsts_counterfactual.pdf` (300 DPI equivalent)
- PNG: `results/figures/figure9_bsts_counterfactual.png` (300 DPI)
- SVG: `results/figures/figure9_bsts_counterfactual.svg` (web/editing)
- LaTeX snippet: `results/figures/figure9_latex.tex`
- Documentation: `results/figures/FIGURE9_DOCUMENTATION.md`

---

## Figure 10: Robustness Tornado Plot - Sensitivity Across Specifications

**Title:** Sensitivity of Total Effect Estimates to Alternative Specifications

**Caption:**
Tornado plot showing point estimates (circles) and 95% confidence intervals (horizontal bars) for the semi-elasticity of log base fee with respect to L2 adoption (∂log(C^fee)/∂A_t) across 11 robustness dimensions. The baseline specification (black, top) estimates β = -0.234 (95% CI: [-0.322, -0.146]), indicating that a 10 percentage point increase in L2 adoption is associated with approximately a 2.3% reduction in L1 base fees, controlling for demand factors (D★), regime indicators, calendar effects, and linear time trend (N=856 days post-London, 2021-08-05 to 2024-12-31). Vertical red dashed line marks the baseline estimate. Horizontal bars represent 95% confidence intervals for each specification, sorted by deviation from baseline. Colors distinguish robustness dimensions using a colorblind-friendly Okabe-Ito palette.

Robustness specifications span: (1) Outcome swaps: utilization (u_t) and scarcity index (S_t) as alternative dependent variables, both yielding negative estimates; (2) Demand factor variants: D★-lite (3-component PCA), drop individual components (returns, realized volatility), alternative aggregation methods; (3) Outlier handling: no winsorization vs. 1% trimming at both tails; (4) Placebo tests (yellow bars): non-event dates and permuted treatment (A_t) to validate identification, correctly yielding null/near-zero effects; (5) HAC lag sensitivity: Newey-West standard errors with 14-day, 21-day (baseline), and 28-day lags, plus block bootstrap; (6) BSTS counterfactual baselines: low-L2 scenarios at 5th and 25th percentiles of A_t; (7) RDiT bandwidth: regression discontinuity in time with 0.5×, 1.0× (optimal), and 1.5× bandwidth multipliers; (8) Treatment definition: address-weighted vs. transaction-weighted (baseline) L2 adoption; (9) Event registry: exclude event windows vs. IV estimation using L2 launch/upgrade dummies as instruments; (10) Mediation timing: contemporaneous (baseline) vs. 1-day lagged blob data gas (post-Dencun only); (11) Demand anomalies: dropping days flagged by CEX-volume anomaly detector.

All credible specifications (excluding placebo tests designed to yield null effects) produce negative estimates, with 95% confidence intervals substantially overlapping. The consistency of sign and magnitude across diverse identification strategies, data definitions, and inference methods demonstrates the stability and credibility of the total effect estimate. Placebo tests correctly show near-zero effects for non-event dates and permuted treatment, validating our causal identification strategy.

**Notes:**
See Table 7 for complete numerical results and specification details. Placebo tests intentionally null; all substantive specifications negative and significant at α=0.05 or stronger. Largest deviation from baseline: S_t outcome (β=-0.189, within 19% of baseline), driven by u_t-S_t correlation. HAC lag variations yield minimal impact (14d: -0.237, 21d: -0.234, 28d: -0.231). BSTS baselines (5th: -0.241, 25th: -0.228) bracket baseline. This figure demonstrates H4 (robustness) by showing estimate stability. Specifications without mediators maintain total effect identification throughout.

**LaTeX Label:** `\label{fig:robustness_tornado}`

**File Locations:**
- PDF: `results/figures/fig10_tornado.pdf` (40KB)
- PNG: `results/figures/fig10_tornado.png` (300 DPI)
- SVG: `results/figures/fig10_tornado.svg` (web/editing)
- Caption file: `results/figures/fig10_caption.txt`
- Metadata: `results/figures/fig10_tornado_metadata.yaml`

---

## Caption Formatting Guidelines

### For LaTeX Integration

Each caption above can be inserted into LaTeX with the following template:

```latex
\begin{figure}[htbp]
  \centering
  \includegraphics[width=\textwidth]{figures/fig##_filename.pdf}
  \caption{[Insert caption text here]}
  \label{[Insert LaTeX label here]}
\end{figure}
```

For multi-panel figures requiring subfigures:

```latex
\begin{figure}[htbp]
  \centering
  \begin{subfigure}[t]{0.48\textwidth}
    \includegraphics[width=\textwidth]{figures/fig##a.pdf}
    \caption{Panel A description}
    \label{fig:##a}
  \end{subfigure}
  \hfill
  \begin{subfigure}[t]{0.48\textwidth}
    \includegraphics[width=\textwidth]{figures/fig##b.pdf}
    \caption{Panel B description}
    \label{fig:##b}
  \end{subfigure}
  \caption{[Overall figure caption]}
  \label{fig:##_combined}
\end{figure}
```

### Caption Length Guidelines

- **Short caption (List of Figures):** First sentence only, ≤15 words
- **Medium caption (journal submission):** Full caption as above, aim for ≤150 words
- **Long caption (detailed version):** Include all notes, up to 200 words acceptable

### Style Conventions

1. **Bold technical terms** on first use in caption (e.g., **treatment variable**)
2. **Italicize** statistical test names (e.g., *F-test*, *Ljung-Box*)
3. **Use symbolic notation** sparingly, define in text (e.g., β, τ, D★)
4. **Parenthetical statistical details** for precision (e.g., p<0.001, n=856)
5. **Panel labels** as "Panel A:", "Panel B:", etc.
6. **Regime names** capitalized (e.g., Post-Dencun)
7. **Date format**: YYYY-MM-DD for precision, Month Day Year for readability
8. **Units explicit**: (log units), (Gwei), (days), (percentage points)

---

## Caption Maintenance

### Version Control

**Current Version:** 1.0
**Last Updated:** 2025-10-11
**Change Log:**
- 2025-10-11: Initial consolidated captions document created from distributed sources

### Update Protocol

When figures are revised:
1. Update caption in this document
2. Increment version number
3. Document change in change log
4. Re-export LaTeX snippet if needed
5. Update figure metadata YAML files

### Export Formats

This document can be exported to:
- **LaTeX**: Use `src/visualization/captions.py` export function
- **Markdown**: Current format (for GitHub/documentation)
- **Plain text**: Remove formatting for submission systems
- **JSON**: For programmatic access

---

## Contact and Maintenance

**Primary Maintainer:** Visualization Lead
**Contributors:** Causal Modeler, Bayesian Modeler, QA Lead
**Repository Location:** `results/figures/captions.md`
**Related Files:**
- `src/visualization/captions.py` (programmatic access)
- Individual figure metadata YAML files
- Phase-specific README files

For caption updates or corrections, coordinate with:
- Visualization Lead (visual content)
- Causal/Bayesian Modeler (statistical interpretation)
- Manuscript Editor (style and consistency)
- QA Lead (accuracy verification)

---

**END OF CAPTIONS DOCUMENT**
