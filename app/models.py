"""Canonical transaction schema and API response models."""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class Transaction(BaseModel):
    """Canonical transaction schema."""

    date: date
    merchant_raw: str
    merchant: str = ""
    category: str = "Other"
    amount: float
    currency: str = "TRY"
    direction: str = "expense"  # expense | income
    balance: Optional[float] = None
    confidence: float = 1.0  # categorization confidence 0-1


class IncomeInference(BaseModel):
    """Income inference result."""

    amount: float
    confidence: float
    explanation: str


class Summary(BaseModel):
    """Monthly summary."""

    expenses: float
    income: float
    net: float
    transaction_count: int


class CategoryBreakdown(BaseModel):
    """Expense by category."""

    category: str
    amount: float
    share: float


class DailySpend(BaseModel):
    """Daily spending."""

    date: str  # YYYY-MM-DD
    amount: float


class RecurringPayment(BaseModel):
    """Detected recurring payment."""

    merchant: str
    frequency: str  # monthly | weekly | etc.
    avg_amount: float
    last_amount: float
    last_seen_date: str
    confidence: float


class AnalysisResult(BaseModel):
    """Full analysis response."""

    month: str  # YYYY-MM
    income: IncomeInference
    summary: Summary
    by_category: list[CategoryBreakdown]
    daily_spend: list[DailySpend]
    recurring: list[RecurringPayment]
    transactions: list[Transaction]
