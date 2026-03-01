"""Income inference from statement heuristics."""

from app.models import Transaction

# Salary/wage keywords (Turkish + English)
INCOME_KEYWORDS = [
    "maaş", "maas", "ücret", "ucret", "bordro", "sgk", "işveren", "isveren",
    "ödeme", "odeme", "ödemesi", "odemesi",
    "salary", "payroll", "wage", "employer", "company pay", "direct deposit",
    "havale", "eft", "transfer",
]


def _matches_income_keywords(desc: str) -> bool:
    """Check if description matches salary-like keywords."""
    desc_lower = desc.lower()
    for kw in INCOME_KEYWORDS:
        if kw in desc_lower:
            return True
    return False


def infer_income(transactions: list[Transaction]) -> dict:
    """
    Infer monthly income from statement.
    - Prefer transactions matching salary keywords.
    - Fallback: largest consistent monthly credit.
    Returns dict with amount, confidence, explanation.
    """
    income_txs = [t for t in transactions if t.direction == "income" and t.amount > 0]

    if not income_txs:
        return {
            "amount": 0.0,
            "confidence": 0.0,
            "explanation": "No income/credit transactions found in statement.",
        }

    # Strategy 1: Find salary-like transactions
    salary_like = [
        t for t in income_txs
        if _matches_income_keywords(t.merchant_raw) or _matches_income_keywords(t.merchant)
    ]

    if salary_like:
        # Take the one with highest amount (main salary)
        best = max(salary_like, key=lambda t: t.amount)
        return {
            "amount": round(best.amount, 2),
            "confidence": 0.9,
            "explanation": f"Inferred from salary-like transaction: '{best.merchant_raw}' (keyword match).",
        }

    # Strategy 2: Largest consistent monthly credit
    # Group by approximate amount (within 5% - same salary each month)
    from collections import defaultdict
    by_amount_bucket: dict[float, list[Transaction]] = defaultdict(list)
    for t in income_txs:
        bucket = round(t.amount, -2)  # Round to nearest 100
        by_amount_bucket[bucket].append(t)

    # Find the most frequent large credit (likely salary)
    best_txs: list[Transaction] = []
    for bucket, txs in by_amount_bucket.items():
        if bucket < 100:  # Ignore tiny credits
            continue
        if len(txs) > len(best_txs) or (len(txs) == len(best_txs) and txs and best_txs and max(t.amount for t in txs) > max(t.amount for t in best_txs)):
            best_txs = txs

    if best_txs:
        best_amount = max(t.amount for t in best_txs)
        return {
            "amount": round(best_amount, 2),
            "confidence": 0.7,
            "explanation": f"Inferred from largest recurring credit (no salary keyword match). Amount: {best_amount:.2f}.",
        }

    # Strategy 3: Just take largest single credit
    largest = max(income_txs, key=lambda t: t.amount)
    return {
        "amount": round(largest.amount, 2),
        "confidence": 0.5,
        "explanation": f"Fallback: largest single credit transaction: '{largest.merchant_raw}'. Low confidence - no salary keywords found.",
    }
