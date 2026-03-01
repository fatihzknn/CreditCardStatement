"""Tests for income inference."""

from app.models import Transaction
from app.services.income import infer_income


def _tx(desc: str, amount: float, direction: str = "income") -> Transaction:
    from datetime import date
    return Transaction(
        date=date(2024, 2, 1),
        merchant_raw=desc,
        amount=amount,
        direction=direction,
    )


def test_salary_keyword_match():
    """MAAŞ keyword triggers high-confidence income."""
    txs = [_tx("MAAŞ ÖDEMESİ - ABC ŞİRKET", 45000)]
    result = infer_income(txs)
    assert result["amount"] == 45000
    assert result["confidence"] >= 0.8
    expl = result["explanation"].lower()
    assert "keyword" in expl or "salary" in expl or "maaş" in expl or "maas" in expl


def test_fallback_largest_credit():
    """No salary keyword -> use largest credit."""
    txs = [_tx("BONUS XYZ CORP", 5000), _tx("REFUND", 100)]
    result = infer_income(txs)
    assert result["amount"] == 5000
    assert result["confidence"] <= 0.8  # No MAAŞ/SALARY keyword


def test_no_income():
    """No income transactions -> zero."""
    txs = [_tx("EXPENSE", -100, direction="expense")]
    result = infer_income(txs)
    assert result["amount"] == 0
    assert result["confidence"] == 0
