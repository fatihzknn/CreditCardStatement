"""Analysis services — categorization, income inference, recurring detection."""

from __future__ import annotations
import json, os, re
from collections import defaultdict
from typing import Optional
from app.models import (
    AnalysisResult, CategoryBreakdown, DailySpend,
    IncomeInference, RecurringPayment, Summary, Transaction,
)

MERCHANT_MAP: dict[str, tuple[str, float]] = {
    # Groceries
    "migros": ("Groceries", 0.98), "bim market": ("Groceries", 0.98),
    "bim a.s": ("Groceries", 0.98), "bim": ("Groceries", 0.95),
    "a101": ("Groceries", 0.98), "şok market": ("Groceries", 0.98),
    "şok": ("Groceries", 0.95), "sok-": ("Groceries", 0.95),
    "carrefoursa": ("Groceries", 0.98), "carrefour": ("Groceries", 0.95),
    "macro center": ("Groceries", 0.98), "hakmar": ("Groceries", 0.97),
    "file market": ("Groceries", 0.97), "onur market": ("Groceries", 0.97),
    "kipa": ("Groceries", 0.97), "walmart": ("Groceries", 0.97),
    "macgal gida": ("Groceries", 0.95), "macgal group": ("Groceries", 0.92),
    "gms gida": ("Groceries", 0.92), "mahi grup": ("Groceries", 0.90),
    "sukas gida": ("Groceries", 0.92), "depodan et": ("Groceries", 0.92),
    "manav": ("Groceries", 0.85), "kasap": ("Groceries", 0.85),
    "market": ("Groceries", 0.75), "supermarket": ("Groceries", 0.85),
    "kavurmaci": ("Groceries", 0.88), "tavuk dunyasi": ("Dining", 0.90),
    "tavuk dünyası": ("Dining", 0.90),

    # Dining
    "yemeksepeti": ("Dining", 0.99), "trendyol yemek": ("Dining", 0.99),
    "param/getir": ("Dining", 0.99), "paycell/getir": ("Dining", 0.99),
    "s/getir": ("Dining", 0.99), "getir": ("Dining", 0.97),
    "tikla gelsin": ("Dining", 0.97), "tıkla gelsin": ("Dining", 0.97),
    "starbucks": ("Dining", 0.99), "espressolab": ("Dining", 0.99),
    "kahve dünyası": ("Dining", 0.99), "kahve dün": ("Dining", 0.97),
    "sbx ": ("Dining", 0.97),  # Starbucks abbreviated
    "shs ": ("Dining", 0.88),  # Coffee shop
    "tchibo": ("Dining", 0.97), "cafe maranello": ("Dining", 0.98),
    "cafe ": ("Dining", 0.80), "kafe": ("Dining", 0.82),
    "mcdonalds": ("Dining", 0.99), "mc donalds": ("Dining", 0.99),
    "burger king": ("Dining", 0.99), "kfc": ("Dining", 0.99),
    "dominos": ("Dining", 0.99), "pizza hut": ("Dining", 0.99),
    "popeyes": ("Dining", 0.99), "little caesars": ("Dining", 0.99),
    "subway": ("Dining", 0.99), "btsm ": ("Dining", 0.85),
    "büyük ev": ("Dining", 0.85), "buyuk ev": ("Dining", 0.85),
    "nev mekan": ("Dining", 0.90), "taş-bahçe": ("Dining", 0.90),
    "tas-bahce": ("Dining", 0.90), "baruthane": ("Dining", 0.90),
    "türk lezzet": ("Dining", 0.92), "turk lezzet": ("Dining", 0.92),
    "saray firin": ("Dining", 0.90), "saray fırın": ("Dining", 0.90),
    "hakan pastane": ("Dining", 0.92), "pastane": ("Dining", 0.85),
    "fırın": ("Dining", 0.80), "firin": ("Dining", 0.80),
    "börek": ("Dining", 0.88), "pide": ("Dining", 0.88),
    "kebap": ("Dining", 0.88), "döner": ("Dining", 0.88),
    "lahmacun": ("Dining", 0.88), "restoran": ("Dining", 0.82),
    "restaurant": ("Dining", 0.82), "lokanta": ("Dining", 0.85),
    "balık": ("Dining", 0.80), "sushi": ("Dining", 0.88),
    "bistro": ("Dining", 0.82), "neruda cafe": ("Dining", 0.95),
    "ist küçükyalı hillto": ("Dining", 0.85),
    "adapazari cadde": ("Shopping", 0.80),
    "sakarya adapazari agora": ("Shopping", 0.80),

    # Transport
    "hgs yükl": ("Transport", 0.99), "hgs yuk": ("Transport", 0.99),
    "hgs ": ("Transport", 0.97), "iyzico/istanbulkart": ("Transport", 0.99),
    "istanbulkart": ("Transport", 0.99), "ibb": ("Transport", 0.95),
    "belbim": ("Transport", 0.99), "bel-bim": ("Transport", 0.99),
    "eshot": ("Transport", 0.99), "uber": ("Transport", 0.99),
    "bolt": ("Transport", 0.99), "bitaksi": ("Transport", 0.99),
    "param/marti": ("Transport", 0.97), "marti.tech": ("Transport", 0.97),
    "uskudar akaryakit": ("Transport", 0.97), "akaryakit": ("Transport", 0.92),
    "opet": ("Transport", 0.97), "shell": ("Transport", 0.95),
    "petrol": ("Transport", 0.85), "benzin": ("Transport", 0.88),
    "otopark": ("Transport", 0.85), "taksi": ("Transport", 0.88),
    "halköde öd/poaş": ("Transport", 0.95), "halkode": ("Transport", 0.92),
    "guzel enerji": ("Transport", 0.88),

    # Travel
    "turkish airlines": ("Travel", 0.99), "thy": ("Travel", 0.99),
    "pegasus": ("Travel", 0.99), "anadolujet": ("Travel", 0.99),
    "sunexpress": ("Travel", 0.99), "booking.com": ("Travel", 0.99),
    "airbnb": ("Travel", 0.99), "otel": ("Travel", 0.85),
    "hotel": ("Travel", 0.85), "obilet": ("Travel", 0.95),

    # Shopping
    "trendyol": ("Shopping", 0.99), "hepsiburada": ("Shopping", 0.99),
    "amazon": ("Shopping", 0.97), "n11": ("Shopping", 0.99),
    "zara": ("Shopping", 0.99), "zara galataport": ("Shopping", 0.99),
    "h&m": ("Shopping", 0.99), "bershka": ("Shopping", 0.99),
    "mango": ("Shopping", 0.97), "koton": ("Shopping", 0.99),
    "defacto": ("Shopping", 0.99), "lcw": ("Shopping", 0.99),
    "teknosa": ("Shopping", 0.99), "mediamarkt": ("Shopping", 0.99),
    "decathlon": ("Shopping", 0.99), "adidas": ("Shopping", 0.99),
    "nike": ("Shopping", 0.99), "boyner": ("Shopping", 0.99),
    "vakko": ("Shopping", 0.99), "beymen": ("Shopping", 0.99),
    "ikea": ("Shopping", 0.99), "bauhaus": ("Shopping", 0.99),
    "watsons": ("Shopping", 0.97), "hediye dunyasi": ("Shopping", 0.92),
    "hediiye dünyası": ("Shopping", 0.92),
    "ozdilek park": ("Shopping", 0.92), "ozdilekpark": ("Shopping", 0.92),
    "n kolay": ("Shopping", 0.85),
    "yaman bijuteri": ("Shopping", 0.90),
    "iyzico/shop.mango": ("Shopping", 0.99),
    "izmit mavi": ("Shopping", 0.85), "bursa kent": ("Shopping", 0.85),
    "reformtec": ("Shopping", 0.85),
    "csa ": ("Shopping", 0.78),  # Generic store abbreviation
    "ayfer kumru": ("Shopping", 0.75),
    "ozlem karaman": ("Shopping", 0.75),

    # Utilities
    "iski": ("Utilities", 0.99), "igdaş": ("Utilities", 0.99),
    "igdas": ("Utilities", 0.99), "bedaş": ("Utilities", 0.99),
    "bedas": ("Utilities", 0.99), "enerjisa": ("Utilities", 0.99),
    "elektrik": ("Utilities", 0.85), "doğalgaz": ("Utilities", 0.85),
    "fatura": ("Utilities", 0.75),

    # Telecom
    "turkcell": ("Telecom", 0.99), "vodafone teleko": ("Telecom", 0.99),
    "vodafone": ("Telecom", 0.99), "türk telekom": ("Telecom", 0.99),
    "turk telekom": ("Telecom", 0.99), "ttnet": ("Telecom", 0.99),
    "superonline": ("Telecom", 0.99), "turknet": ("Telecom", 0.99),
    "5342143110 vodafone": ("Telecom", 0.99),
    "5456744498 vodafone": ("Telecom", 0.99),

    # Health
    "eczane": ("Health", 0.97), "pharmacy": ("Health", 0.97),
    "in istanbul eczanesi": ("Health", 0.99),
    "hastane": ("Health", 0.95), "klinik": ("Health", 0.92),
    "doktor": ("Health", 0.90), "medikal": ("Health", 0.88),
    "diş": ("Health", 0.88), "optik": ("Health", 0.88),
    "acıbadem": ("Health", 0.99), "memorial": ("Health", 0.97),
    "sgk": ("Health", 0.90), "muayene": ("Health", 0.90),
    "ennova çocuk": ("Health", 0.88), "ennova cocuk": ("Health", 0.88),

    # Entertainment & Subscriptions
    "netflix": ("Entertainment", 0.99), "spotify": ("Entertainment", 0.99),
    "apple.com/bill": ("Entertainment", 0.99), "apple.com": ("Entertainment", 0.92),
    "google *youtube": ("Entertainment", 0.99),
    "youtube": ("Entertainment", 0.97), "google *": ("Entertainment", 0.88),
    "linkedinprea": ("Entertainment", 0.97), "linkedin": ("Entertainment", 0.95),
    "steam": ("Entertainment", 0.99), "epic games": ("Entertainment", 0.99),
    "playstation": ("Entertainment", 0.99), "xbox": ("Entertainment", 0.99),
    "blutv": ("Entertainment", 0.99), "gain tv": ("Entertainment", 0.99),
    "exxen": ("Entertainment", 0.99), "mubi": ("Entertainment", 0.99),
    "disney+": ("Entertainment", 0.99), "bein sport": ("Entertainment", 0.99),
    "sinema": ("Entertainment", 0.88), "cinemaximum": ("Entertainment", 0.99),
    "iyzico/storytel": ("Entertainment", 0.97), "storytel": ("Entertainment", 0.97),
    "zula kanyon": ("Entertainment", 0.88),
    "istanbul orienteering": ("Entertainment", 0.88),
    "istanbul orienteering si": ("Entertainment", 0.88),
    "chatgpt": ("Entertainment", 0.97), "openai": ("Entertainment", 0.97),
    "claude": ("Entertainment", 0.97), "anthropic": ("Entertainment", 0.97),
    "canva": ("Entertainment", 0.90), "adobe": ("Entertainment", 0.92),
    "microsoft 365": ("Entertainment", 0.95),

    # Education
    "udemy": ("Education", 0.99), "coursera": ("Education", 0.99),
    "duolingo": ("Education", 0.99), "okul": ("Education", 0.82),
    "kurs": ("Education", 0.82), "dershane": ("Education", 0.90),

    # Income
    "maaş": ("Income", 0.97), "maas": ("Income", 0.97),
    "salary": ("Income", 0.97), "hesaptan aktarim": ("Income", 0.90),
    "şube-hesaptan ödeme": ("Income", 0.95),
    "şube-otomatik ödeme": ("Income", 0.92),
    "iade": ("Income", 0.88), "satis iade": ("Income", 0.95),
    "refund": ("Income", 0.88), "cashback": ("Income", 0.90),
    "temettü": ("Income", 0.95),

    # Transfer
    "havale": ("Transfer", 0.85), "eft": ("Transfer", 0.85),
    "fast ödeme": ("Transfer", 0.90), "transfer": ("Transfer", 0.80),
    "kredi kartı öde": ("Transfer", 0.92), "minimum ödeme": ("Transfer", 0.92),

    # Cash/ATM
    "atm": ("Cash", 0.95), "bankamatik": ("Cash", 0.95), "nakit": ("Cash", 0.90),

    # Insurance
    "mapfre": ("Insurance", 0.99), "sigorta": ("Insurance", 0.92),
    "axa": ("Insurance", 0.97), "allianz": ("Insurance", 0.97),
    "kasko": ("Insurance", 0.95), "dask": ("Insurance", 0.97),

    # Rent & Housing
    "kira": ("Rent", 0.88), "aidat": ("Rent", 0.90),
    "site aidat": ("Rent", 0.95),

    # Finance
    "kredi taksit": ("Finance", 0.92), "taksit": ("Finance", 0.80),
    "faiz": ("Finance", 0.85), "komisyon": ("Finance", 0.85),

    # Tax/Government
    "www.gib.gov.tr": ("Tax", 0.99), "gib.gov": ("Tax", 0.99),
    "vergi": ("Tax", 0.95), "sgk": ("Tax", 0.88),
}

