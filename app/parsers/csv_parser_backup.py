"""
Statement parsers — CSV and PDF.

Supports common Turkish bank statement formats:
  - Garanti BBVA, İş Bankası, Yapı Kredi, Akbank, Ziraat, QNB Finansbank
  - Generic fallback for unknown formats

PDF extraction uses pdfplumber (preferred) with PyMuPDF (fitz) as fallback.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from app.models import Transaction

# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

_DATE_PATTERNS = [
    "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d",
    "%d-%m-%Y", "%d/%m/%y", "%d.%m.%y",
    "%Y/%m/%d", "%m/%d/%Y",
]

_TR_MONTHS = {
    "ocak": "01", "şubat": "02", "mart": "03", "nisan": "04",
    "mayıs": "05", "haziran": "06", "temmuz": "07", "ağustos": "08",
    "eylül": "09", "ekim": "10", "kasım": "11", "aralık": "12",
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}


def _parse_date(raw: str) -> Optional[date]:
    raw = raw.strip()
    # Replace Turkish month names
    for name, num in _TR_MONTHS.items():
        raw = raw.lower().replace(name, num)
    raw = raw.strip()
    for fmt in _DATE_PATTERNS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Amount helpers
# ---------------------------------------------------------------------------

def _parse_amount(raw: str) -> Optional[float]:
    """Parse Turkish/European formatted numbers: 1.234,56 or 1,234.56"""
    raw = raw.strip().replace(" ", "").replace("\xa0", "")
    if not raw or raw in ("-", ""):
        return None
    # Detect format: if comma comes after dot → English format
    if re.search(r"\.\d{3},", raw):          # 1.234,56 → Turkish
        raw = raw.replace(".", "").replace(",", ".")
    elif re.search(r",\d{3}\.", raw):         # 1,234.56 → English
        raw = raw.replace(",", "")
    elif "," in raw and "." not in raw:       # 1234,56 → Turkish decimal
        raw = raw.replace(",", ".")
    raw = re.sub(r"[^\d.\-]", "", raw)
    try:
        return float(raw)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# CSV parser
# ---------------------------------------------------------------------------

def _parse_csv(file_path: Path) -> list[Transaction]:
    """
    Parse CSV with automatic column detection.
    Handles BOM, various delimiters (comma, semicolon, tab, pipe).
    """
    raw = file_path.read_bytes()
    # Strip UTF-8 BOM if present
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]

    text = raw.decode("utf-8", errors="replace")
    # Detect delimiter
    sample = text[:2048]
    delimiter = max([",", ";", "\t", "|"], key=lambda d: sample.count(d))

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("CSV has no headers — cannot parse.")

    fields = [f.strip().lower() for f in reader.fieldnames]

    # Map canonical column names
    def find_col(*candidates) -> Optional[str]:
        for c in candidates:
            for f in (reader.fieldnames or []):
                if c in f.strip().lower():
                    return f
        return None

    date_col    = find_col("tarih", "date", "işlem tarihi", "transaction date", "vade")
    merchant_col= find_col("açıklama", "description", "merchant", "işyeri", "detay", "detail", "karşı taraf")
    amount_col  = find_col("tutar", "amount", "işlem tutarı", "transaction amount", "borç", "debit")
    credit_col  = find_col("alacak", "credit", "gelir")
    balance_col = find_col("bakiye", "balance", "kalan")
    currency_col= find_col("para birimi", "currency", "döviz")

    if not date_col or not merchant_col or not amount_col:
        raise ValueError(
            f"Cannot find required columns. Found: {', '.join(reader.fieldnames or [])}. "
            "Expected columns: date, description/merchant, amount."
        )

    transactions: list[Transaction] = []
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
        if amount is None:
            # Try credit column
            credit_str = row.get(credit_col or "", "").strip() if credit_col else ""
            amount = _parse_amount(credit_str) if credit_str else None
        if amount is None:
            continue

        amount = abs(amount)

        # Direction: if separate credit column has a value, it's income
        direction = "expense"
        if credit_col and row.get(credit_col, "").strip():
            credit_val = _parse_amount(row[credit_col])
            if credit_val and credit_val > 0:
                direction = "income"

        # Some banks use negative = income
        raw_signed = _parse_amount(amt_str)
        if raw_signed is not None and raw_signed < 0:
            direction = "income"
            amount = abs(raw_signed)

        balance = None
        if balance_col:
            balance = _parse_amount(row.get(balance_col, ""))

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
        raise ValueError("CSV parsed but no valid transactions found.")
    return transactions


# ---------------------------------------------------------------------------
# PDF parser
# ---------------------------------------------------------------------------

def _extract_text_pdfplumber(file_path: Path) -> str:
    """Extract text from PDF using pdfplumber (preferred)."""
    import pdfplumber
    lines = []
    with pdfplumber.open(str(file_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=3, y_tolerance=3)
            if text:
                lines.append(text)
            # Also try table extraction for tabular statements
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row:
                        lines.append("\t".join(cell or "" for cell in row))
    return "\n".join(lines)


def _extract_text_pymupdf(file_path: Path) -> str:
    """Fallback: extract text using PyMuPDF (fitz)."""
    import fitz  # PyMuPDF
    doc = fitz.open(str(file_path))
    lines = []
    for page in doc:
        lines.append(page.get_text("text"))
    doc.close()
    return "\n".join(lines)


def _extract_pdf_text(file_path: Path) -> str:
    """Try pdfplumber first, fall back to PyMuPDF."""
    try:
        text = _extract_text_pdfplumber(file_path)
        if text.strip():
            return text
    except ImportError:
        pass
    except Exception:
        pass

    try:
        text = _extract_text_pymupdf(file_path)
        if text.strip():
            return text
    except ImportError:
        raise ValueError(
            "No PDF library found. Install pdfplumber: pip install pdfplumber"
        )
    except Exception as e:
        raise ValueError(f"Could not read PDF: {e}")

    raise ValueError("PDF appears to be empty or image-based (scanned). Please use a text-based PDF.")


# Row patterns for common Turkish bank PDFs
# Each pattern: (date_group, merchant_group, amount_group, optional_balance_group)
_PDF_ROW_PATTERNS = [
    # Garanti BBVA: "01/01/2024  MIGROS TICARET  1.234,56"
    re.compile(
        r"(\d{2}[.\/]\d{2}[.\/]\d{4})\s+"
        r"(.+?)\s+"
        r"([\d.,]+)\s*(?:TL|TRY)?\s*"
        r"(?:([\d.,]+)\s*(?:TL|TRY)?)?$",
        re.MULTILINE,
    ),
    # İş Bankası: "01.01.2024 - MERCHANT NAME - 1.234,56 TL"
    re.compile(
        r"(\d{2}\.\d{2}\.\d{4})\s*[-–]\s*"
        r"(.+?)\s*[-–]\s*"
        r"([\d.,]+)\s*(?:TL|TRY)?",
        re.MULTILINE,
    ),
    # Generic: date anywhere followed by amount at end of line
    re.compile(
        r"(\d{2}[.\/\-]\d{2}[.\/\-]\d{2,4})\s+"
        r"(.{3,60}?)\s+"
        r"([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\s*$",
        re.MULTILINE,
    ),
]

_INCOME_KEYWORDS = re.compile(
    r"(maaş|havale gelen|eft gelen|faiz|temettü|kira gelir|alacak|"
    r"salary|transfer in|credit|income|refund|iade)",
    re.IGNORECASE,
)


def _parse_pdf(file_path: Path) -> list[Transaction]:
    text = _extract_pdf_text(file_path)
    transactions: list[Transaction] = []

    for pattern in _PDF_ROW_PATTERNS:
        matches = list(pattern.finditer(text))
        if len(matches) < 3:
            continue  # Not enough matches → try next pattern

        for m in matches:
            raw_date = m.group(1)
            merchant_raw = m.group(2).strip()
            amount_str = m.group(3)
            balance_str = m.group(4) if pattern.groups >= 4 and m.lastindex and m.lastindex >= 4 else None

            parsed_date = _parse_date(raw_date)
            if not parsed_date:
                continue

            amount = _parse_amount(amount_str)
            if amount is None or amount == 0:
                continue
            amount = abs(amount)

            direction = "income" if _INCOME_KEYWORDS.search(merchant_raw) else "expense"
            balance = _parse_amount(balance_str) if balance_str else None

            # Skip header/footer noise
            if re.match(r"^(tarih|date|açıklama|description|tutar|amount)$",
                        merchant_raw.lower()):
                continue

            transactions.append(Transaction(
                date=parsed_date,
                merchant_raw=merchant_raw,
                merchant=merchant_raw,
                amount=amount,
                direction=direction,
                balance=balance,
            ))

        if transactions:
            break  # Found a working pattern

    if not transactions:
        raise ValueError(
            "Could not extract transactions from this PDF. "
            "The format may not be supported yet. Try exporting as CSV from your bank's app."
        )

    return transactions


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_statement(file_path: Path) -> list[Transaction]:
    """
    Parse a credit card statement file (CSV or PDF).
    Returns a list of Transaction objects.
    Raises ValueError with a user-friendly message on failure.
    """
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return _parse_csv(file_path)
    elif suffix == ".pdf":
        return _parse_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Please upload a CSV or PDF.")