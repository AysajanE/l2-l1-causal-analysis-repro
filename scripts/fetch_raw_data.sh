#!/usr/bin/env bash
set -euo pipefail

# Fetches raw/large inputs that are intentionally excluded from the public repo.
# Each asset is downloaded to its target path and verified via SHA256.
#
# Usage:
#   bash scripts/fetch_raw_data.sh
#
# Requirements: curl, shasum (macOS) or sha256sum (Linux).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Choose shasum command adaptively
if command -v sha256sum >/dev/null 2>&1; then
  SHASUM="sha256sum"
else
  SHASUM="shasum -a 256"
fi

fail() { echo "ERROR: $*" >&2; exit 1; }

download_and_check() {
  local url="$1"
  local target="$2"
  local expected_sha="$3"

  echo ">> Fetching $(basename "$target")"
  mkdir -p "$(dirname "$target")"
  curl -L --fail --retry 3 --continue-at - -o "$target" "$url"

  echo ">> Verifying SHA256"
  local actual_sha
  actual_sha=$($SHASUM "$target" | awk '{print $1}')
  if [[ "$actual_sha" != "$expected_sha" ]]; then
    fail "Checksum mismatch for $(basename "$target"): expected $expected_sha got $actual_sha"
  fi
}

###############################
# RAW ASSETS (PIN THE URL + SHA)
###############################

# TODO: Replace URLs and SHA256 values with the exact source locations you are allowed to redistribute.
# Ethereum blocks (raw)
download_and_check \
  "https://zenodo.org/records/17665980/files/ethereum_blocks.parquet?download=1" \
  "$ROOT_DIR/data/blocks/ethereum_blocks.parquet" \
  "35eedaec90a25705387b5d81d93c1323ab75d26126bf458068c70a123c6a6397"

# Ethereum transactions (raw)
download_and_check \
  "https://zenodo.org/records/17665980/files/ethereum_transactions.parquet?download=1" \
  "$ROOT_DIR/data/transactions/ethereum_transactions.parquet" \
  "4567b8622b63ac9e45a010a7bba8509d230c137f9877ed5a98cdab0833c721c6"

# Project B Dune batches (licensed)
download_and_check \
  "https://zenodo.org/records/17665980/files/dune_batches.zip?download=1" \
  "$ROOT_DIR/data/project_B/dune_batches/projectB_dune_batches.zip" \
  "d34ea7105f37d10434cf7440d7ec67129f8665607c19e8dcb5de07a0315fcf91"

# Nansen CSV bundle (licensed)
download_and_check \
  "https://zenodo.org/records/17665980/files/nansen_bundle.zip?download=1" \
  "$ROOT_DIR/data/nansen/nansen_bundle.zip" \
  "dd4d4f7575f66bc1bd8a90ff7fa6d4a3c42371237c493bea93e874be8d7d85ec"

echo "All downloads completed and verified."
