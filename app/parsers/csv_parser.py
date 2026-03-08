"""CSV statement parser."""
from __future__ import annotations
import csv, io, re
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from app.models import Transaction

_DATE_PATTERNS = ["%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%d.%m.%y"]
_TR_MONTHS = {
    "ocak": "01", "subat": "02", "mart": "03", "nisan": "04",
    "mayis": "05", "haziran": "06", "temmuz": "07", "agustos": "08",
    "eylul": "09", "ekim": "10", "kasim": "11", "aralik": "12",
}


def _parse_date(raw: str) -> Optional[date]:
    s = raw.strip().lower()
    for name, num in _TR_MONTHS.items():
        s = s.replace(name, num)
    for fmt in _DATE_PATTERNS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(raw: str) -> Optional[float]:
    s = raw.strip().replace(" ", "").replace("\xa0", "")
    if not s or s == "-":
        return None
    if re.search(r"\.\d{3},", s):
        s = s.replace(".", "").replace(",", ".")
    elif re.search(r",\d{3}\.", s):
        s = s.replace(",", "")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def _find_col(fieldnames, *candidates):
    for c in candidates:
        for f in fieldnames:
            if c in f.strip().lower():
                return f
    return None


def parse_csv(file_path: Path) -> list[Transaction]:
    raw = file_path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8", errors="replace")
    sample = text[:2048]
    delimiter = max([",", ";", "\t", "|"], key=lambda d: sample.count(d))
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("CSV baslik satiri bulunamadi.")
    fn = list(reader.fieldnames)
    date_col     = _find_col(fn, "tarih", "date", "islem tarihi", "transaction date", "vade")
    merchant_col = _find_col(fn, "aciklama", "description", "merchant", "isyeri", "detay", "detail")
    amount_col   = _find_col(fn, "tutar", "amount", "islem tutari", "transaction amount", "borc", "debit")
    credit_col   = _find_col(fn, "alacak", "credit", "gelir")
    balance_col  = _find_col(fn, "bakiye", "balance", "kalan")
    currency_col = _find_col(fn, "para birimi", "currency", "doviz")
    if not date_col or not merchant_col or not amount_col:
        raise ValueError(f"Gerekli sutunlar bulunamadi. Bulunanlar: {', '.join(fn)}")
    transactions = []
    for row in reader:
        raw_date = row.get(date_col, "").strip()
        if not raw_date:
            continue
        parsed_date = _parse_date(raw_date)
        if not parsed_date:
            continue
        merchant_raw = row.get(merchant_col, "").strip()
        amt_str = row.get(amount_col, "").strip()
        amount = _parse_amount(amt_str)
        if amount is None and credit_col:
            amount = _parse_amount(row.get(credit_col, ""))
        if amount is None:
            continue
        direction = "expense"
        if amount < 0:
            direction, amount = "income", abs(amount)
        elif credit_col and row.get(credit_col, "").strip():
            cv = _parse_amount(row[credit_col])
            if cv and cv > 0:
                direction = "income"
        else:
            amount = abs(amount)
        balance = _parse_amount(row.get(balance_col, "")) if balance_col else None
        currency = "TRY"
        if currency_col:
            c = row.get(currency_col, "").strip().upper()
            if c:
                currency = c
        transactions.append(Transaction(
            date=parsed_date,
            merchant_raw=merchant_raw,
            merchant=merchant_raw,
            amount=amount,
            currency=currency,
            direction=direction,
            balance=balance,
        ))
    if not transactions:
        raise ValueError("CSV parse edildi ama hic islem bulunamadi.")
    return transactions