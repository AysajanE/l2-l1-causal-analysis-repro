#!/usr/bin/env python3
"""
Plot post-Dencun slope estimates with 95% CIs at daily vs weekly frequency,
and the interaction difference, to visually communicate power changes.
"""
from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Ensure the project root is on sys.path so that `src` and
# `project_A_effects` packages can be imported when this script is
# invoked as a standalone module.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visualization.plot_config import (  # type: ignore[import]
    FIGURE_SIZES,
    FONT_SIZES,
    save_figure,
    set_publication_style,
)


POWER_CSV = PROJECT_ROOT / "results" / "power" / "table_i5_power_precision.csv"
OUT_DIR = PROJECT_ROOT / "results" / "power"


def main() -> None:
    """
    Generate Management Science–compatible power/precision figure for
    post-Dencun slopes and interactions.
    """
    # Ensure consistent publication style (fonts, DPI, colors)
    set_publication_style(dpi=300, use_latex=False)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(POWER_CSV)

    # Expect rows with Specification in {Interaction Δβ (post vs. pre), Post-Dencun slope}
    keep = df[df["Specification"].isin(["Interaction Δβ (post vs. pre)", "Post-Dencun slope"])].copy()

    # Build labels combining frequency
    keep["label"] = keep.apply(
        lambda r: ("Interaction Δβ" if "Interaction" in r["Specification"] else "Post-Dencun")
        + f" ({r['Frequency']})",
        axis=1,
    )

    # Compute 95% CI in beta units
    z = 1.96
    keep["ci_low"] = keep["$\\hat{\\beta}$"] - z * keep["HAC SE"]
    keep["ci_high"] = keep["$\\hat{\\beta}$"] + z * keep["HAC SE"]

    # Layout: single-column width, compact height for appendix placement
    single_width, single_height = FIGURE_SIZES["single"]
    fig_height = single_height * 0.9
    fig, ax = plt.subplots(figsize=(single_width, fig_height))

    y = np.arange(len(keep))
    ax.errorbar(
        x=keep["$\\hat{\\beta}$"],
        y=y,
        xerr=z * keep["HAC SE"],
        fmt="o",
        color="#1f77b4",
        ecolor="#1f77b4",
        elinewidth=1.2,
        capsize=3,
    )

    ax.axvline(0, color="#999999", linestyle="--", linewidth=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels(keep["label"].tolist(), fontsize=FONT_SIZES["small"])
    ax.set_xlabel(r"$\hat{\beta}$ with 95\% CI (log-point units)", fontsize=FONT_SIZES["normal"])

    # No in-figure title; caption in LaTeX carries the descriptive text
    fig.tight_layout()

    out_base = OUT_DIR / "fig_power_post_dencun"
    save_figure(fig, str(out_base), formats=["pdf", "png"], dpi=300)
    print(f"Wrote: {out_base}.pdf")


if __name__ == "__main__":
    main()
