import hashlib
import json
from pathlib import Path

CORE_PATH = Path("data/core_panel_v1/core_panel_v1.parquet")
META_PATH = Path("data/core_panel_v1/core_panel_v1_metadata.yaml")


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    import yaml

    meta = yaml.safe_load(META_PATH.read_text())
    expected = meta["checksums"]["sha256"]
    actual = sha256sum(CORE_PATH)
    if actual != expected:
        raise SystemExit(f"Checksum mismatch for {CORE_PATH}: {actual} != {expected}")
    print(f"OK: {CORE_PATH} sha256 matches {expected}")

if __name__ == "__main__":
    main()
