"""Live exchange rates from the Open Access endpoint of exchangerate-api.com
(https://open.er-api.com/v6/latest/USD) — free, no API key required. Used by
Fraud Detection's high-value-amount factor to convert any transaction
currency into its USD equivalent.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import requests

OPEN_ER_API_URL = "https://open.er-api.com/v6/latest/USD"


@dataclass
class ExchangeRates:
    """rates maps ISO 4217 code -> units of that currency per 1 USD."""

    base: str
    rates: dict

    def to_usd(self, amount: Decimal, currency: str) -> Optional[Decimal]:
        """Convert amount (in currency) to its USD equivalent. Returns None
        if no rate is available for currency — never guessed or defaulted."""
        currency = currency.upper() if currency else currency
        if currency == self.base:
            return amount
        rate = self.rates.get(currency)
        if not rate:
            return None
        return amount / Decimal(str(rate))


def fetch_exchange_rates(retries: int = 3, delay_seconds: float = 3.0) -> ExchangeRates:
    """Fetch current USD-based exchange rates, retrying on failure. Raises
    RuntimeError if all retries are exhausted — never falls back to a
    guessed or stale rate."""
    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(OPEN_ER_API_URL, timeout=10)
            response.raise_for_status()
            payload = response.json()
            if payload.get("result") != "success":
                raise RuntimeError(f"exchange rate source returned non-success result: {payload.get('result')}")
            return ExchangeRates(base=payload["base_code"], rates=payload["rates"])
        except Exception as exc:  # noqa: BLE001 - genuinely any failure must retry then surface
            last_error = exc
            if attempt < retries:
                time.sleep(delay_seconds)

    raise RuntimeError(
        f"failed to fetch live exchange rates from {OPEN_ER_API_URL} after {retries} attempts: {last_error}"
    )
