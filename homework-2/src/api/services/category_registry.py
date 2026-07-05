"""In-memory registry of ticket categories and their classification keywords.

Categories are managed at runtime through the /category API rather than being
a fixed enum, so new categories can be added without a code change. "other" is
the hardcoded fallback used when nothing matches and is not manageable here.
"""
from __future__ import annotations

OTHER_CATEGORY = "other"

# Seed data: precedence order matters as a tie-breaker when two categories
# match the same number of keywords. bug_report is listed before
# technical_issue so specific reproduction-step language keeps its edge in a
# tie against generic error/bug wording.
_DEFAULT_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    (
        "bug_report",
        ["steps to reproduce", "reproduction steps", "reproduce", "defect", "regression"],
    ),
    (
        "account_access",
        [
            "login",
            "log in",
            "password",
            "2fa",
            "two-factor",
            "authentication",
            "locked out",
            "sign in",
        ],
    ),
    (
        "billing_question",
        ["invoice", "payment", "refund", "billing", "charge", "subscription", "credit card"],
    ),
    (
        "feature_request",
        [
            "feature request",
            "enhancement",
            "suggestion",
            "would be nice",
            "please add",
            "could you add",
        ],
    ),
    (
        "technical_issue",
        ["bug", "error", "crash", "exception", "broken", "not working", "fails", "failure"],
    ),
]


class CategoryNotFoundError(Exception):
    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Category '{key}' not found")


def normalize_keyword(keyword: str) -> str:
    return keyword.strip().lower()


class CategoryRegistry:
    """Dict-backed registry. Insertion order is the classification precedence
    order: earlier categories win ties when scoring keyword matches."""

    def __init__(self) -> None:
        self._keywords: dict[str, list[str]] = {}
        for key, keywords in _DEFAULT_CATEGORY_KEYWORDS:
            self._keywords[key] = list(keywords)

    def exists(self, key: str) -> bool:
        return key in self._keywords

    def get(self, key: str) -> list[str]:
        if key not in self._keywords:
            raise CategoryNotFoundError(key)
        return list(self._keywords[key])

    def list_all(self) -> dict[str, list[str]]:
        """Returns categories in precedence order (dict preserves insertion order)."""
        return {key: list(keywords) for key, keywords in self._keywords.items()}

    def create(self, key: str, keywords: list[str]) -> list[str]:
        """Idempotent: creates the category (appended last, lowest precedence)
        if missing, then merges in any given keywords."""
        if key not in self._keywords:
            self._keywords[key] = []
        return self.add_keywords(key, keywords)

    def add_keywords(self, key: str, keywords: list[str]) -> list[str]:
        """Merges new keywords into an existing category, skipping exact
        duplicates already present. Raises CategoryNotFoundError if missing."""
        if key not in self._keywords:
            raise CategoryNotFoundError(key)
        existing = self._keywords[key]
        for keyword in keywords:
            normalized = normalize_keyword(keyword)
            if normalized and normalized not in existing:
                existing.append(normalized)
        return list(existing)

    def reset(self) -> None:
        """Restores the registry to just the default seed categories. Used by tests."""
        self._keywords = {}
        for key, keywords in _DEFAULT_CATEGORY_KEYWORDS:
            self._keywords[key] = list(keywords)


category_registry = CategoryRegistry()
