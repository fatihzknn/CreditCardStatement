"""Tests for CSV and PDF parsers."""

from datetime import date
from pathlib import Path

import pytest

from app.parsers import parse_csv, parse_statement
from app.models import Transaction


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_csv_basic():
    """Parse a simple CSV with date, description, amount."""
    csv_path = Path(__file__).parent.parent / "sample_data" / "sample_statement.csv"
    txs = parse_csv(csv_path)
    assert len(txs) > 0
    t = txs[0]
    assert isinstance(t, Transaction)
    assert isinstance(t.date, date)
    assert t.merchant_raw
    assert t.amount != 0
    assert t.direction in ("expense", "income")


def test_parse_csv_income_detection():
    """Income (positive) and expense (negative) correctly detected."""
    csv_path = Path(__file__).parent.parent / "sample_data" / "sample_statement.csv"
    txs = parse_csv(csv_path)
    income = [t for t in txs if t.direction == "income"]
    expenses = [t for t in txs if t.direction == "expense"]
    assert len(income) >= 1  # MAAŞ
    assert len(expenses) >= 1


def test_parse_statement_csv():
    """parse_statement dispatches to CSV parser."""
    csv_path = Path(__file__).parent.parent / "sample_data" / "sample_statement.csv"
    txs = parse_statement(csv_path)
    assert len(txs) > 0


def test_parse_statement_unsupported():
    """Unsupported format raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported"):
        parse_statement(Path("/tmp/test.xlsx"))
