"""
Pre-EDA preflight checks

Ensures analysis readiness by:
- Ensuring the frozen panel snapshot exists locally (auto-extracts from tag panel/v1.0 if missing)
- Validating required columns and mediator exclusion
- Computing treatment support/positivity by regime
- Emitting a short memo and a ridgeline-style density plot

Outputs:
- results/phase5/positivity_memo.md
- results/figures/phase5/treatment_ridgeline_by_regime.png
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import List

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[2]
PANEL_PATH = REPO_ROOT / "data" / "analytical" / "core_panel_v1.parquet"
RESULTS_DIR = REPO_ROOT / "results" / "phase5"
FIG_DIR = REPO_ROOT / "results" / "figures" / "phase5"


def _git_has_tag(tag: str) -> bool:
    try:
        out = subprocess.check_output(["git", "tag", "-l", tag], cwd=REPO_ROOT).decode().strip()
        return out == tag
    except Exception:
        return False


def ensure_panel_snapshot() -> None:
    """Ensure data/core_panel_v1/core_panel_v1.parquet exists.

    If missing, attempt to extract from frozen tag panel/v1.0.
    """
    PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PANEL_PATH.exists():
        return

    if not _git_has_tag("panel/v1.0"):
        print("⚠️  panel/v1.0 tag not found; cannot auto-extract panel snapshot.")
        return

    try:
        # Extract blob from tag into the working tree
        blob_spec = "panel/v1.0:data/core_panel_v1/core_panel_v1.parquet"
        with open(PANEL_PATH, "wb") as f:
            subprocess.check_call(["git", "show", blob_spec], stdout=f, cwd=REPO_ROOT)
        print(f"✅ Extracted {PANEL_PATH} from tag panel/v1.0")
    except subprocess.CalledProcessError:
        print("❌ Failed to extract core_panel_v1.parquet from tag panel/v1.0")


def get_panel_schema_columns() -> List[str]:
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(PANEL_PATH)
    # Use Arrow schema names to avoid pandas metadata issues
    return list(pf.schema_arrow.names)


def load_panel_required_subset() -> pd.DataFrame:
    if not PANEL_PATH.exists():
        raise FileNotFoundError(f"Panel snapshot not found: {PANEL_PATH}. Run ensure_panel_snapshot first.")

    import pyarrow.parquet as pq  # lazy import

    # Columns we need for readiness + positivity
    preferred = [
        "date",
        "A_t_clean",
        "A_t",
        "D_star",
        "regime_post_london",
        "regime_post_merge",
        "regime_post_dencun",
        "weekday",
        "is_weekend",
        "log_base_fee",
        "C_fee",
        "S_t",
    ]
    schema_cols = get_panel_schema_columns()
    existing = [c for c in preferred if c in schema_cols]
    if not existing:
        raise ValueError("No expected columns found in panel schema.")

    # Read subset without pandas metadata and convert to Python lists
    table = pq.read_table(PANEL_PATH, columns=existing, use_pandas_metadata=False)
    data = {name: table.column(name).to_pylist() for name in existing}
    df = pd.DataFrame(data)

    # Normalize date dtype if present
    if "date" in df.columns:
        try:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        except Exception:
            pass
    return df


def validate_required_columns(schema_columns: List[str]) -> List[str]:
    """Return a list of issues found; empty means PASS."""
    issues: List[str] = []

    # Minimal required variables per plan
    required_any = [
        ("log_base_fee", ["log_base_fee", "C_fee", "S_t"]),
        ("treatment (A_t_clean)", ["A_t", "A_t_clean"]),
        ("D_star", ["D_star"]),
        ("regimes", ["regime_post_london", "regime_post_merge", "regime_post_dencun"]),
        ("calendar", ["weekday", "is_weekend"]),
    ]

    for label, candidates in required_any:
        if not any(c in schema_columns for c in candidates):
            issues.append(f"Missing required field: {label} (candidates: {candidates})")

    # Mediator exclusion for TE models (just check panel content)
    mediator_patterns = ["P_calldata", "P_blob", "posting_tx_count"]
    for col in schema_columns:
        for pat in mediator_patterns:
            if pat.lower() in col.lower():
                issues.append(f"Mediator present in panel snapshot: {col} (should be excluded for TE models)")
                break

    return issues


def compute_positivity_by_regime(df: pd.DataFrame) -> pd.DataFrame:
    # Determine treatment column (canonical: A_t_clean; warn if fallback)
    treat_col = None
    if "A_t_clean" in df.columns:
        treat_col = "A_t_clean"
    elif "A_t" in df.columns:
        treat_col = "A_t"
        print("⚠️  Using legacy 'A_t' column. Please migrate to 'A_t_clean' in panel export.")
    if treat_col is None:
        raise ValueError("No treatment column found (A_t or A_t_clean)")

    # Build regime bucket as in plan (London→Merge, Merge→Dencun, Post‑Dencun)
    if all(c in df.columns for c in ("regime_post_london", "regime_post_merge", "regime_post_dencun")):
        def regime_bucket(row):
            if row.get("regime_post_dencun", 0) == 1:
                return "post_dencun"
            if row.get("regime_post_merge", 0) == 1:
                return "merge_to_dencun"
            if row.get("regime_post_london", 0) == 1:
                return "london_to_merge"
            return "pre_london"
        rb = df.apply(regime_bucket, axis=1)
    else:
        rb = pd.Series(["all"] * len(df))

    d = pd.DataFrame({"regime": rb, treat_col: df[treat_col]})
    d = d.dropna()
    agg = d.groupby("regime")[treat_col].agg(["count", "min", "max", "mean", "median", lambda x: x.quantile(0.1), lambda x: x.quantile(0.9)])
    agg.columns = ["n", "min", "max", "mean", "median", "p10", "p90"]
    return agg.reset_index()


def plot_treatment_ridgeline(df: pd.DataFrame, outpath: Path) -> None:
    treat_col = "A_t_clean" if "A_t_clean" in df.columns else ("A_t" if "A_t" in df.columns else None)
    if treat_col is None:
        return

    if all(c in df.columns for c in ("regime_post_london", "regime_post_merge", "regime_post_dencun")):
        def regime_bucket(row):
            if row.get("regime_post_dencun", 0) == 1:
                return "post_dencun"
            if row.get("regime_post_merge", 0) == 1:
                return "merge_to_dencun"
            if row.get("regime_post_london", 0) == 1:
                return "london_to_merge"
            return "pre_london"
        df = df.copy()
        df["regime_bucket"] = df.apply(regime_bucket, axis=1)
    else:
        df = df.copy()
        df["regime_bucket"] = "all"

    # Create a simple layered density plot by regime (ridgeline-like)
    plt.figure(figsize=(9, 6))
    for i, regime in enumerate(df["regime_bucket"].unique()):
        sub = df[df["regime_bucket"] == regime]
        if sub.empty:
            continue
        sns.kdeplot(sub[treat_col], label=regime, fill=True, alpha=0.4)
    plt.xlim(0, 1)
    plt.xlabel(treat_col)
    plt.ylabel("Density")
    plt.title("Treatment support by regime")
    plt.legend(title="Regime")
    outpath.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close()


def write_memo(issues: List[str], positivity: pd.DataFrame, fig_path: Path) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    memo = RESULTS_DIR / "positivity_memo.md"
    with open(memo, "w") as f:
        f.write("# Phase 5 Readiness: Treatment Support & Preflight Checks\n\n")
        if issues:
            f.write("## Issues Detected\n")
            for it in issues:
                f.write(f"- {it}\n")
            f.write("\n")
        else:
            f.write("## Issues Detected\n- None (PASS)\n\n")

        f.write("## Treatment Positivity by Regime\n\n")
        # Write a simple pipe-delimited table to avoid optional deps
        cols = list(positivity.columns)
        f.write("| " + " | ".join(cols) + " |\n")
        f.write("|" + "|".join([" --- "] * len(cols)) + "|\n")
        for _, row in positivity.iterrows():
            f.write("| " + " | ".join(str(row[c]) for c in cols) + " |\n")
        f.write("\n")
        f.write("## Figure\n")
        f.write(f"Saved ridgeline: `{fig_path}`\n")

    print(f"📝 Wrote memo: {memo}")


def main() -> None:
    ensure_panel_snapshot()
    df = load_panel_required_subset()
    schema_cols = get_panel_schema_columns()
    issues = validate_required_columns(schema_cols)
    # If mediators are present, emit a sanitized TE view parquet without mediators for analysis phases
    mediator_patterns = ["P_calldata", "P_blob", "posting_tx_count"]
    mediators_present = any(any(pat.lower() in c.lower() for pat in mediator_patterns) for c in schema_cols)
    if mediators_present:
        try:
            import pyarrow.parquet as pq
            # Drop mediator columns
            te_cols = [c for c in schema_cols if not any(pat.lower() in c.lower() for pat in mediator_patterns)]
            table = pq.read_table(PANEL_PATH, columns=te_cols, use_pandas_metadata=False)
            te_view_path = REPO_ROOT / "data" / "analytical" / "core_panel_v1_teview.parquet"
            pq.write_table(table, te_view_path)
            print(f"✅ Created mediator-free TE view: {te_view_path}")
        except Exception as e:
            print(f"⚠️  Could not create TE view parquet: {e}")
    # Positivity
    positivity = compute_positivity_by_regime(df)
    # Plot
    fig_path = FIG_DIR / "treatment_ridgeline_by_regime.png"
    plot_treatment_ridgeline(df, fig_path)
    # Memo
    write_memo(issues, positivity, fig_path)
    # Console summary
    print("\n=== Pre-EDA Summary ===")
    print("Panel:", PANEL_PATH)
    print("Rows:", len(df))
    print("Columns:", len(df.columns))
    print("Issues:", "None" if not issues else f"{len(issues)} (see memo)")


if __name__ == "__main__":
    main()