_PATTERN_RULES = [
    (re.compile(r"\batm\b", re.I), "Cash", 0.97),
    (re.compile(r"\bhgs\b", re.I), "Transport", 0.99),
    (re.compile(r"param/marti|marti\.tech", re.I), "Transport", 0.97),
    (re.compile(r"iyzico/istanbulkart|belbim", re.I), "Transport", 0.99),
    (re.compile(r"\b(eczane|pharmacy)\b", re.I), "Health", 0.97),
    (re.compile(r"\b(maaş|salary|maas)\b", re.I), "Income", 0.97),
    (re.compile(r"hesaptan.?ödeme|hesaptan.?aktarim|otomatik.?ödeme", re.I), "Income", 0.92),
    (re.compile(r"satis.?iade|iade", re.I), "Income", 0.90),
    (re.compile(r"\b(sigorta|kasko|dask)\b", re.I), "Insurance", 0.92),
    (re.compile(r"akaryakit|petrol|benzin|opet|\bshell\b|poaş", re.I), "Transport", 0.92),
    (re.compile(r"vodafone|turkcell|türk telekom|turk telekom", re.I), "Telecom", 0.99),
    (re.compile(r"espressolab|kahve|sbx \w+|starbucks", re.I), "Dining", 0.92),
    (re.compile(r"macgal|mahi grup|gms gida|sukas gida|depodan et", re.I), "Groceries", 0.90),
    (re.compile(r"tikla gelsin|tıkla gelsin|param/getir|paycell/getir|s/getir", re.I), "Dining", 0.97),
    (re.compile(r"www\.gib\.gov", re.I), "Tax", 0.99),
    (re.compile(r"iyzico/storytel|storytel", re.I), "Entertainment", 0.97),
    (re.compile(r"zula|orienteer", re.I), "Entertainment", 0.85),
    (re.compile(r"watsons|ozdilek|ozdilekpark", re.I), "Shopping", 0.92),
    (re.compile(r"mc.?donalds|burger king|popeyes|kfc|subway", re.I), "Dining", 0.99),
    (re.compile(r"baruthane|kavurmaci|türk lezzet|turk lezzet|tavuk", re.I), "Dining", 0.90),
    (re.compile(r"nev mekan|büyük ev|buyuk ev|taş.bahçe|btsm ", re.I), "Dining", 0.85),
    (re.compile(r"reformtec", re.I), "Shopping", 0.85),
    (re.compile(r"ennova", re.I), "Health", 0.88),
    (re.compile(r"linkedinprea|linkedin", re.I), "Entertainment", 0.95),
    (re.compile(r"google \*youtube|youtube premium", re.I), "Entertainment", 0.99),
]


