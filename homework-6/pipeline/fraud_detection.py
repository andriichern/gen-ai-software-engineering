"""Fraud Detection stage.

Reads validated records from shared/output, moves each into shared/processing
while scoring it, and always passes the (now-annotated) record on to
shared/output for Compliance Check -- flagging is never a rejection.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict

from lib.common import (
    audit,
    clear_processing_file,
    lean_data,
    list_json_files,
    make_envelope,
    move_into_processing,
    parse_decimal,
    parse_iso8601,
    read_json,
    read_original_record,
    utc_now_iso,
    write_envelope,
)

STAGE_NAME = "fraud_detection"

HIGH_VALUE_WEIGHT = Decimal("0.50")
CROSS_BORDER_WEIGHT = Decimal("0.30")
UNUSUAL_HOUR_WEIGHT = Decimal("0.20")
HIGH_VALUE_USD_THRESHOLD = Decimal("10000")
FLAG_THRESHOLD = Decimal("0.50")
SCORE_CAP = Decimal("1.00")
BASELINE_COUNTRY = "GB"
UNUSUAL_HOUR_START = 6
UNUSUAL_HOUR_END = 22

ExchangeRates = Dict[str, Decimal]


def _usd_equivalent(amount: Decimal, currency: str, rates: ExchangeRates) -> Decimal:
    if currency == "USD":
        return amount
    rate = rates.get(currency)
    if rate is None:
        raise ValueError(f"no exchange rate available for currency: {currency}")
    return amount / rate


def score_transaction(record: Dict[str, Any], rates: ExchangeRates) -> Dict[str, Any]:
    """Computes a weighted, explainable fraud risk score. Never rejects -- flags only.

    `record` is the full original transaction (read from shared/input) so that
    metadata.country and the transaction's own timestamp are available.
    """
    amount = abs(parse_decimal(record["amount"]))
    currency = record["currency"]
    usd_equivalent = _usd_equivalent(amount, currency, rates)

    high_value = usd_equivalent >= HIGH_VALUE_USD_THRESHOLD

    # The canonical schema carries no separate source/destination account
    # country field -- only metadata.country -- so cross-border is judged
    # against the GB baseline via metadata.country alone.
    country = record.get("metadata", {}).get("country")
    cross_border = country is not None and country != BASELINE_COUNTRY

    tx_timestamp = parse_iso8601(record["timestamp"])
    unusual_hour = not (UNUSUAL_HOUR_START <= tx_timestamp.hour < UNUSUAL_HOUR_END)

    score = Decimal("0.00")
    if high_value:
        score += HIGH_VALUE_WEIGHT
    if cross_border:
        score += CROSS_BORDER_WEIGHT
    if unusual_hour:
        score += UNUSUAL_HOUR_WEIGHT
    score = min(score, SCORE_CAP)

    flagged = score >= FLAG_THRESHOLD

    return {
        "score": str(score),
        "factors": {
            "high_value_amount": high_value,
            "cross_border_mismatch": cross_border,
            "unusual_hour_timing": unusual_hour,
        },
        "flagged": flagged,
        "scored_at": utc_now_iso(),
    }


def run_stage(input_dir: Path, processing_dir: Path, output_dir: Path, rates: ExchangeRates) -> Dict[str, int]:
    processed = passed = failed = 0
    for src in list_json_files(output_dir):
        transaction_id = src.stem
        working = move_into_processing(src, processing_dir)
        envelope = read_json(working)
        data = envelope["data"]

        original = read_original_record(input_dir, transaction_id)
        result = score_transaction(original, rates)
        processed += 1
        if result["flagged"]:
            failed += 1
        else:
            passed += 1

        data["fraud_result"] = result
        new_data = lean_data(transaction_id, data["amount"], data["currency"], {
            "validation_result": data.get("validation_result"),
            "fraud_result": result,
        })
        new_envelope = make_envelope(STAGE_NAME, "compliance", new_data)
        write_envelope(output_dir, transaction_id, new_envelope)
        audit(STAGE_NAME, transaction_id, "flagged" if result["flagged"] else "not_flagged")

        clear_processing_file(working)

    return {"processed": processed, "passed": passed, "failed": failed}


def _default_shared_dir() -> Path:
    return Path("shared")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Fraud Detection stage standalone.")
    parser.add_argument("--input-dir", type=Path, default=_default_shared_dir() / "input")
    parser.add_argument("--output-dir", type=Path, default=_default_shared_dir() / "output")
    parser.add_argument("--processing-dir", type=Path, default=_default_shared_dir() / "processing")
    args = parser.parse_args()

    currencies = set()
    for f in list_json_files(args.output_dir):
        env = read_json(f)
        currencies.add(env["data"]["currency"])
    from lib.exchange_rates import fetch_exchange_rates  # local import to avoid a hard dependency for other stages

    rates = fetch_exchange_rates(currencies) if currencies else {}

    tally = run_stage(args.input_dir, args.processing_dir, args.output_dir, rates)
    print(f"[{STAGE_NAME}] processed={tally['processed']} passed={tally['passed']} failed={tally['failed']}")


if __name__ == "__main__":
    main()
