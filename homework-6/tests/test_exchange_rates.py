"""Unit tests for lib/exchange_rates.py."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from lib.exchange_rates import ExchangeRates, OPEN_ER_API_URL, fetch_exchange_rates


# ---------------------------------------------------------------------------
# ExchangeRates.to_usd
# ---------------------------------------------------------------------------


def test_to_usd_same_currency_returns_amount_unchanged():
    rates = ExchangeRates(base="USD", rates={"EUR": "0.92"})
    assert rates.to_usd(Decimal("100"), "USD") == Decimal("100")


def test_to_usd_converts_using_rate():
    rates = ExchangeRates(base="USD", rates={"EUR": "0.92"})
    result = rates.to_usd(Decimal("92"), "EUR")
    assert result == Decimal("92") / Decimal("0.92")


def test_to_usd_missing_currency_returns_none():
    rates = ExchangeRates(base="USD", rates={"EUR": "0.92"})
    assert rates.to_usd(Decimal("100"), "JPY") is None


def test_to_usd_zero_rate_raises_division_by_zero():
    """Known gap: to_usd's falsy-check ("if not rate") does not catch the
    string "0" (a non-empty string is truthy), so a zero rate reaches the
    division and raises decimal.DivisionByZero instead of returning None.
    This test documents the current behaviour rather than asserting the
    presumably-intended graceful-None outcome, since fixing pipeline code
    is out of scope for test generation."""
    import decimal

    rates = ExchangeRates(base="USD", rates={"XXX": "0"})
    with pytest.raises(decimal.DivisionByZero):
        rates.to_usd(Decimal("100"), "XXX")


def test_to_usd_lowercase_currency_is_normalized():
    rates = ExchangeRates(base="USD", rates={"EUR": "0.92"})
    result = rates.to_usd(Decimal("92"), "eur")
    assert result == Decimal("92") / Decimal("0.92")


# ---------------------------------------------------------------------------
# fetch_exchange_rates
# ---------------------------------------------------------------------------


def _success_response(rates=None):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "result": "success",
        "base_code": "USD",
        "rates": rates or {"EUR": 0.92, "GBP": 0.79},
    }
    return response


def test_fetch_success_returns_exchange_rates_object():
    with patch("lib.exchange_rates.requests.get", return_value=_success_response()):
        result = fetch_exchange_rates(retries=1)
    assert isinstance(result, ExchangeRates)
    assert result.base == "USD"
    assert result.rates["EUR"] == 0.92


def test_fetch_uses_the_open_access_endpoint():
    with patch("lib.exchange_rates.requests.get", return_value=_success_response()) as mock_get:
        fetch_exchange_rates(retries=1)
    called_url = mock_get.call_args[0][0]
    assert called_url == OPEN_ER_API_URL


def test_fetch_uses_a_10_second_timeout():
    with patch("lib.exchange_rates.requests.get", return_value=_success_response()) as mock_get:
        fetch_exchange_rates(retries=1)
    assert mock_get.call_args[1]["timeout"] == 10


def test_fetch_non_success_result_raises_runtime_error():
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"result": "error"}
    with patch("lib.exchange_rates.requests.get", return_value=response), \
         patch("lib.exchange_rates.time.sleep"):
        with pytest.raises(RuntimeError):
            fetch_exchange_rates(retries=1)


def test_fetch_retries_on_failure_then_succeeds():
    with patch("lib.exchange_rates.requests.get") as mock_get, \
         patch("lib.exchange_rates.time.sleep") as mock_sleep:
        mock_get.side_effect = [Exception("network down"), _success_response()]
        result = fetch_exchange_rates(retries=2, delay_seconds=0)
    assert result.rates["EUR"] == 0.92
    assert mock_get.call_count == 2
    mock_sleep.assert_called()


def test_fetch_all_retries_exhausted_raises_runtime_error():
    with patch("lib.exchange_rates.requests.get") as mock_get, \
         patch("lib.exchange_rates.time.sleep"):
        mock_get.side_effect = Exception("connection refused")
        with pytest.raises(RuntimeError, match="failed to fetch live exchange rates"):
            fetch_exchange_rates(retries=3, delay_seconds=0)
    assert mock_get.call_count == 3


def test_fetch_never_falls_back_to_a_guessed_rate():
    """On total failure, fetch_exchange_rates raises rather than returning
    any stale/guessed ExchangeRates object."""
    with patch("lib.exchange_rates.requests.get") as mock_get, \
         patch("lib.exchange_rates.time.sleep"):
        mock_get.side_effect = Exception("boom")
        with pytest.raises(RuntimeError):
            fetch_exchange_rates(retries=1, delay_seconds=0)


def test_fetch_http_error_status_triggers_retry_then_succeeds():
    failing = MagicMock()
    failing.raise_for_status.side_effect = Exception("500 server error")
    with patch("lib.exchange_rates.requests.get") as mock_get, \
         patch("lib.exchange_rates.time.sleep"):
        mock_get.side_effect = [failing, _success_response()]
        result = fetch_exchange_rates(retries=2, delay_seconds=0)
    assert result.rates["EUR"] == 0.92


def test_fetch_single_retry_does_not_sleep_after_final_attempt():
    with patch("lib.exchange_rates.requests.get") as mock_get, \
         patch("lib.exchange_rates.time.sleep") as mock_sleep:
        mock_get.side_effect = Exception("boom")
        with pytest.raises(RuntimeError):
            fetch_exchange_rates(retries=1, delay_seconds=5)
    mock_sleep.assert_not_called()
