#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from project_A_effects.visualization.utils.theme import (  # type: ignore
    set_publication_theme,
    save_figure,
    get_figure_size,
)

IN_CSV = ROOT / "results" / "demand_factor" / "d_star_leave_one_out.csv"
OUT_DIR = ROOT / "figures" / "demand_factor"
VARIANT_DISPLAY = {
    "D★-lite": r"$D^{*}$-lite",
    "D★-full": r"$D^{*}$-full",
}


def plot_variant(ax: plt.Axes, df: pd.DataFrame, title: str) -> None:
    # Baseline rows are encoded with a missing dropped_component (NaN in CSV)
    base = df[df["dropped_component"].isna()].copy()
    comps = list(base["component"])
    x = np.arange(len(comps))

    # Baseline loadings
    ax.bar(x - 0.2, base["loading"].values, width=0.4, color="#1f77b4", label="Baseline")

    # Leave-one-out loadings for each dropped component (plot remaining comps)
    # Leave-one-out variants: all non-null dropped components
    drops = [d for d in df["dropped_component"].dropna().unique()]
    colors = ["#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    for i, drop in enumerate(drops):
        sub = df[df["dropped_component"] == drop].copy()
        # Align to full component list; missing (dropped) comp gets NaN
        y = []
        for c in comps:
            if c in list(sub["component"]):
                y.append(float(sub.loc[sub["component"] == c, "loading"].iloc[0]))
            else:
                y.append(np.nan)
        ax.scatter(x + 0.2, y, color=colors[i % len(colors)], label=f"drop {drop}", s=30)

    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_", "\\_") for c in comps], rotation=20, ha="right")
    ax.set_ylabel("PCA loading")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.2)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    set_publication_theme()
    df = pd.read_csv(IN_CSV)

    figsize = get_figure_size("double")
    fig, axes = plt.subplots(1, 2, figsize=figsize, constrained_layout=True)
    for ax, variant in zip(axes, ["D★-lite", "D★-full"]):
        sub = df[df["variant"] == variant]
        # Baseline EVR row: dropped_component is missing
        base_rows = sub.loc[sub["dropped_component"].isna(), "explained_variance"]
        if not base_rows.empty:
            evr = float(base_rows.iloc[0])
        else:
            # Fallback: use the first available EVR
            evr = float(sub["explained_variance"].iloc[0]) if not sub.empty else float("nan")
        display = VARIANT_DISPLAY.get(variant, variant)
        plot_variant(ax, sub, f"{display} (EVR={evr:.2f})")

    out_base = OUT_DIR / "leave_one_out_loadings"
    save_figure(fig, str(out_base), formats=["pdf", "png"], include_provenance=False)
    plt.close(fig)
    print(f"Saved LOO figure to {out_base.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
