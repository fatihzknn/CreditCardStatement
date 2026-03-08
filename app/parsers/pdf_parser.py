"""PDF statement parser — Ziraat Bankası + İş Bankası (Maximum) formats."""

from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
import pdfplumber
from app.models import Transaction


def _parse_amount(s: str) -> tuple[float, str]:
    s = s.strip()
    direction = "expense"
    if s.endswith("+"):
        direction = "income"
        s = s[:-1]
    elif s.endswith("-"):
        direction = "expense"
        s = s[:-1]

    s = s.replace("TL", "").replace(" ", "").strip()

    if re.search(r"\d\.\d{3}", s) and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.search(r"\d,\d{3}", s) and "." in s:
        s = s.replace(",", "")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")

    s = re.sub(r"[^\d.]", "", s)
    try:
        return abs(float(s)), direction
    except ValueError:
        return 0.0, direction


def _parse_date(s: str) -> datetime | None:
    s = s.strip()
    for fmt in ["%d/%m/%Y", "%d.%m.%Y", "%d/%m/%y"]:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        parts = s.split(".")
        if len(parts) == 3:
            d, m, y = parts
            return datetime.strptime(f"{int(d):02d}.{m}.{y}", "%d.%m.%Y")
    except Exception:
        pass
    return None


def _clean_desc(desc: str) -> str:
    desc = re.sub(r"KAZANILAN MAX[İI]PUAN[:：][\d,\.]+", "", desc, flags=re.I)
    desc = re.sub(r"\(\d+/\d+\s*TK\)\s*[\d.,]+\s*TL", "", desc)
    desc = re.sub(r"\s+", " ", desc).strip()
    return desc


_SKIP_PATTERNS = re.compile(
    r"(önceki aydan devir|kart no\s*:|işlem tarihi|açıklama|tutar|"
    r"sözleşme değişikl|faiz ve ücret|devreden bakiye|büyük mükellef|"
    r"türkiye iş bankası|toplam maxipuan|hesap kesim|son ödeme|"
    r"müşteri numara|kart numara|hesap özeti|asgari ödeme|"
    r"devir bakiyesi|dönem faizi|bankkart|taksit faizi|bsmv|kkdf)",
    re.IGNORECASE,
)

_TX_LINE = re.compile(r"^\d{1,2}[/\.]\d{2}[/\.]\d{4}")


def _extract_tx_lines(text: str) -> list[str]:
    """Extract only transaction lines from page text."""
    return [l.strip() for l in text.splitlines()
            if _TX_LINE.match(l.strip()) and not _SKIP_PATTERNS.search(l)]


def _parse_ziraat_line(line: str) -> Transaction | None:
    m = re.match(r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d.,]+[+-]?)\s*$", line)
    if not m:
        return None
    date_str, desc, amt_str = m.groups()

    desc = re.sub(r"\d[\d.,]*\s*TL\s+İşlemin\s+\d+/\d+\s+Taksidi", "", desc).strip()
    desc = _clean_desc(desc)
    if not desc:
        return None

    dt = _parse_date(date_str)
    if not dt:
        return None

    amount, direction = _parse_amount(amt_str)
    if amount == 0:
        return None

    if re.match(r"^(kredi faizi|taksit faizi|bsmv|kkdf)$", desc, re.I):
        return None

    return Transaction(
        date=dt.date(),
        merchant_raw=desc,
        merchant=desc,
        amount=amount,
        currency="TRY",
        direction=direction,
    )


def _parse_isbank_line(line: str) -> Transaction | None:
    m = re.match(r"^(\d{1,2}\.\d{2}\.\d{4})\s+(.+?)\s+([\d,\.]+[+-])\s*$", line)
    if not m:
        return None
    date_str, desc, amt_str = m.groups()

    desc = _clean_desc(desc)
    if not desc:
        return None

    dt = _parse_date(date_str)
    if not dt:
        return None

    amount, direction = _parse_amount(amt_str)
    if amount == 0:
        return None

    return Transaction(
        date=dt.date(),
        merchant_raw=desc,
        merchant=desc,
        amount=amount,
        currency="TRY",
        direction=direction,
    )


def parse_pdf(path: Path) -> list[Transaction]:
    try:
        with pdfplumber.open(path) as pdf:
            first_text = pdf.pages[0].extract_text() or ""
            is_ziraat = "Bankkart" in first_text or "Ziraat" in first_text
            is_isbank = "MAXİPUAN" in first_text or "Maximum" in first_text or "İş Bankası" in first_text

            # Collect unique page texts — skip pages that are exact duplicates
            # Ziraat sometimes repeats all pages (landscape summary)
            seen_page_signatures: set[str] = set()
            unique_pages: list[str] = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                # Signature = sorted tx lines (order-independent duplicate detection)
                tx_lines = _extract_tx_lines(text)
                signature = "||".join(sorted(tx_lines))
                if signature and signature not in seen_page_signatures:
                    seen_page_signatures.add(signature)
                    unique_pages.append(text)

    except Exception as e:
        raise ValueError(f"PDF okunamadı: {e}") from e

    transactions: list[Transaction] = []
    for text in unique_pages:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or _SKIP_PATTERNS.search(line):
                continue

            tx = None
            if is_ziraat:
                tx = _parse_ziraat_line(line)
            elif is_isbank:
                tx = _parse_isbank_line(line)
            else:
                tx = _parse_ziraat_line(line) or _parse_isbank_line(line)

            if tx is not None:
                transactions.append(tx)

    if not transactions:
        raise ValueError(
            "PDF'den işlem çıkarılamadı. Lütfen bankanızın uygulamasından CSV olarak export edip deneyin."
        )

    return transactions