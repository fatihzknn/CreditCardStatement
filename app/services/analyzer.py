"""Main analysis orchestrator."""

from collections import defaultdict
from datetime import date

from app.models import (
    Transaction,
    IncomeInference,
    Summary,
    CategoryBreakdown,
    DailySpend,
    RecurringPayment,
    AnalysisResult,
)
from app.services.merchant import normalize_merchant
from app.services.categorizer import categorize_transaction
from app.services.recurring import detect_recurring
from app.services.income import infer_income


def analyze_statement(transactions: list[Transaction]) -> AnalysisResult:
    """
    Run full analysis: normalize merchants, categorize, detect recurring, infer income.
    """
    if not transactions:
        return AnalysisResult(
            month="",
            income=IncomeInference(amount=0, confidence=0, explanation="No transactions."),
            summary=Summary(expenses=0, income=0, net=0, transaction_count=0),
            by_category=[],
            daily_spend=[],
            recurring=[],
            transactions=[],
        )

    # Infer month from transaction dates
    dates = [t.date for t in transactions]
    month_str = max(dates).strftime("%Y-%m") if dates else ""

    # 1. Normalize merchants and categorize
    for t in transactions:
        merchant_norm, _ = normalize_merchant(t.merchant_raw)
        t.merchant = merchant_norm
        cat, conf = categorize_transaction(t.merchant_raw, t.merchant)
        t.category = cat
        t.confidence = conf

    # 2. Income inference
    income_result = infer_income(transactions)
    income = IncomeInference(**income_result)

    # 3. Summary
    expenses = sum(abs(t.amount) for t in transactions if t.direction == "expense")
    income_total = sum(t.amount for t in transactions if t.direction == "income")
    summary = Summary(
        expenses=round(expenses, 2),
        income=round(income_total, 2),
        net=round(income_total - expenses, 2),
        transaction_count=len(transactions),
    )

    # 4. By category (expenses only)
    by_cat: dict[str, float] = defaultdict(float)
    for t in transactions:
        if t.direction == "expense":
            by_cat[t.category] += abs(t.amount)

    by_category = [
        CategoryBreakdown(
            category=cat,
            amount=round(amt, 2),
            share=round(amt / expenses, 4) if expenses > 0 else 0,
        )
        for cat, amt in sorted(by_cat.items(), key=lambda x: -x[1])
    ]

    # 5. Daily spend (expenses only)
    daily: dict[str, float] = defaultdict(float)
    for t in transactions:
        if t.direction == "expense":
            daily[t.date.isoformat()] += abs(t.amount)

    daily_spend = [
        DailySpend(date=d, amount=round(amt, 2))
        for d, amt in sorted(daily.items())
    ]

    # 6. Recurring detection
    recurring_raw = detect_recurring(transactions)
    recurring = [RecurringPayment(**r) for r in recurring_raw]

    return AnalysisResult(
        month=month_str,
        income=income,
        summary=summary,
        by_category=by_category,
        daily_spend=daily_spend,
        recurring=recurring,
        transactions=transactions,
    )
