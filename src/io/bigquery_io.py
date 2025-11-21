"""BigQuery I/O helpers (placeholders)."""
from typing import Any, Optional


def query(sql: str, params: Optional[dict[str, Any]] = None) -> "object":
    """Run a query and return a DataFrame (placeholder)."""
    raise NotImplementedError("Implement BigQuery client and return DataFrame")


def export_table(table: str, dest_path: str) -> None:
    """Export a table/snapshot to local parquet (placeholder)."""
    raise NotImplementedError

