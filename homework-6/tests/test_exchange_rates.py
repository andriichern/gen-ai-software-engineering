"""Unit tests for exchange rate fetching."""
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from lib.exchange_rates import fetch_exchange_rates, ExchangeRateError


class TestFetchExchangeRates:
    """Tests for fetch_exchange_rates function."""

    def test_fetch_single_currency(self):
        """Should fetch exchange rate for a single currency."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"quote": "EUR", "rate": 0.92}
        ]

        with patch("lib.exchange_rates.requests.get", return_value=mock_response):
            result = fetch_exchange_rates(["EUR"])

        assert "USD" in result
        assert result["USD"] == Decimal("1")
        assert result["EUR"] == Decimal("0.92")

    def test_fetch_multiple_currencies(self):
        """Should fetch multiple currencies."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"quote": "EUR", "rate": 0.92},
            {"quote": "GBP", "rate": 0.79},
            {"quote": "JPY", "rate": 150.5}
        ]

        with patch("lib.exchange_rates.requests.get", return_value=mock_response):
            result = fetch_exchange_rates(["EUR", "GBP", "JPY"])

        assert result["USD"] == Decimal("1")
        assert result["EUR"] == Decimal("0.92")
        assert result["GBP"] == Decimal("0.79")
        assert result["JPY"] == Decimal("150.5")

    def test_fetch_ignores_usd(self):
        """Should not request USD exchange rate."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"quote": "EUR", "rate": 0.92}
        ]

        with patch("lib.exchange_rates.requests.get", return_value=mock_response) as mock_get:
            result = fetch_exchange_rates(["USD", "EUR"])

        # Should still have USD with rate 1
        assert result["USD"] == Decimal("1")
        # Should only request EUR, not USD
        call_args = mock_get.call_args
        assert "USD" not in call_args[1]["params"]["quotes"]

    def test_fetch_empty_currencies_returns_usd_only(self):
        """Empty currency list should return only USD."""
        result = fetch_exchange_rates([])

        assert result == {"USD": Decimal("1")}

    def test_fetch_with_none_currencies(self):
        """None currencies should be filtered out."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"quote": "EUR", "rate": 0.92}
        ]

        with patch("lib.exchange_rates.requests.get", return_value=mock_response):
            result = fetch_exchange_rates([None, "EUR", None])

        assert "EUR" in result
        assert "None" not in result

    def test_fetch_decimal_precision_preserved(self):
        """Rates should be Decimal with precision preserved."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"quote": "EUR", "rate": 0.918273645}
        ]

        with patch("lib.exchange_rates.requests.get", return_value=mock_response):
            result = fetch_exchange_rates(["EUR"])

        assert result["EUR"] == Decimal("0.918273645")

    def test_fetch_missing_required_rate_raises_error(self):
        """Missing rate for requested currency should raise error."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"quote": "EUR", "rate": 0.92}
            # Missing GBP
        ]

        with patch("lib.exchange_rates.requests.get", return_value=mock_response):
            with pytest.raises(ExchangeRateError, match="did not return rates"):
                fetch_exchange_rates(["EUR", "GBP"])

    def test_fetch_network_error_retries(self):
        """Network errors should trigger retries."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"quote": "EUR", "rate": 0.92}
        ]

        with patch("lib.exchange_rates.requests.get") as mock_get:
            # Fail twice, succeed on third attempt
            mock_get.side_effect = [
                Exception("Connection failed"),
                Exception("Connection failed"),
                mock_response
            ]

            with patch("lib.exchange_rates.time.sleep"):  # Don't actually sleep
                result = fetch_exchange_rates(["EUR"])

        assert result["EUR"] == Decimal("0.92")
        assert mock_get.call_count == 3

    def test_fetch_all_retries_fail_raises_error(self):
        """All retries failing should raise ExchangeRateError."""
        with patch("lib.exchange_rates.requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            with patch("lib.exchange_rates.time.sleep"):
                with pytest.raises(ExchangeRateError):
                    fetch_exchange_rates(["EUR"])

        assert mock_get.call_count == 3

    def test_fetch_http_error_retries(self):
        """HTTP errors should trigger retries."""
        mock_response_fail = MagicMock()
        mock_response_fail.raise_for_status.side_effect = Exception("500 Server Error")

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = [
            {"quote": "EUR", "rate": 0.92}
        ]

        with patch("lib.exchange_rates.requests.get") as mock_get:
            mock_get.side_effect = [
                mock_response_fail,
                mock_response_success
            ]

            with patch("lib.exchange_rates.time.sleep"):
                result = fetch_exchange_rates(["EUR"])

        assert result["EUR"] == Decimal("0.92")

    def test_fetch_timeout_parameter(self):
        """Request should use 10 second timeout."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"quote": "EUR", "rate": 0.92}
        ]

        with patch("lib.exchange_rates.requests.get", return_value=mock_response) as mock_get:
            fetch_exchange_rates(["EUR"])

        # Check timeout parameter
        call_args = mock_get.call_args
        assert call_args[1]["timeout"] == 10

    def test_fetch_uses_correct_api_url(self):
        """Should use Frankfurter API."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"quote": "EUR", "rate": 0.92}
        ]

        with patch("lib.exchange_rates.requests.get", return_value=mock_response) as mock_get:
            fetch_exchange_rates(["EUR"])

        call_args = mock_get.call_args
        assert "frankfurter" in call_args[0][0].lower()

    def test_fetch_request_params_structure(self):
        """Should send correct params to API."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"quote": "EUR", "rate": 0.92}
        ]

        with patch("lib.exchange_rates.requests.get", return_value=mock_response) as mock_get:
            fetch_exchange_rates(["EUR"])

        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["base"] == "USD"
        assert "EUR" in params["quotes"]

    def test_exchange_rate_error_message(self):
        """ExchangeRateError should have descriptive message."""
        with patch("lib.exchange_rates.requests.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            with patch("lib.exchange_rates.time.sleep"):
                with pytest.raises(ExchangeRateError) as exc_info:
                    fetch_exchange_rates(["EUR"])

        assert "failed to fetch" in str(exc_info.value)
        assert "frankfurter" in str(exc_info.value).lower()

    def test_fetch_sorted_currency_quotes(self):
        """Currencies should be sorted in request."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"quote": "GBP", "rate": 0.79},
            {"quote": "EUR", "rate": 0.92},
            {"quote": "JPY", "rate": 150.5}
        ]

        with patch("lib.exchange_rates.requests.get", return_value=mock_response) as mock_get:
            fetch_exchange_rates(["JPY", "EUR", "GBP"])

        call_args = mock_get.call_args
        quotes_str = call_args[1]["params"]["quotes"]
        quotes_list = quotes_str.split(",")
        assert quotes_list == sorted(quotes_list)

    def test_fetch_returns_decimal_type(self):
        """All returned rates should be Decimal type."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"quote": "EUR", "rate": 0.92},
            {"quote": "GBP", "rate": 0.79}
        ]

        with patch("lib.exchange_rates.requests.get", return_value=mock_response):
            result = fetch_exchange_rates(["EUR", "GBP"])

        for currency, rate in result.items():
            assert isinstance(rate, Decimal)

    def test_fetch_handles_string_rates_from_api(self):
        """API might return rates as strings."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"quote": "EUR", "rate": "0.92"},  # String instead of number
            {"quote": "GBP", "rate": 0.79}      # Number
        ]

        with patch("lib.exchange_rates.requests.get", return_value=mock_response):
            result = fetch_exchange_rates(["EUR", "GBP"])

        assert result["EUR"] == Decimal("0.92")
        assert result["GBP"] == Decimal("0.79")
