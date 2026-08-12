"""Shared data types for the transaction processing pipeline.

These types are reused by every stage module (pipeline/), the orchestrator,
and the stage services (services/), so they live in lib/ per the project's
shared-utilities convention.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Transaction:
    """The original transaction record, as read from the input dataset."""

    transaction_id: str
    timestamp: str
    source_account: str
    destination_account: str
    amount: str
    currency: str
    transaction_type: str
    description: str = ""
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(
            transaction_id=data.get("transaction_id"),
            timestamp=data.get("timestamp"),
            source_account=data.get("source_account"),
            destination_account=data.get("destination_account"),
            amount=data.get("amount"),
            currency=data.get("currency"),
            transaction_type=data.get("transaction_type"),
            description=data.get("description", ""),
            metadata=data.get("metadata") or {},
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ValidationResult:
    passed: bool
    reason: Optional[str] = None
    errors: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"passed": self.passed, "reason": self.reason, "errors": self.errors}

    @classmethod
    def from_dict(cls, data: dict) -> "ValidationResult":
        return cls(passed=data["passed"], reason=data.get("reason"), errors=data.get("errors", []))


@dataclass
class FraudResult:
    """score is kept as a decimal string to avoid binary-float rounding error."""

    score: str
    flagged: bool
    factors: dict = field(default_factory=dict)
    missing: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "flagged": self.flagged,
            "factors": self.factors,
            "missing": self.missing,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FraudResult":
        return cls(
            score=data["score"],
            flagged=data["flagged"],
            factors=data.get("factors", {}),
            missing=data.get("missing", []),
        )


@dataclass
class ComplianceResult:
    """status is one of: passed, held, rejected, not_applicable."""

    status: str
    reason: Optional[str] = None
    rule_outcomes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"status": self.status, "reason": self.reason, "rule_outcomes": self.rule_outcomes}

    @classmethod
    def from_dict(cls, data: dict) -> "ComplianceResult":
        return cls(
            status=data["status"],
            reason=data.get("reason"),
            rule_outcomes=data.get("rule_outcomes", {}),
        )


@dataclass
class SettlementResult:
    """status is one of: settled, not_settled."""

    status: str
    settlement_reference: Optional[str] = None
    settlement_timestamp: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "settlement_reference": self.settlement_reference,
            "settlement_timestamp": self.settlement_timestamp,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SettlementResult":
        return cls(
            status=data["status"],
            settlement_reference=data.get("settlement_reference"),
            settlement_timestamp=data.get("settlement_timestamp"),
            reason=data.get("reason"),
        )


@dataclass
class StageContext:
    """Accumulated results from stages that have already run for a transaction.

    A missing entry is a normal condition (that stage has not run yet, or ran
    in an order where it hasn't reached this record), never an error. Stages
    must handle any combination of present/absent entries gracefully.
    """

    validation_result: Optional[ValidationResult] = None
    fraud_result: Optional[FraudResult] = None
    compliance_result: Optional[ComplianceResult] = None
    settlement_result: Optional[SettlementResult] = None

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "StageContext":
        data = data or {}
        return cls(
            validation_result=ValidationResult.from_dict(data["validation_result"])
            if data.get("validation_result")
            else None,
            fraud_result=FraudResult.from_dict(data["fraud_result"]) if data.get("fraud_result") else None,
            compliance_result=ComplianceResult.from_dict(data["compliance_result"])
            if data.get("compliance_result")
            else None,
            settlement_result=SettlementResult.from_dict(data["settlement_result"])
            if data.get("settlement_result")
            else None,
        )

    def to_dict(self) -> dict:
        out = {}
        if self.validation_result is not None:
            out["validation_result"] = self.validation_result.to_dict()
        if self.fraud_result is not None:
            out["fraud_result"] = self.fraud_result.to_dict()
        if self.compliance_result is not None:
            out["compliance_result"] = self.compliance_result.to_dict()
        if self.settlement_result is not None:
            out["settlement_result"] = self.settlement_result.to_dict()
        return out


@dataclass
class ProcessedTransaction:
    """A fully-processed transaction as Reporting receives it: lean identifying
    fields plus the accumulated context from all prior stages."""

    transaction_id: str
    amount: str
    currency: str
    context: StageContext


@dataclass
class VerdictRecord:
    transaction_id: str
    verdict: str
    fraud_flagged: bool
    reason: Optional[str]
    stage_outcomes: dict


@dataclass
class RunReport:
    total: int
    settled: int
    rejected: int
    held: int
    incomplete: int
    fraud_flagged: int
    compliance_held: int
    summary: str
    generated_at: str
    verdicts: list  # list[VerdictRecord]
    errors: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "settled": self.settled,
            "rejected": self.rejected,
            "held": self.held,
            "incomplete": self.incomplete,
            "fraud_flagged": self.fraud_flagged,
            "compliance_held": self.compliance_held,
            "summary": self.summary,
            "generated_at": self.generated_at,
            "errors": self.errors,
        }
