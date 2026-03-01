"""Base parser and statement parsing entry point."""

from pathlib import Path
from typing import Union

from app.models import Transaction
from app.parsers.csv_parser import parse_csv
from app.parsers.pdf_parser import parse_pdf


def parse_statement(file_path: Union[str, Path]) -> list[Transaction]:
    """
    Parse a credit card statement file (CSV or PDF).
    Returns list of Transaction objects in canonical schema.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return parse_csv(path)
    elif suffix == ".pdf":
        return parse_pdf(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use CSV or PDF.")
