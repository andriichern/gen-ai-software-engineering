"""Live exchange-rate fetching against the Frankfurter API (api.frankfurter.dev),
a free, open, no-API-key currency data source publishing ECB reference rates.

Used by the orchestrator (once per run, for whatever currencies actually
appear in the input) and, for standalone invocation, by the Fraud Detection
stage's CLI entry point.
"""
from __future__ import annotations

import time
from decimal import Decimal
from typing import Dict, Iterable, Set

import requests

FRANKFURTER_URL = "https://api.frankfurter.dev/v2/rates"
BASE_CURRENCY = "USD"
RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 3


class ExchangeRateError(RuntimeError):
    """Raised when live exchange rates cannot be fetched after all retries."""


def fetch_exchange_rates(currencies: Iterable[str]) -> Dict[str, Decimal]:
    """Fetch current USD-based exchange rates for the given currencies.

    Returns a mapping of currency -> Decimal(units of that currency per 1 USD).
    USD itself is always included with a rate of 1. Retries RETRY_ATTEMPTS
    times with a RETRY_DELAY_SECONDS delay; raises ExchangeRateError if every
    attempt fails. Never falls back to a guessed or stale rate.
    """
    quotes: Set[str] = {c for c in currencies if c and c != BASE_CURRENCY}
    rates: Dict[str, Decimal] = {BASE_CURRENCY: Decimal("1")}
    if not quotes:
        return rates

    params = {"base": BASE_CURRENCY, "quotes": ",".join(sorted(quotes))}

    last_error: Exception = ExchangeRateError("unknown error")
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = requests.get(FRANKFURTER_URL, params=params, timeout=10)
            response.raise_for_status()
            for entry in response.json():
                rates[entry["quote"]] = Decimal(str(entry["rate"]))
            missing = quotes - set(rates.keys())
            if missing:
                raise ExchangeRateError(f"exchange rate source did not return rates for: {sorted(missing)}")
            return rates
        except Exception as exc:  # noqa: BLE001 -- any failure triggers the retry/backoff contract
            last_error = exc
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS)

    raise ExchangeRateError(
        f"failed to fetch live exchange rates from {FRANKFURTER_URL} after {RETRY_ATTEMPTS} attempts: {last_error}"
    ) from last_error
