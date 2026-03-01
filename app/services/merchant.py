"""Merchant name normalization."""

import re
from typing import Optional

# Alias map: patterns or raw strings -> normalized name
# Order matters: more specific first
MERCHANT_ALIASES: list[tuple[str, str]] = [
    # Amazon variants
    (r"amzn\s*(eu|mkts?|\.)?", "Amazon"),
    ("amazon marketplace", "Amazon"),
    ("amazon.de", "Amazon"),
    ("amazon.com", "Amazon"),
    ("amazon tr", "Amazon"),
    # Netflix
    ("netflix.com", "Netflix"),
    ("netflix", "Netflix"),
    # Spotify
    ("spotify", "Spotify"),
    # Apple
    ("apple.com/bill", "Apple"),
    ("itunes.com", "Apple"),
    ("app store", "Apple"),
    # Google
    ("google", "Google"),
    ("google play", "Google Play"),
    ("youtube", "YouTube"),
    # Uber
    ("uber", "Uber"),
    ("uber eats", "Uber Eats"),
    # Common Turkish
    ("migros", "Migros"),
    ("carrefour", "Carrefour"),
    ("bim", "BIM"),
    ("a101", "A101"),
    ("sok", "Şok"),
    ("turkcell", "Turkcell"),
    ("vodafone", "Vodafone"),
    ("turk telekom", "Türk Telekom"),
    ("garanti", "Garanti Bank"),
    ("is bank", "İş Bankası"),
    ("yapi kredi", "Yapı Kredi"),
    ("akbank", "Akbank"),
    ("ziraat", "Ziraat Bankası"),
    # Generic
    ("atm", "ATM"),
    ("pos", "POS"),
    ("nakit", "Cash"),
]


def _normalize_raw(s: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def normalize_merchant(raw: str) -> tuple[str, float]:
    """
    Normalize merchant name.
    Returns (normalized_name, confidence 0-1).
    """
    if not raw or not raw.strip():
        return "Unknown", 0.0

    normalized_raw = _normalize_raw(raw)

    # Check alias map (regex and literal)
    for pattern, alias in MERCHANT_ALIASES:
        if re.search(pattern, normalized_raw, re.I):
            return alias, 0.95
        if pattern.lower() in normalized_raw:
            return alias, 0.9

    # Fallback: clean up and return shortened version
    # Remove common suffixes: location, numbers, etc.
    cleaned = re.sub(r"\b(tr|eu|de|com|net|org)\b", "", normalized_raw, flags=re.I)
    cleaned = re.sub(r"\d{4,}", "", cleaned)  # Remove long number sequences
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Take first 2-3 meaningful words
    words = [w for w in cleaned.split() if len(w) > 1][:3]
    result = " ".join(words).title() if words else raw[:30]

    # Confidence lower for fallback
    return result or raw[:30], 0.6
