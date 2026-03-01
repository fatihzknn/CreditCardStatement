"""Recurring payment / subscription detection."""

from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from app.models import Transaction


def _amount_similar(a: float, b: float, tolerance: float = 0.15) -> bool:
    """Check if amounts are similar (within tolerance, e.g. 15% for price changes)."""
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return False
    ratio = min(a, b) / max(a, b)
    return ratio >= (1 - tolerance)


def _infer_frequency(dates: list[date]) -> str:
    """Infer frequency from date gaps (weekly vs monthly)."""
    if len(dates) < 2:
        return "monthly"
    sorted_dates = sorted(dates)
    gaps = [
        (sorted_dates[i + 1] - sorted_dates[i]).days
        for i in range(len(sorted_dates) - 1)
    ]
    avg_gap = sum(gaps) / len(gaps)
    if avg_gap <= 10:
        return "weekly"
    if avg_gap <= 35:
        return "monthly"
    if avg_gap <= 95:
        return "quarterly"
    return "yearly"


def detect_recurring(
    transactions: list[Transaction],
    min_occurrences: int = 2,
    amount_tolerance: float = 0.15,
) -> list[dict]:
    """
    Detect recurring payments by merchant + similar amounts.
    Handles price changes (e.g. 9.99 -> 10.99).
    """
    # Group by merchant (expenses only)
    by_merchant: dict[str, list[Transaction]] = defaultdict(list)
    for t in transactions:
        if t.direction == "expense" and t.merchant and t.amount != 0:
            amt = abs(t.amount)
            by_merchant[t.merchant].append((t.date, amt))

    result: list[dict] = []

    for merchant, entries in by_merchant.items():
        if len(entries) < min_occurrences:
            continue

        # Cluster by similar amount
        entries_sorted = sorted(entries, key=lambda x: x[0])
        clusters: list[list[tuple[date, float]]] = []
        current_cluster: list[tuple[date, float]] = [entries_sorted[0]]

        for d, amt in entries_sorted[1:]:
            prev_amt = current_cluster[-1][1]
            if _amount_similar(amt, prev_amt, amount_tolerance):
                current_cluster.append((d, amt))
            else:
                if len(current_cluster) >= min_occurrences:
                    clusters.append(current_cluster)
                current_cluster = [(d, amt)]

        if len(current_cluster) >= min_occurrences:
            clusters.append(current_cluster)

        for cluster in clusters:
            amounts = [a for _, a in cluster]
            dates = [d for d, _ in cluster]
            avg_amount = sum(amounts) / len(amounts)
            last_amount = amounts[-1]
            last_date = dates[-1]
            frequency = _infer_frequency(dates)

            # Confidence: more occurrences = higher
            confidence = min(0.95, 0.5 + 0.1 * len(cluster))
            if frequency == "monthly" and len(cluster) >= 2:
                confidence = max(confidence, 0.8)

            result.append({
                "merchant": merchant,
                "frequency": frequency,
                "avg_amount": round(avg_amount, 2),
                "last_amount": round(last_amount, 2),
                "last_seen_date": last_date.isoformat(),
                "confidence": round(confidence, 2),
            })

    return result
