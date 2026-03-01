"""Tests for recurring payment detection."""

from datetime import date, timedelta

from app.models import Transaction
from app.services.recurring import detect_recurring


def _tx(d: date, merchant: str, amount: float, direction: str = "expense") -> Transaction:
    return Transaction(
        date=d,
        merchant_raw=merchant,
        merchant=merchant,
        amount=-amount if direction == "expense" else amount,
        direction=direction,
    )


def test_detect_netflix_monthly():
    """Netflix charged twice in same month -> recurring."""
    txs = [
        _tx(date(2024, 2, 4), "Netflix", 79.99),
        _tx(date(2024, 2, 17), "Netflix", 79.99),
    ]
    result = detect_recurring(txs, min_occurrences=2)
    assert len(result) >= 1
    r = result[0]
    assert "Netflix" in r["merchant"]
    assert r["frequency"] == "monthly"
    assert r["last_amount"] == 79.99


def test_detect_price_change():
    """Subscription with price change (9.99 -> 10.99) still detected."""
    txs = [
        _tx(date(2024, 1, 5), "Spotify", 34.99),
        _tx(date(2024, 2, 5), "Spotify", 36.99),  # ~6% increase
    ]
    result = detect_recurring(txs, min_occurrences=2, amount_tolerance=0.15)
    assert len(result) >= 1
    assert result[0]["merchant"] == "Spotify"


def test_no_recurring_single_occurrence():
    """Single occurrence is not recurring."""
    txs = [_tx(date(2024, 2, 4), "Netflix", 79.99)]
    result = detect_recurring(txs, min_occurrences=2)
    assert len(result) == 0


def test_ignores_income():
    """Income transactions are not considered for recurring."""
    txs = [
        _tx(date(2024, 2, 1), "Salary", 5000, direction="income"),
        _tx(date(2024, 2, 4), "Netflix", 79.99),
        _tx(date(2024, 2, 17), "Netflix", 79.99),
    ]
    result = detect_recurring(txs)
    assert all(r["merchant"] != "Salary" for r in result)
