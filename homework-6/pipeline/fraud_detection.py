"""Fraud Detection stage.

Scores every transaction on a 0.00-1.00 scale using three additive, capped,
weighted factors. Fraud Detection only flags for review; it never rejects or
blocks a transaction. Each factor is evaluated independently from the
record and live exchange rates alone, so this stage does not actually need
any prior stage's result to run correctly — but per the stage-independence
contract, any factor it genuinely cannot evaluate (e.g. no exchange rate
for the transaction's currency) is recorded as not-applicable, naming what
was missing, rather than guessed or defaulted.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, time as dt_time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from lib.exchange_rates import ExchangeRates, fetch_exchange_rates
from lib.models import FraudResult, StageContext, Transaction
from lib.stage_runner import run_downstream_stage

HIGH_VALUE_USD_THRESHOLD = Decimal("10000")
HIGH_VALUE_WEIGHT = Decimal("0.50")
CROSS_BORDER_WEIGHT = Decimal("0.30")
UNUSUAL_HOUR_WEIGHT = Decimal("0.20")
FLAG_THRESHOLD = Decimal("0.50")
BASELINE_COUNTRY = "GB"
UNUSUAL_HOUR_WINDOW_START = dt_time(6, 0)
UNUSUAL_HOUR_WINDOW_END = dt_time(22, 0)


def _parse_utc_datetime(value: str):
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def _high_value_factor(record: Transaction, rates: ExchangeRates) -> dict:
    try:
        amount = abs(Decimal(record.amount))
    except (InvalidOperation, TypeError):
        return {"triggered": False, "weight": float(HIGH_VALUE_WEIGHT), "applicable": False,
                "note": "amount is not a valid decimal string"}

    usd_amount = rates.to_usd(amount, record.currency)
    if usd_amount is None:
        return {
            "triggered": False,
            "weight": float(HIGH_VALUE_WEIGHT),
            "applicable": False,
            "note": f"no exchange rate available for currency '{record.currency}'",
        }
    return {
        "triggered": usd_amount >= HIGH_VALUE_USD_THRESHOLD,
        "weight": float(HIGH_VALUE_WEIGHT),
        "applicable": True,
        "note": f"{usd_amount} USD equivalent",
    }


def _cross_border_factor(record: Transaction) -> dict:
    country = (record.metadata or {}).get("country")
    if not country:
        return {
            "triggered": False,
            "weight": float(CROSS_BORDER_WEIGHT),
            "applicable": False,
            "note": "metadata.country missing",
        }
    return {
        "triggered": country.upper() != BASELINE_COUNTRY,
        "weight": float(CROSS_BORDER_WEIGHT),
        "applicable": True,
        "note": f"metadata.country={country} vs baseline {BASELINE_COUNTRY}",
    }


def _unusual_hour_factor(record: Transaction) -> dict:
    try:
        parsed = _parse_utc_datetime(record.timestamp)
    except (ValueError, AttributeError):
        return {
            "triggered": False,
            "weight": float(UNUSUAL_HOUR_WEIGHT),
            "applicable": False,
            "note": "timestamp is not a valid ISO 8601 UTC datetime",
        }
    clock = parsed.timetz().replace(tzinfo=None)
    within_window = UNUSUAL_HOUR_WINDOW_START <= clock <= UNUSUAL_HOUR_WINDOW_END
    return {
        "triggered": not within_window,
        "weight": float(UNUSUAL_HOUR_WEIGHT),
        "applicable": True,
        "note": f"transaction time {clock.isoformat()} UTC",
    }


def score_transaction(record: Transaction, context: StageContext, rates: ExchangeRates) -> FraudResult:
    factors = {
        "high_value_amount": _high_value_factor(record, rates),
        "cross_border_mismatch": _cross_border_factor(record),
        "unusual_hour_timing": _unusual_hour_factor(record),
    }

    total = Decimal("0")
    missing = []
    for name, factor in factors.items():
        if not factor["applicable"]:
            missing.append(f"{name}: {factor['note']}")
            continue
        if factor["triggered"]:
            total += Decimal(str(factor["weight"]))

    score = min(total, Decimal("1.00"))
    flagged = score >= FLAG_THRESHOLD

    return FraudResult(score=str(score), flagged=flagged, factors=factors, missing=missing)


def _is_pass(result: FraudResult) -> bool:
    return not result.flagged


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fraud_detection",
        description="Fraud Detection stage for the transaction processing pipeline.",
    )
    parser.add_argument("--input-dir", default="shared/output", help="Directory of upstream messages to read.")
    parser.add_argument("--output-dir", default="shared/output", help="Directory to write annotated messages to.")
    parser.add_argument(
        "--original-dir",
        default="shared/input",
        help="Directory holding original transaction records (for fields not carried in lean messages).",
    )
    args = parser.parse_args()

    rates = fetch_exchange_rates()

    tally = run_downstream_stage(
        stage_name="fraud_detection",
        next_stage="compliance",
        result_key="fraud_result",
        compute_fn=score_transaction,
        source_dir=Path(args.input_dir),
        processing_dir=Path(args.output_dir).parent / "processing",
        output_dir=Path(args.output_dir),
        input_dir=Path(args.original_dir),
        is_pass=_is_pass,
        extra_kwargs={"rates": rates},
    )
    print(f"[fraud_detection] done: {tally}")


if __name__ == "__main__":
    main()
