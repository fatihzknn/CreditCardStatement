# Credit Card Statement Analyzer

An MVP web app that parses credit card statements (CSV or PDF), groups expenses by category, normalizes merchant names, detects recurring payments/subscriptions, and infers monthly income.

## Setup

```bash
cd CreditcardStatement
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

**Option A — Developer (with Python):**
```bash
uvicorn app.main:app --reload
```

**Option B — Standalone app (no Python needed):**
```bash
python build_app.py
```
Then run `dist/StatementAnalyzer` (macOS) or `dist/StatementAnalyzer.exe` (Windows). The app starts the server and opens your browser automatically. Share the executable with friends — they don't need Python installed.

- **macOS**: Build on a Mac to get `StatementAnalyzer` and `StatementAnalyzer.app`.
- **Windows**: Build on a Windows machine to get `StatementAnalyzer.exe`.

Visit http://localhost:8000 and upload a statement file.

## UI Features

- **Tabs**: Overview, Categories, Daily Spending, Recurring, Other, All Transactions — click to switch views.
- **Click a day on the chart**: The daily spending chart is interactive. Click any data point to see that day's transactions in a modal.

## How Parsing Works

### CSV

- **Column detection**: Automatically detects columns by common names (EN/TR):
  - Date: `date`, `tarih`, `transaction_date`, `islem_tarihi`
  - Description: `description`, `aciklama`, `merchant`, `details`
  - Amount: `amount`, `tutar`, `debit`, `credit`
  - Balance: `balance`, `bakiye`
- **Direction**: Negative amounts = expense, positive = income. If separate debit/credit columns exist, both are used.
- **Date formats**: `YYYY-MM-DD`, `DD.MM.YYYY`, `DD/MM/YYYY`, etc.

### PDF

- **Best-effort**: Uses `pdfplumber` to extract tables from each page.
- **Fallback**: If extraction fails or returns no transactions, a clear error asks the user to export CSV instead.
- **Limitations**: Complex PDF layouts, scanned documents, or non-tabular statements may not parse correctly.

### Expected Statement Formats

**CSV example:**

| date       | description           | amount   | currency |
|------------|-----------------------|----------|----------|
| 2024-02-01 | MAAŞ ÖDEMESİ          | 45000.00 | TRY      |
| 2024-02-02 | MIGROS MARKET         | -125.50  | TRY      |

- At least: date, description, amount.
- Amount: negative for expenses, positive for income/credits (or use separate debit/credit columns).

## Assumptions & Limitations

1. **Single currency**: Assumes one primary currency per statement (default TRY).
2. **Monthly view**: Analysis is per-statement; multi-month PDFs are treated as one period.
3. **Income inference**: Heuristic-based (salary keywords, largest recurring credit). No bank integration.
4. **Merchant normalization**: Rules-based alias map. Extensible via `MERCHANT_ALIASES` in `app/services/merchant.py`.
5. **Categorization**: Keyword rules only. "Other" used when no match; confidence shown.
6. **Recurring detection**: Requires ≥2 similar charges (within 15% amount tolerance) from same merchant.
7. **No auth**: Local use only; no user accounts.

## Project Structure

```
CreditcardStatement/
├── app/
│   ├── main.py          # FastAPI app, upload endpoint
│   ├── models.py        # Pydantic schemas
│   ├── config.py
│   ├── db.py            # SQLite persistence
│   ├── parsers/
│   │   ├── base.py      # parse_statement()
│   │   ├── csv_parser.py
│   │   └── pdf_parser.py
│   └── services/
│       ├── analyzer.py  # Orchestrator
│       ├── merchant.py  # Normalization
│       ├── categorizer.py
│       ├── recurring.py
│       └── income.py
├── static/
│   └── index.html       # Single-page UI
├── sample_data/
│   └── sample_statement.csv
├── tests/
├── requirements.txt
└── README.md
```

## Output Schema

```json
{
  "month": "YYYY-MM",
  "income": {"amount": 0, "confidence": 0.0, "explanation": "string"},
  "summary": {"expenses": 0, "income": 0, "net": 0, "transaction_count": 0},
  "by_category": [{"category": "Restaurants", "amount": 0, "share": 0.0}],
  "daily_spend": [{"date": "YYYY-MM-DD", "amount": 0}],
  "recurring": [{"merchant": "Netflix", "frequency": "monthly", "avg_amount": 0, "last_amount": 0, "confidence": 0.0}],
  "transactions": [...]
}
```

## Tests

```bash
pytest tests/ -v
```

## Sample Data

Use `sample_data/sample_statement.csv` to verify the app. It contains anonymized Turkish-style transactions (salary, groceries, subscriptions, etc.).
