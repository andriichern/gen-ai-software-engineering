"""Keyword-based ticket classification (category + priority)."""
from __future__ import annotations

import logging

from .category_registry import OTHER_CATEGORY, category_registry
from ..models import ClassificationResult, Priority

logger = logging.getLogger("ticket_classification")

_PRIORITY_KEYWORDS: dict[Priority, list[str]] = {
    Priority.URGENT: ["can't access", "cannot access", "critical", "production down", "security"],
    Priority.HIGH: ["important", "blocking", "asap"],
    Priority.LOW: ["minor", "cosmetic", "suggestion"],
}


def _find_matches(text: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if kw in text]


def _pick_category(text: str) -> tuple[str, list[str]]:
    """Scores every registered category by how many of its keywords appear in
    the text and picks the highest score. Ties go to whichever category was
    registered first (built-ins, then categories in creation order), since a
    strictly-greater count is required to overtake the current best."""
    best_category = OTHER_CATEGORY
    best_matches: list[str] = []
    for candidate_category, keywords in category_registry.list_all().items():
        matches = _find_matches(text, keywords)
        if len(matches) > len(best_matches):
            best_category = candidate_category
            best_matches = matches
    return best_category, best_matches


def classify_ticket(subject: str, description: str) -> ClassificationResult:
    text = f"{subject} {description}".lower()

    category, category_matches = _pick_category(text)

    priority = Priority.MEDIUM
    priority_matches: list[str] = []
    for candidate_priority in (Priority.URGENT, Priority.HIGH, Priority.LOW):
        matches = _find_matches(text, _PRIORITY_KEYWORDS[candidate_priority])
        if matches:
            priority = candidate_priority
            priority_matches = matches
            break

    all_keywords = category_matches + priority_matches
    if not all_keywords:
        confidence = 0.3  # both fell back to defaults, low confidence
    else:
        # More distinct keyword hits -> higher confidence, capped at 1.0.
        confidence = min(1.0, 0.5 + 0.15 * len(all_keywords))

    reasoning_parts = []
    if category_matches:
        reasoning_parts.append(
            f"category '{category}' matched the most keywords ({len(category_matches)}): {category_matches}"
        )
    else:
        reasoning_parts.append(f"no category keywords matched, defaulted to '{category}'")
    if priority_matches:
        reasoning_parts.append(f"priority '{priority.value}' matched keywords {priority_matches}")
    else:
        reasoning_parts.append(f"no priority keywords matched, defaulted to '{priority.value}'")
    reasoning = "; ".join(reasoning_parts)

    result = ClassificationResult(
        category=category,
        priority=priority,
        confidence=confidence,
        reasoning=reasoning,
        keywords_found=all_keywords,
    )

    logger.info(
        "Classified ticket: category=%s priority=%s confidence=%.2f keywords=%s",
        result.category,
        result.priority.value,
        result.confidence,
        result.keywords_found,
    )

    return result
