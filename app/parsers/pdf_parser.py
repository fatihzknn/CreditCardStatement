"""PDF statement parser tailored for Turkish bank statements (incl. sample)."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pdfplumber

from app.models import Transaction


def _parse_amount_str(amount_str: str) -> float:
    """
    Parse amount from strings like:
    - 2,034.96-
    - 25,000.00+
    - 123,45

    Handles thousand separators and Turkish/EN decimal formats.
    Always returns a signed float.
    """
    if amount_str is None:
        return 0.0

    s = str(amount_str).strip()
    if not s:
        return 0.0

    # Extract sign from trailing +/- if present
    sign = 1.0
    if s.endswith("-"):
        sign = -1.0
        s = s[:-1]
    elif s.endswith("+"):
        sign = 1.0
        s = s[:-1]

    # Remove currency text and spaces
    s = s.replace("TL", "").replace("tl", "").strip()

    # If both ',' and '.' exist -> assume ',' thousands, '.' decimal (e.g. 25,000.00)
    if "," in s and "." in s:
        s = s.replace(",", "")
    # If only ',' present -> treat as decimal separator (Turkish style)
    elif "," in s and "." not in s:
        s = s.replace(".", "").replace(",", ".")
    # Else only '.' or digits -> standard float

    # Keep only digits and decimal point
    s = re.sub(r"[^0-9.]", "", s)
    try:
        val = float(s) if s else 0.0
    except ValueError:
        return 0.0
    return sign * val


def _parse_date(val) -> datetime | None:
    """Parse date from string."""
    if val is None:
        return None
    s = str(val).strip()[:10]
    for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _clean_description(desc: str) -> str:
    """Strip noisy suffixes like MaxiPuan details."""
    if not desc:
        return ""
    # Remove "KAZANILAN MAXIPUAN:..." fragments
    desc = re.sub(
        r"KAZANILAN MAX[İI]PUAN[:：].*",
        "",
        desc,
        flags=re.IGNORECASE,
    )
    # Collapse whitespace
    desc = re.sub(r"\s+", " ", desc).strip()
    return desc


def _parse_transaction_line(line: str) -> Transaction | None:
    """
    Parse a single statement line in the format seen in sample PDF, e.g.:

    19.02.2026 MAPFRE SIGORTA A(2/9 TK) 18,314.62 TL 2,034.96-
    9.02.2026 2000-3816259 HESAPTAN AKTARIM 2000 İNTERAKTİF 25,000.00+
    2.02.2026 SAKARYA ADAPAZARI AGORA SAKARYA TR 18.00-
    """
    line = line.strip()
    if not line:
        return None

    # Date at start of line
    m = re.match(r"^(\d{1,2}\.\d{1,2}\.\d{4})\s+(.+)$", line)
    if not m:
        return None

    date_str, rest = m.groups()
    dt = _parse_date(date_str)
    if not dt:
        return None

    # Amount is the last numeric chunk with optional +/- at the end
    # e.g. "... 2,034.96-" or "... 25,000.00+"
    amt_match = re.search(r"([0-9][0-9.,]*[+-])\s*$", rest)
    if not amt_match:
        # Sometimes sign may be separated by space: "25,000.00 +"
        amt_match = re.search(r"([0-9][0-9.,]*)\s*([+-])\s*$", rest)
        if not amt_match:
            return None
        amount_str = amt_match.group(1) + amt_match.group(2)
        desc_part = rest[: amt_match.start()].rstrip()
    else:
        amount_str = amt_match.group(1)
        desc_part = rest[: amt_match.start()].rstrip()

    amount = _parse_amount_str(amount_str)
    if amount == 0:
        return None

    desc = _clean_description(desc_part)
    if not desc:
        return None

    direction = "expense" if amount < 0 else "income"

    return Transaction(
        date=dt.date(),
        merchant_raw=desc,
        amount=amount,
        currency="TRY",
        direction=direction,
    )


def parse_pdf(path: Path) -> list[Transaction]:
    """
    Parse PDF credit card statement.

    Uses a text-based parser tailored for Turkish card statements, but
    will treat *any* line that starts with a date (dd.MM.yyyy) as a
    potential transaction. This makes it more robust across different
    banks/layouts as long as the PDF contains real text (not scanned
    images).
    """
    transactions: list[Transaction] = []

    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for raw_line in text.splitlines():
                    line = raw_line.strip()
                    if not line:
                        continue

                    # Skip obvious non-transaction / legal text
                    upper = line.upper()
                    if line.startswith("*") or "TÜRKİYE İŞ BANKASI" in upper:
                        continue
                    if line.startswith("--") and "OF" in upper:
                        # page marker like \"-- 1 of 2 --\"
                        continue

                    # Try to parse any date-prefixed line as a transaction
                    tx = _parse_transaction_line(line)
                    if tx is not None:
                        transactions.append(tx)

    except Exception as e:
        raise ValueError(
            f"PDF parsing failed: {e}. Please export your statement as CSV and upload that instead."
        ) from e

    if not transactions:
        raise ValueError(
            "No transactions could be extracted from the PDF. "
            "Please export your statement as CSV and upload that instead."
        )

    return transactions
