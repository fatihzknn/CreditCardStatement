"""CSV statement parser with flexible column detection."""

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.models import Transaction


# Common column name mappings (case-insensitive)
DATE_COLUMNS = ["date", "tarih", "transaction_date", "islem_tarihi", "posting_date"]
DESC_COLUMNS = ["description", "aciklama", "merchant", "merchant_name", "details", "detay"]
AMOUNT_COLUMNS = ["amount", "tutar", "debit", "credit", "withdrawal", "deposit"]
BALANCE_COLUMNS = ["balance", "bakiye"]
CURRENCY_COLUMNS = ["currency", "para_birimi"]

# Direction hints: if column contains these, it may indicate expense vs income
EXPENSE_HINTS = ["debit", "withdrawal", "expense", "gider", "borc"]
INCOME_HINTS = ["credit", "deposit", "income", "gelir", "alacak"]


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Find first matching column (case-insensitive)."""
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    return None


def _parse_amount(val) -> float:
    """Parse amount from various formats."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    s = s.replace(",", ".").replace(" ", "")
    # Remove currency symbols
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_date(val) -> datetime | None:
    """Parse date from various formats."""
    if pd.isna(val):
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).strip()
    for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"]:
        try:
            return datetime.strptime(s[:10], fmt)
        except ValueError:
            continue
    return None


def _infer_direction(
    df: pd.DataFrame,
    amount_col: str,
    has_separate_debit_credit: bool,
) -> str:
    """
    Infer whether amounts are expenses (negative) or income (positive).
    Many statements: negative = expense, positive = credit/income.
    Some: separate debit/credit columns, both positive.
    """
    if has_separate_debit_credit:
        return "expense"  # We're in debit column
    sample = df[amount_col].dropna().head(100)
    if sample.empty:
        return "expense"
    # If most values are negative, convention is expense=negative
    neg_count = (sample < 0).sum()
    if neg_count > len(sample) * 0.5:
        return "expense"
    return "expense"  # Default


def parse_csv(path: Path) -> list[Transaction]:
    """
    Parse CSV credit card statement.
    Handles various column naming conventions (EN/TR).
    """
    df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
    if df.empty:
        return []

    date_col = _find_column(df, DATE_COLUMNS)
    desc_col = _find_column(df, DESC_COLUMNS)
    amount_col = _find_column(df, AMOUNT_COLUMNS)
    balance_col = _find_column(df, BALANCE_COLUMNS)
    currency_col = _find_column(df, CURRENCY_COLUMNS)

    # Fallback: use first columns by position
    if not date_col:
        date_col = df.columns[0] if len(df.columns) > 0 else None
    if not desc_col:
        desc_col = df.columns[1] if len(df.columns) > 1 else "description"
    if not amount_col:
        # Find numeric column
        for c in df.columns:
            if df[c].dtype in ("float64", "int64") or "amount" in c.lower():
                amount_col = c
                break
        amount_col = amount_col or df.columns[-1] if df.columns else "amount"

    if not date_col or not desc_col or not amount_col:
        raise ValueError("Could not detect required columns (date, description, amount).")

    # Check for separate debit/credit columns
    debit_col = _find_column(df, ["debit", "borc", "withdrawal", "expense"])
    credit_col = _find_column(df, ["credit", "alacak", "deposit", "income"])
    has_separate = bool(debit_col and credit_col)

    transactions: list[Transaction] = []
    currency = "TRY"

    for _, row in df.iterrows():
        dt = _parse_date(row.get(date_col))
        if not dt:
            continue

        desc = str(row.get(desc_col, "")).strip()
        if not desc or desc.lower() in ("nan", ""):
            continue

        if has_separate and debit_col and credit_col:
            amt_debit = _parse_amount(row.get(debit_col))
            amt_credit = _parse_amount(row.get(credit_col))
            if amt_debit > 0:
                amount = -amt_debit
                direction = "expense"
            elif amt_credit > 0:
                amount = amt_credit
                direction = "income"
            else:
                continue
        else:
            amount = _parse_amount(row.get(amount_col))
            direction = "expense" if amount < 0 else "income"
            # Normalize: we store expenses as negative, income as positive
            if amount == 0:
                continue

        if currency_col:
            cur = str(row.get(currency_col, "TRY")).strip().upper()
            if cur and cur != "NAN":
                currency = cur[:3]

        balance = None
        if balance_col:
            b = _parse_amount(row.get(balance_col))
            if b != 0:
                balance = b

        transactions.append(
            Transaction(
                date=dt.date(),
                merchant_raw=desc,
                amount=amount,
                currency=currency,
                direction=direction,
                balance=balance,
            )
        )

    return transactions
