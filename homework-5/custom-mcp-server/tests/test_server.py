import pytest

from server import _read_words


def test_default_word_count_returns_30_words():
    result = _read_words()
    assert len(result.split()) == 30


def test_explicit_word_count_returns_that_many_words():
    result = _read_words(10)
    assert len(result.split()) == 10


def test_zero_word_count_returns_empty_string():
    result = _read_words(0)
    assert result == ""


def test_negative_word_count_raises_value_error():
    with pytest.raises(ValueError):
        _read_words(-1)


def test_word_count_beyond_total_clamps_to_all_available_words():
    result = _read_words(10_000)
    assert len(result.split()) == 418


def test_result_is_prefix_of_source_text():
    full_text = " ".join(_read_words(10_000).split())
    limited = _read_words(5)
    assert full_text.startswith(limited)
