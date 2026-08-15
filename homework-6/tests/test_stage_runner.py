"""Unit tests for stage runner orchestration logic."""
import json
from pathlib import Path

import pytest

from lib.common import write_json, read_json
from lib.stage_runner import run_stage_loop


class TestRunStageLoop:
    """Tests for run_stage_loop orchestration function."""

    def test_stage_loop_processes_all_files(self, temp_shared_dir):
        """Stage loop should process all JSON files in input directory."""
        input_dir = temp_shared_dir / "input"
        processing_dir = temp_shared_dir / "processing"
        output_dir = temp_shared_dir / "output"

        # Create test files
        write_json(input_dir / "TXN001.json", {"id": "TXN001"})
        write_json(input_dir / "TXN002.json", {"id": "TXN002"})

        # Simple processor function that copies files
        def process_tx(tx_id: str, working: Path) -> bool:
            data = read_json(working)
            write_json(output_dir / f"{tx_id}.json", data)
            return True

        # Run stage loop with "move" strategy
        result = run_stage_loop(input_dir, processing_dir, "move", process_tx)

        assert result["processed"] == 2
        assert result["passed"] == 2
        assert result["failed"] == 0

    def test_stage_loop_counts_failures(self, temp_shared_dir):
        """Stage loop should count failed transactions."""
        input_dir = temp_shared_dir / "input"
        processing_dir = temp_shared_dir / "processing"
        output_dir = temp_shared_dir / "output"

        # Create test files
        write_json(input_dir / "TXN001.json", {"id": "TXN001"})
        write_json(input_dir / "TXN002.json", {"id": "TXN002"})

        # Processor that fails on TXN002
        def process_tx(tx_id: str, working: Path) -> bool:
            if tx_id == "TXN002":
                return False  # Fail this one
            return True

        result = run_stage_loop(input_dir, processing_dir, "move", process_tx)

        assert result["processed"] == 2
        assert result["passed"] == 1
        assert result["failed"] == 1

    def test_stage_loop_empty_input_directory(self, temp_shared_dir):
        """Stage loop should handle empty input directory."""
        input_dir = temp_shared_dir / "input"
        processing_dir = temp_shared_dir / "processing"

        def process_tx(tx_id: str, working: Path) -> bool:
            return True

        result = run_stage_loop(input_dir, processing_dir, "move", process_tx)

        assert result["processed"] == 0
        assert result["passed"] == 0
        assert result["failed"] == 0

    def test_stage_loop_copy_strategy_preserves_input(self, temp_shared_dir):
        """Copy strategy should not remove input files."""
        input_dir = temp_shared_dir / "input"
        processing_dir = temp_shared_dir / "processing"
        output_dir = temp_shared_dir / "output"

        write_json(input_dir / "TXN001.json", {"id": "TXN001"})

        def process_tx(tx_id: str, working: Path) -> bool:
            data = read_json(working)
            write_json(output_dir / f"{tx_id}.json", data)
            return True

        run_stage_loop(input_dir, processing_dir, "copy", process_tx)

        # Input file should still exist with copy strategy
        assert (input_dir / "TXN001.json").exists()

    def test_stage_loop_move_strategy_removes_input(self, temp_shared_dir):
        """Move strategy should remove input files after processing."""
        input_dir = temp_shared_dir / "input"
        processing_dir = temp_shared_dir / "processing"
        output_dir = temp_shared_dir / "output"

        write_json(input_dir / "TXN001.json", {"id": "TXN001"})

        def process_tx(tx_id: str, working: Path) -> bool:
            data = read_json(working)
            write_json(output_dir / f"{tx_id}.json", data)
            return True

        run_stage_loop(input_dir, processing_dir, "move", process_tx)

        # Input file should be removed with move strategy
        assert not (input_dir / "TXN001.json").exists()

    def test_stage_loop_exception_handling(self, temp_shared_dir):
        """Stage loop should handle processor exceptions gracefully."""
        input_dir = temp_shared_dir / "input"
        processing_dir = temp_shared_dir / "processing"

        write_json(input_dir / "TXN001.json", {"id": "TXN001"})

        # Processor that raises exception
        def process_tx(tx_id: str, working: Path) -> bool:
            if tx_id == "TXN001":
                raise ValueError("Processing error")
            return True

        # Should raise the exception
        with pytest.raises(ValueError, match="Processing error"):
            run_stage_loop(input_dir, processing_dir, "move", process_tx)

    def test_stage_loop_processing_dir_cleanup(self, temp_shared_dir):
        """Processing directory should have no files after stage loop completes."""
        input_dir = temp_shared_dir / "input"
        processing_dir = temp_shared_dir / "processing"
        output_dir = temp_shared_dir / "output"

        write_json(input_dir / "TXN001.json", {"id": "TXN001"})

        def process_tx(tx_id: str, working: Path) -> bool:
            # Don't move the file, just process
            return True

        run_stage_loop(input_dir, processing_dir, "move", process_tx)

        # Processing directory should be empty
        processing_files = list(processing_dir.glob("*.json"))
        assert len(processing_files) == 0

    def test_stage_loop_sorted_order(self, temp_shared_dir):
        """Stage loop should process files in sorted order."""
        input_dir = temp_shared_dir / "input"
        processing_dir = temp_shared_dir / "processing"

        # Create files in non-alphabetical order
        write_json(input_dir / "TXN003.json", {"id": "TXN003"})
        write_json(input_dir / "TXN001.json", {"id": "TXN001"})
        write_json(input_dir / "TXN002.json", {"id": "TXN002"})

        processed_order = []

        def process_tx(tx_id: str, working: Path) -> bool:
            processed_order.append(tx_id)
            return True

        run_stage_loop(input_dir, processing_dir, "move", process_tx)

        # Should be processed in alphabetical order
        assert processed_order == ["TXN001", "TXN002", "TXN003"]
