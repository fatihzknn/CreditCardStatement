"""FastAPI application entry point."""

import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import UPLOAD_DIR, STATIC_DIR
from app.db import save_transactions, save_upload
from app.models import AnalysisResult
from app.parsers import parse_statement
from app.services import analyze_statement

app = FastAPI(title="Credit Card Statement Analyzer", version="0.1.0")

# Serve static files
static_dir = STATIC_DIR
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the main page."""
    return FileResponse(static_dir / "index.html")


@app.post("/api/upload")
async def upload_statement(file: UploadFile = File(...)):
    """
    Upload a credit card statement (CSV or PDF) and return analysis.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".csv", ".pdf"):
        raise HTTPException(400, "Only CSV and PDF files are supported.")

    # Save to uploads
    UPLOAD_DIR.mkdir(exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = UPLOAD_DIR / unique_name

    try:
        with file_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(500, f"Failed to save file: {e}")

    try:
        transactions = parse_statement(file_path)
    except ValueError as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(400, str(e))
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(500, f"Parsing error: {e}")

    # Analyze
    result = analyze_statement(transactions)

    # Persist (optional for MVP)
    try:
        upload_id = save_upload(file.filename or unique_name, str(file_path), result.month)
        save_transactions(upload_id, result.transactions)
    except Exception:
        pass  # Non-fatal

    return result.model_dump()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
