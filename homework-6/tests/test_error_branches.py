"""Tests for defensive error branches that the happy-path flows never reach.

These are the guard clauses and encoder fallbacks that only fire on malformed
input or programmer error. They are cheap to reach directly and are exactly
the paths most likely to be wrong when they finally do fire in production.
"""
import json
from decimal import Decimal
from pathlib import Path

import pytest

from lib import common
from lib.common import read_json, write_json
from lib.stage_runner import run_stage_loop
from pipeline import validation


class TestDecimalEncoder:
    def test_decimal_is_serialized_as_a_string(self, tmp_path):
        """Monetary values must never round-trip through float."""
        path = tmp_path / "out.json"

        write_json(path, {"amount": Decimal("0.1") + Decimal("0.2")})

        assert json.loads(path.read_text(encoding="utf-8"))["amount"] == "0.3"

    def test_unsupported_type_still_raises_type_error(self, tmp_path):
        """The encoder must delegate unknown types to the base class, not swallow them."""

        class Unserializable:
            pass

        with pytest.raises(TypeError):
            write_json(tmp_path / "out.json", {"bad": Unserializable()})

    def test_encoder_default_delegates_to_super(self):
        encoder = common._DecimalEncoder()

        assert encoder.default(Decimal("1.5")) == "1.5"
        with pytest.raises(TypeError):
            encoder.default(object())

    def test_nested_decimals_are_encoded(self, tmp_path):
        path = tmp_path / "out.json"

        write_json(path, {"totals": {"USD": Decimal("1500.00"), "EUR": Decimal("250.00")}})

        assert read_json(path)["totals"] == {"USD": "1500.00", "EUR": "250.00"}


class TestIso4217ValidGuard:
    @pytest.mark.parametrize("code", [None, 123, 12.5, ["USD"], {"c": "USD"}, True])
    def test_non_string_currency_is_invalid(self, code):
        assert validation._iso4217_valid(code) is False

    def test_empty_string_is_invalid(self):
        assert validation._iso4217_valid("") is False

    def test_real_code_is_valid(self):
        assert validation._iso4217_valid("usd") is True


class TestRunStageLoopGuards:
    def test_invalid_copy_mode_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError, match="copy_mode must be 'copy' or 'move'"):
            run_stage_loop(tmp_path, tmp_path / "processing", "teleport", lambda tid, path: True)

    def test_copy_mode_is_validated_before_any_file_is_touched(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "T1.json").write_text("{}", encoding="utf-8")
        processing = tmp_path / "processing"

        with pytest.raises(ValueError):
            run_stage_loop(source, processing, "", lambda tid, path: True)

        assert (source / "T1.json").exists()
        assert not processing.exists()

    def test_clear_processing_false_leaves_working_file(self, tmp_path):
        """Reporting relies on this: it clears files only after building the report."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "T1.json").write_text("{}", encoding="utf-8")
        processing = tmp_path / "processing"

        tally = run_stage_loop(source, processing, "move", lambda tid, path: True,
                               clear_processing=False)

        assert tally == {"processed": 1, "passed": 1, "failed": 0}
        assert (processing / "T1.json").exists()

    def test_callback_receives_transaction_id_and_working_path(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "TXN042.json").write_text('{"k": "v"}', encoding="utf-8")
        processing = tmp_path / "processing"
        seen = []

        def capture(transaction_id, working):
            # Asserted inside the callback: the loop clears the working file
            # as soon as the callback returns.
            seen.append(transaction_id)
            assert working.parent == processing
            assert json.loads(working.read_text(encoding="utf-8")) == {"k": "v"}
            return True

        run_stage_loop(source, processing, "copy", capture)

        assert seen == ["TXN042"]
        # The working file is cleared once the stage is done with it.
        assert not (processing / "TXN042.json").exists()

    def test_non_json_files_are_ignored(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "T1.json").write_text("{}", encoding="utf-8")
        (source / "notes.txt").write_text("ignore me", encoding="utf-8")
        (source / "sub").mkdir()

        tally = run_stage_loop(source, tmp_path / "processing", "copy", lambda tid, path: True)

        assert tally["processed"] == 1

    def test_files_are_processed_in_deterministic_sorted_order(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        for name in ("T3", "T1", "T2"):
            (source / f"{name}.json").write_text("{}", encoding="utf-8")
        seen = []

        run_stage_loop(source, tmp_path / "processing", "copy",
                       lambda tid, path: seen.append(tid) or True)

        assert seen == ["T1", "T2", "T3"]


class TestScoreBucketBoundaries:
    """The risk-score histogram buckets are closed intervals with gaps between
    them (0.00-0.19, 0.20-0.49, ...), so scores that land in a gap or outside
    0.00-1.00 are silently counted in no bucket. These tests pin that
    behaviour down so a future change to SCORE_BUCKETS is a deliberate one.
    """

    def _distribution(self, score):
        from pipeline.reporting import build_report

        report = build_report([{"fraud_result": {"score": score, "flagged": False},
                                "final_status": "settled"}])
        return report["risk_score_distribution"]

    @pytest.mark.parametrize("score,bucket", [
        ("0.00", "0.00-0.19"),
        ("0.19", "0.00-0.19"),
        ("0.20", "0.20-0.49"),
        ("0.49", "0.20-0.49"),
        ("0.50", "0.50-0.79"),
        ("0.79", "0.50-0.79"),
        ("0.80", "0.80-1.00"),
        ("1.00", "0.80-1.00"),
    ])
    def test_scores_land_in_the_expected_bucket(self, score, bucket):
        distribution = self._distribution(score)

        assert distribution[bucket] == 1
        assert sum(distribution.values()) == 1

    @pytest.mark.parametrize("score", ["0.195", "0.499999", "0.795"])
    def test_score_in_a_gap_between_buckets_is_counted_nowhere(self, score):
        """Documented consequence of the closed-interval bucket definitions."""
        assert sum(self._distribution(score).values()) == 0

    @pytest.mark.parametrize("score", ["1.01", "-0.10"])
    def test_score_outside_the_valid_range_is_counted_nowhere(self, score):
        assert sum(self._distribution(score).values()) == 0

    def test_missing_score_is_counted_nowhere(self):
        from pipeline.reporting import build_report

        report = build_report([{"fraud_result": {"flagged": False}, "final_status": "settled"}])

        assert sum(report["risk_score_distribution"].values()) == 0
