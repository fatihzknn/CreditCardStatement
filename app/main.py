"""FastAPI application — multi-bank upload support."""

import shutil, uuid
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile, Form
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import UPLOAD_DIR, STATIC_DIR
from app.db import save_transactions, save_upload
from app.models import AnalysisResult
from app.parsers import parse_statement
from app.services import analyze_statement

app = FastAPI(title="Credit Card Statement Analyzer", version="0.2.0")

static_dir = STATIC_DIR
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    response = FileResponse(static_dir / "index.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.post("/api/upload")
async def upload_statement(file: UploadFile = File(...)):
    """Single file upload (legacy)."""
    return await _process_file(file)


@app.post("/api/upload-multi")
async def upload_multi(files: List[UploadFile] = File(...)):
    """
    Upload multiple bank statements and merge them.
    Returns combined analysis across all files.
    """
    if not files:
        raise HTTPException(400, "No files provided.")
    if len(files) > 10:
        raise HTTPException(400, "Maximum 10 files at once.")

    all_transactions = []

    for file in files:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in (".csv", ".pdf"):
            raise HTTPException(400, f"{file.filename}: Only CSV and PDF supported.")

        UPLOAD_DIR.mkdir(exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}{suffix}"
        file_path = UPLOAD_DIR / unique_name

        try:
            with file_path.open("wb") as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            raise HTTPException(500, f"Failed to save {file.filename}: {e}")

        try:
            transactions = parse_statement(file_path)
            all_transactions.extend(transactions)
        except ValueError as e:
            file_path.unlink(missing_ok=True)
            raise HTTPException(400, f"{file.filename}: {e}")
        except Exception as e:
            file_path.unlink(missing_ok=True)
            raise HTTPException(500, f"Parsing error in {file.filename}: {e}")

    if not all_transactions:
        raise HTTPException(400, "No transactions found in uploaded files.")

    # Sort by date across all files
    all_transactions.sort(key=lambda t: t.date)

    result = analyze_statement(all_transactions)

    try:
        upload_id = save_upload("multi-upload", "", result.month)
        save_transactions(upload_id, result.transactions)
    except Exception:
        pass

    return result.model_dump()


async def _process_file(file: UploadFile) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".csv", ".pdf"):
        raise HTTPException(400, "Only CSV and PDF files are supported.")

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

    result = analyze_statement(transactions)

    try:
        upload_id = save_upload(file.filename or unique_name, str(file_path), result.month)
        save_transactions(upload_id, result.transactions)
    except Exception:
        pass

    return result.model_dump()