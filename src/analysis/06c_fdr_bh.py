#!/usr/bin/env python3
"""
Compute Benjamini–Hochberg (BH) FDR q-values for the confirmatory outcome family
and export a compact table for manuscript inclusion.

Confirmatory family:
- Log base fee (log C^fee) — main FGLS/Prais–Winsten spec
- Log scarcity (log S_t) — main FGLS spec

Inputs:
- results/its_levels/table3_comprehensive.csv (for base-fee β, SE, p-value)
- project_A_effects/manuscript/sections/04_results_table3_levels_update.tex (for scarcity β, SE)

Outputs:
- results/fdr/fdr_confirmatory_bh.csv
- results/fdr/table_c9_fdr_bh.tex

Notes:
- If a p-value is not directly available (scarcity), compute two-tailed p from β/SE
  using a large-sample normal approximation.
"""

from __future__ import annotations

from pathlib import Path
import re
import math
import pandas as pd
from scipy.stats import norm


PROJECT_ROOT = Path(".")


def load_base_fee_row(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path)
    # Expect a row with FGLS / Prais–Winsten
    row = df[df["Specification"].str.contains("FGLS", na=False)].iloc[0]
    beta_str = str(row["β (A_t)"]) if "β (A_t)" in df.columns else str(row.get("Coefficient", ""))
    se_str = str(row["SE"]) if "SE" in df.columns else str(row.get("StdErr", ""))
    p_str = str(row["P-value"]) if "P-value" in df.columns else str(row.get("pvalue", ""))

    # Parse numeric beta, se
    beta = float(str(beta_str).replace("***", "").replace("**", "").replace("*", "").strip())
    se = float(str(se_str).replace("(", "").replace(")", "").strip())
    # Clean p-value; handle strings like "<0.001" or "0.000"
    try:
        pval = float(p_str)
    except Exception:
        m = re.search(r"([0-9.]+)", p_str)
        if m:
            pval = float(m.group(1))
        else:
            pval = float("nan")
    # If p-value is missing or reported as 0.000, compute from z
    if not (pval > 0):
        z = abs(beta / se)
        pval = 2 * (1 - norm.cdf(z))

    return {
        "outcome": "log_C_fee",
        "label": "$\\log C^{\\mathrm{fee}}$",
        "beta": beta,
        "se": se,
        "pval": pval,
        "source": str(csv_path),
    }


def load_scarcity_from_tex(tex_path: Path) -> dict:
    # Find line like: Scarcity ($\log S_t$) & $-0.062$ & (0.019) & ...
    text = tex_path.read_text()
    m = re.search(r"Scarcity .*?\$\s*([\-0-9.]+)\s*\$\s*&\s*\(([-0-9.]+)\)", text)
    if not m:
        # Alternate pattern: numbers without $ delimiters
        m = re.search(r"Scarcity .*?&\s*([-0-9.]+)\s*&\s*\(([-0-9.]+)\)", text)
    if not m:
        raise RuntimeError("Could not parse Scarcity row from tex file")
    beta = float(m.group(1))
    se = float(m.group(2))
    z = abs(beta / se)
    pval = 2 * (1 - norm.cdf(z))
    return {
        "outcome": "log_S_t",
        "label": "$\\log S_{t}$",
        "beta": beta,
        "se": se,
        "pval": pval,
        "source": str(tex_path),
    }


def bh_adjust(pvals: list[float]) -> list[float]:
    m = len(pvals)
    # Pair p with original index
    indexed = list(enumerate(pvals))
    sorted_pairs = sorted(indexed, key=lambda x: x[1])
    qvals = [0.0] * m
    # Compute raw BH
    for rank, (idx, p) in enumerate(sorted_pairs, start=1):
        qvals[idx] = p * m / rank
    # Enforce monotonicity (non-decreasing when sorted by p)
    # Work from largest p to smallest
    min_so_far = math.inf
    for rank_rev, (idx, p) in enumerate(reversed(sorted_pairs), start=1):
        q = qvals[idx]
        if q < min_so_far:
            min_so_far = q
        else:
            q = min_so_far
        qvals[idx] = min(q, 1.0)
    # Cap at 1
    qvals = [min(1.0, q) for q in qvals]
    return qvals


def format_sci(x: float) -> str:
    if x == 0:
        return "0"
    # Use engineering-style for very small values
    if x < 1e-3:
        return f"{x:.1e}"
    return f"{x:.4f}"


def main() -> None:
    base_path = PROJECT_ROOT / "results" / "its_levels" / "table3_comprehensive.csv"
    scarcity_tex = PROJECT_ROOT / "project_A_effects" / "manuscript" / "sections" / "04_results_table3_levels_update.tex"

    if not base_path.exists():
        raise FileNotFoundError(f"Missing {base_path}")
    if not scarcity_tex.exists():
        raise FileNotFoundError(f"Missing {scarcity_tex}")

    base_row = load_base_fee_row(base_path)
    scarcity_row = load_scarcity_from_tex(scarcity_tex)
    rows = [base_row, scarcity_row]

    df = pd.DataFrame(rows)
    qvals = bh_adjust(df["pval"].tolist())
    df["qval"] = qvals

    out_dir = PROJECT_ROOT / "results" / "fdr"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "fdr_confirmatory_bh.csv"
    df.to_csv(csv_path, index=False)

    # TeX table
    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\small",
        "\\caption{Confirmatory Outcomes: BH FDR-Adjusted q-values}",
        "\\label{tab:c9_fdr_bh}",
        "\\begin{tabular}{lcccc}",
        "\\hline",
        "Outcome & $\\beta$ & SE & $p$ & $q$ (BH) \\\\ ",
        "\\hline",
    ]
    for _, r in df.iterrows():
        lines.append(
            f"{r['label']} & {r['beta']:.3f} & {r['se']:.3f} & {format_sci(r['pval'])} & {format_sci(r['qval'])} \\")
    lines += [
        "\\hline",
        "\\multicolumn{5}{l}{\\textit{Note:} Benjamini--Hochberg adjustment over the confirmatory family ($\\log C^{fee}$, $\\log S_t$). Exploratory outcomes are unadjusted.}\\\\",
        "\\multicolumn{5}{r}{\\footnotesize\\textcolor{gray}{Data: results/its_levels/* | Code: src/analysis/06c_fdr_bh.py}}\\\\[-0.3ex]",
        "\\hline",
        "\\end{tabular}",
        "\\end{table}",
        "",
    ]
    tex_path = out_dir / "table_c9_fdr_bh.tex"
    tex_path.write_text("\n".join(lines))

    print(f"Wrote: {csv_path}")
    print(f"Wrote: {tex_path}")


if __name__ == "__main__":
    main()
