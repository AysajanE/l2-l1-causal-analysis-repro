#!/usr/bin/env python3
"""
Generate a compact 2x2 welfare sensitivity grid combining:
- Baseline percentile: 5th vs 25th (relative to the 10th percentile baseline)
- Price weighting: mean (gas-time-weighted proxy) vs daily close

This script derives the 2x2 grid from existing audited artifacts:
- results/bsts/welfare_baseline_sensitivity.csv (provides scaling ratios for p05/p25)
- results/bsts/welfare_bridge_summary.json (provides price scenario totals at p10)

Outputs:
- results/bsts/welfare_sensitivity_2x2.csv
- results/bsts/table_welfare_sensitivity_2x2.tex

Method: For each adoption percentile P in {p05, p25} and price scenario S in {mean, close},
we scale the p10 welfare total under S by the adoption scaling ratio for P from
welfare_baseline_sensitivity.csv. This matches the manuscript’s stated approach
(interpolation diagnostic; no BSTS refit).
"""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(".")
RESULTS_DIR = PROJECT_ROOT / "results" / "bsts"


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load inputs
    baseline_sens_csv = RESULTS_DIR / "welfare_baseline_sensitivity.csv"
    summary_json = RESULTS_DIR / "welfare_bridge_summary.json"

    if not baseline_sens_csv.exists():
        raise FileNotFoundError(f"Missing {baseline_sens_csv}")
    if not summary_json.exists():
        raise FileNotFoundError(f"Missing {summary_json}")

    baseline_df = pd.read_csv(baseline_sens_csv)
    with open(summary_json, "r") as f:
        summary = json.load(f)

    # Days analyzed for daily average
    days_analyzed = int(summary.get("window_analysis", {}).get("days_analyzed", 137))

    # Price scenarios at p10 (baseline)
    price_scenarios = summary.get("price_scenarios", {})
    if not price_scenarios:
        raise ValueError("price_scenarios missing in welfare_bridge_summary.json")

    # Extract required p10 totals for scenarios we will include
    # We choose 'mean' and 'close' for the 2x2 grid (baseline in manuscript uses gas-time-weighted;
    # mean approximates that series closely in our bundle.)
    required_price_keys = ["mean", "close"]
    p10_totals = {}
    for key in required_price_keys:
        ps = price_scenarios.get(key)
        if not ps:
            raise KeyError(f"Price scenario '{key}' not found in summary")
        p10_totals[key] = {
            "base_only": float(ps.get("base_only")),
            "base_plus_tip": float(ps.get("base_plus_tip")),
        }

    # Get adoption scaling ratios for p05 and p25 relative to p10
    # Expect columns: percentile_label (p05/p10/p25), scaling_ratio_mean
    scale_map = (
        baseline_df.set_index("percentile_label")["scaling_ratio_mean"].to_dict()
    )
    if not {"p05", "p25"}.issubset(scale_map.keys()):
        raise KeyError("Expected percentile labels p05 and p25 in baseline sensitivity CSV")

    adopt_share_map = (
        baseline_df.set_index("percentile_label")["adoption_percentile_pct"].to_dict()
    )

    rows = []
    for perc_label in ["p05", "p25"]:
        scale = float(scale_map[perc_label])
        adopt_pct = float(adopt_share_map.get(perc_label, float("nan")))
        for price_key in required_price_keys:
            base_p10 = p10_totals[price_key]["base_only"]
            tip_p10 = p10_totals[price_key]["base_plus_tip"]

            total_base = base_p10 * scale
            total_tip = tip_p10 * scale

            rows.append(
                {
                    "baseline_percentile": perc_label,
                    "adoption_share_pct": adopt_pct,
                    "price_scenario": price_key,
                    "total_base_usd": total_base,
                    "total_base_plus_tip_usd": total_tip,
                    "daily_avg_base_usd": total_base / days_analyzed,
                    "daily_avg_base_plus_tip_usd": total_tip / days_analyzed,
                    "days": days_analyzed,
                }
            )

    out_df = pd.DataFrame(rows)
    out_csv = RESULTS_DIR / "welfare_sensitivity_2x2.csv"
    out_df.to_csv(out_csv, index=False)

    # Emit a compact LaTeX table (2 rows × 2 cols) with values as "Base / Base+Tip"
    # Columns: Baseline (with adoption %), Mean price, Daily close price
    # Note: We round to 1 decimal for millions and 2 decimals for daily millions to match manuscript style
    def fmt_millions(v: float) -> str:
        return f"{v/1e6:,.1f}"

    # Build row strings for p05 and p25
    def row_for(perc_label: str) -> str:
        adopt_pct = out_df[out_df.baseline_percentile == perc_label][
            "adoption_share_pct"
        ].iloc[0]
        # mean
        r_mean = out_df[(out_df.baseline_percentile == perc_label) & (out_df.price_scenario == "mean")].iloc[0]
        mean_cell = f"{fmt_millions(r_mean['total_base_usd'])} / {fmt_millions(r_mean['total_base_plus_tip_usd'])}"
        # close
        r_close = out_df[(out_df.baseline_percentile == perc_label) & (out_df.price_scenario == "close")].iloc[0]
        close_cell = f"{fmt_millions(r_close['total_base_usd'])} / {fmt_millions(r_close['total_base_plus_tip_usd'])}"
        return f"{perc_label} ({adopt_pct:.1f}\\%) & {mean_cell} & {close_cell} \\" 

    tex_lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\small",
        "\\caption{Two-by-Two Welfare Sensitivity (Baseline Percentile $\\times$ Price Weighting)}",
        "\\label{tab:welfare_sensitivity_2x2}",
        "\\begin{tabular}{lcc}",
        "\\hline",
        "Baseline (Adoption) & Mean Price (Base / Base+Tip, $M$) & Close Price (Base / Base+Tip, $M$) \\",
        "\\hline",
        row_for("p05"),
        row_for("p25"),
        "\\hline",
        "\\multicolumn{3}{l}{\\textit{Note:} Values in millions of USD over the 137-day window. No BSTS refit; adoption-only scaling.}\\\\",
        "\\multicolumn{3}{r}{\\footnotesize\\textcolor{gray}{Data: results/bsts/* | Code: src/analysis/08c_welfare_sensitivity_2x2.py}}\\\\[-0.3ex]",
        "\\hline",
        "\\end{tabular}",
        "\\end{table}",
        "",
    ]

    tex_path = RESULTS_DIR / "table_welfare_sensitivity_2x2.tex"
    tex_path.write_text("\n".join(tex_lines))

    print(f"Wrote 2x2 sensitivity grid to: {out_csv}")
    print(f"Wrote LaTeX table to: {tex_path}")


if __name__ == "__main__":
    main()
