"""Classification service tests: category scoring + priority rules (Task 3)."""
from __future__ import annotations

from api.models import Priority
from api.services.classification import classify_ticket


def test_account_access_keywords_classify_correctly():
    result = classify_ticket("Cannot log in", "I forgot my password and need to sign in again.")
    assert result.category == "account_access"


def test_billing_question_keywords_classify_correctly():
    result = classify_ticket("Invoice issue", "My invoice has a charge I don't recognize on my subscription.")
    assert result.category == "billing_question"


def test_feature_request_keywords_classify_correctly():
    result = classify_ticket("Feature request", "It would be nice to have an enhancement for exporting data.")
    assert result.category == "feature_request"


def test_tied_category_scores_break_toward_earlier_registered_bug_report():
    result = classify_ticket("Regression found", "There is an error in the latest release.")
    assert result.category == "bug_report"


def test_more_keyword_matches_override_precedence_order():
    result = classify_ticket(
        "App error and crash",
        "There is a bug causing an error and crash, and also a regression.",
    )
    assert result.category == "technical_issue"


def test_urgent_priority_detected():
    result = classify_ticket("Production down", "This is critical and a security concern, production down now.")
    assert result.priority == Priority.URGENT


def test_high_priority_detected():
    result = classify_ticket("Important issue", "This is important and blocking our team, please handle asap.")
    assert result.priority == Priority.HIGH


def test_low_priority_detected():
    result = classify_ticket("Minor cosmetic issue", "This is a minor cosmetic suggestion, low impact.")
    assert result.priority == Priority.LOW


def test_defaults_to_other_and_medium_with_low_confidence_when_nothing_matches():
    result = classify_ticket("Hello", "Just checking in about something unrelated to any keywords.")
    assert result.category == "other"
    assert result.priority == Priority.MEDIUM
    assert result.confidence == 0.3


def test_confidence_increases_with_more_matches_and_is_capped_at_one():
    few_matches = classify_ticket("Login issue", "I forgot my password.")
    many_matches = classify_ticket(
        "Login issue",
        "I forgot my password, cannot log in, sign in fails, locked out, two-factor broken.",
    )
    assert many_matches.confidence >= few_matches.confidence
    assert many_matches.confidence <= 1.0
