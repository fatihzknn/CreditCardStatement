"""Transaction categorization by keywords."""

import re
from typing import Optional

CATEGORIES = [
    "Groceries",
    "Restaurants",
    "Transport",
    "Shopping",
    "Bills",
    "Subscriptions",
    "Cash/ATM",
    "Health",
    "Travel",
    "Entertainment",
    "Education",
    "Other",
]

# Category -> list of keyword patterns (lowercase).
# These are deliberately generic TR + EN keywords so the app works
# for different banks and merchants, not just a single PDF.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Groceries": [
        # Large chains / markets
        "migros",
        "carrefour",
        "bim",
        "a101",
        "a 101",
        "sok",
        "şok",
        "market",
        "grocery",
        "süpermarket",
        "supermarket",
        "bakkal",
        "tesco",
        "mjet",
    ],
    "Restaurants": [
        "restaurant",
        "cafe",
        "café",
        "kafe",
        "restoran",
        "yemek",
        "food",
        "burger",
        "pizza",
        "kahve",
        "doner",
        "döner",
        "kebap",
        "kavur",
        "pilavcı",
        "pilavcisi",
        "tavuk dünyasi",
        "tavuk dunyasi",
        # Delivery platforms
        "uber eats",
        "getir yemek",
        "getir",
        "yemeksepeti",
        "tikla gelsin",
        # Fast food chains
        "mcdonald",
        "mc donald",
        "burger king",
        "kfc",
    ],
    "Transport": [
        "uber",
        "taxi",
        "taksi",
        "benzin",
        "petrol",
        "shell",
        "opet",
        "bp",
        "fuel",
        "otobüs",
        "otobus",
        "metro",
        "tram",
        "park",
        "otopark",
        "parking",
        # Tolls / public transport
        "hgs",
        "osmangazi",
        "kmo",
        "otoyol",
        "istanbulkart",
        "belbim",
    ],
    "Shopping": [
        "amazon",
        "amzn",
        "hepsiburada",
        "trendyol",
        "n11",
        "aliexpress",
        "shopping",
        "alışveriş",
        "alisveris",
        "lc waikiki",
        "zara",
        "hm ",
        "decathlon",
        "boyner",
        "mavi",
        "watsons",
        "rossmann",
        "flo",
        "avm",
        "mall",
        "bijuteri",
    ],
    "Bills": [
        "turkcell",
        "vodafone",
        "turk telekom",
        "türk telekom",
        "elektrik",
        "su ",
        "dogalgaz",
        "doğalgaz",
        "internet",
        "fatura",
        "fat.öde",
        "fat. ode",
        "bill",
        "ödeme",
        "odeme",
    ],
    "Subscriptions": [
        "netflix",
        "spotify",
        "storytel",
        "youtube",
        "youtube premium",
        "apple",
        "apple.com/bill",
        "itunes",
        "google play",
        "subscription",
        "abonelik",
        "premium",
        "membership",
    ],
    "Cash/ATM": [
        "atm",
        "nakit",
        "cash",
        "para çekme",
        "para cekme",
        "withdrawal",
        "bankamatik",
    ],
    "Health": [
        "eczane",
        "pharmacy",
        "sağlık",
        "saglik",
        "hastane",
        "hospital",
        "doktor",
        "doctor",
        "ilaç",
        "ilac",
        "dental",
    ],
    "Travel": [
        "thy",
        "turkish airlines",
        "pegasus",
        "sunexpress",
        "booking",
        "hotel",
        "otel",
        "uçak",
        "ucak",
        "flight",
        "tatil",
        "holiday",
        "travel",
        "airbnb",
    ],
    "Entertainment": [
        "sinema",
        "cinema",
        "film",
        "oyun",
        "game",
        "steam",
        "playstation",
        "psn",
        "netflix",
        "spotify",
        "biletix",
        "concert",
        "konser",
    ],
    "Education": [
        "kurs",
        "course",
        "eğitim",
        "egitim",
        "okul",
        "school",
        "üniversite",
        "universite",
        "udemy",
        "coursera",
    ],
    "Other": [],
}


def categorize_transaction(merchant_raw: str, merchant_normalized: str) -> tuple[str, float]:
    """
    Categorize a transaction.
    Returns (category, confidence 0-1).
    """
    text = f"{merchant_raw} {merchant_normalized}".lower()
    text = re.sub(r"[^\w\s]", " ", text)

    best_category = "Other"
    best_score = 0.0

    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == "Other":
            continue
        for kw in keywords:
            if kw in text:
                # Exact match = higher confidence
                score = 0.9 if f" {kw} " in f" {text} " or text.startswith(kw) else 0.7
                if score > best_score:
                    best_score = score
                    best_category = category

    if best_category == "Other":
        return "Other", 0.5  # Unknown, low confidence

    return best_category, best_score
