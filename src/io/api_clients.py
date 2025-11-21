"""Minimal off-chain API clients (placeholders)."""


class DuneClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch(self, query_id: str, params: dict | None = None):
        raise NotImplementedError


class CoinGeckoClient:
    def fetch_price_series(self, asset: str = "ethereum"):
        raise NotImplementedError