def _categorize_single(merchant_raw: str) -> tuple[str, float]:
    name = merchant_raw.lower().strip()
    best_match, best_len = ("Other", 0.0), 0
    for keyword, (cat, conf) in MERCHANT_MAP.items():
        if keyword.lower() in name and len(keyword) > best_len:
            best_match, best_len = (cat, conf), len(keyword)
    if best_match[1] >= 0.75:
        return best_match
    for pattern, cat, conf in _PATTERN_RULES:
        if pattern.search(name):
            return cat, conf
    return "Other", 0.0


def _enrich_with_claude(merchants: list[str]) -> dict[str, str]:
    import urllib.request
    categories = ["Groceries","Dining","Transport","Travel","Shopping","Utilities",
                  "Telecom","Health","Entertainment","Education","Income","Transfer",
                  "Cash","Insurance","Rent","Finance","Tax","Other"]
    prompt = (
        "You are a Turkish bank statement analyst. Categorize each merchant into exactly one category.\n\n"
        f"Categories: {', '.join(categories)}\n\n"
        "These are raw strings from Turkish credit card statements — many are abbreviated or truncated.\n"
        "Merchant names:\n" + "\n".join(f"- {m}" for m in merchants) +
        "\n\nRespond ONLY with valid JSON. Keys = exact merchant names, values = category. No markdown."
    )
    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=payload,
        headers={"Content-Type": "application/json", "anthropic-version": "2023-06-01"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            text = re.sub(r"^```[a-z]*\n?|\n?```$", "", data["content"][0]["text"].strip())
            return json.loads(text)
    except Exception:
        return {}


def _categorize_transactions(transactions: list[Transaction]) -> list[Transaction]:
    unknown = []
    for t in transactions:
        # direction=income → always Income category
        if t.direction == "income":
            t.category = "Income"
            t.confidence = 0.95
            continue
        cat, conf = _categorize_single(t.merchant_raw)
        t.category = cat
        t.confidence = conf
        if cat == "Other":
            unknown.append(t.merchant_raw)

    if unknown:
        unique = list(dict.fromkeys(unknown))
        enriched = _enrich_with_claude(unique)
        if enriched:
            for t in transactions:
                if t.category == "Other" and t.merchant_raw in enriched:
                    t.category = enriched[t.merchant_raw]
                    t.confidence = 0.85

    for t in transactions:
        t.merchant = _clean_merchant_name(t.merchant_raw)
    return transactions


def _clean_merchant_name(raw: str) -> str:
    name = re.sub(r"\b(a\.ş\.|a\.s\.|ltd\.|tic\.|san\.|ins\.|co\.|inc\.)\b", "", raw, flags=re.I)
    name = re.sub(r"KAZANILAN MAX[İI]PUAN[:：][\d,\.]+", "", name, flags=re.I)
    name = re.sub(r"\b(istanbul|istanb|trtr|tr)\b", "", name, flags=re.I)
    name = re.sub(r"[*\-_/|]+$", "", name).strip()
    name = re.sub(r"\s+", " ", name).strip()
    if name.isupper():
        name = name.title()
    return name or raw


def _infer_income(transactions: list[Transaction]) -> IncomeInference:
    income_txns = [t for t in transactions if t.direction == "income" or t.category == "Income"]
    total = sum(t.amount for t in income_txns)
    if not income_txns:
        expenses = [t.amount for t in transactions if t.direction == "expense"]
        if expenses:
            median_exp = sorted(expenses)[len(expenses) // 2]
            candidates = [t for t in transactions if t.amount > 3 * median_exp]
            if candidates:
                best = max(candidates, key=lambda t: t.amount)
                best.direction = "income"
                best.category = "Income"
                return IncomeInference(amount=best.amount, confidence=0.65,
                    explanation=f"Inferred salary: {best.merchant_raw} ({best.amount:,.2f} TRY)")
        return IncomeInference(amount=0.0, confidence=0.3, explanation="No income detected.")
    return IncomeInference(amount=total, confidence=0.92,
        explanation=f"{len(income_txns)} income transaction(s) totalling {total:,.2f} TRY")


def _detect_recurring(transactions: list[Transaction]) -> list[RecurringPayment]:
    by_merchant: dict[str, list[Transaction]] = defaultdict(list)
    for t in transactions:
        if t.direction == "expense":
            by_merchant[t.merchant].append(t)
    recurring = []
    for merchant, txns in by_merchant.items():
        if len(txns) < 2:
            continue
        amounts = [t.amount for t in txns]
        avg = sum(amounts) / len(amounts)
        variance = sum((a - avg) ** 2 for a in amounts) / len(amounts)
        if variance < (avg * 0.25) ** 2:
            dates = sorted(t.date for t in txns)
            gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            avg_gap = sum(gaps) / len(gaps) if gaps else 0
            frequency = ("monthly" if 25 <= avg_gap <= 35 else
                         "weekly" if 5 <= avg_gap <= 9 else
                         "bi-weekly" if 12 <= avg_gap <= 16 else "irregular")
            recurring.append(RecurringPayment(
                merchant=merchant, frequency=frequency,
                avg_amount=round(avg, 2), last_amount=txns[-1].amount,
                last_seen_date=str(dates[-1]),
                confidence=min(0.95, 0.6 + 0.1 * len(txns)),
            ))
    return sorted(recurring, key=lambda r: r.avg_amount, reverse=True)


def analyze_statement(transactions: list[Transaction]) -> AnalysisResult:
    if not transactions:
        raise ValueError("No transactions to analyze.")
    transactions = _categorize_transactions(transactions)
    income = _infer_income(transactions)
    expenses = sum(t.amount for t in transactions if t.direction == "expense")
    income_total = income.amount
    summary = Summary(expenses=round(expenses, 2), income=round(income_total, 2),
                      net=round(income_total - expenses, 2), transaction_count=len(transactions))
    cat_totals: dict[str, float] = defaultdict(float)
    for t in transactions:
        if t.direction == "expense" and t.category not in ("Transfer", "Income"):
            cat_totals[t.category] += t.amount
    total_cat = sum(cat_totals.values()) or 1
    by_category = sorted([
        CategoryBreakdown(category=c, amount=round(a, 2), share=round(a/total_cat, 4))
        for c, a in cat_totals.items()], key=lambda x: x.amount, reverse=True)
    daily: dict[str, float] = defaultdict(float)
    for t in transactions:
        if t.direction == "expense":
            daily[str(t.date)] += t.amount
    daily_spend = [DailySpend(date=d, amount=round(a, 2)) for d, a in sorted(daily.items())]
    dates = [t.date for t in transactions]
    month = f"{min(dates).year}-{min(dates).month:02d}" if dates else "unknown"
    recurring = _detect_recurring(transactions)
    return AnalysisResult(month=month, income=income, summary=summary,
                          by_category=by_category, daily_spend=daily_spend,
                          recurring=recurring, transactions=transactions)