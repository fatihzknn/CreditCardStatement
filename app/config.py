"""App configuration."""

import os
import sys
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# When packaged (PyInstaller), use writable user dir for uploads/DB
if getattr(sys, "frozen", False):
    _bundle_dir = Path(sys._MEIPASS)
    _user_data = Path.home() / ".creditcard-analyzer"
    _user_data.mkdir(exist_ok=True)
    UPLOAD_DIR = _user_data / "uploads"
    UPLOAD_DIR.mkdir(exist_ok=True)
    SAMPLE_DATA_DIR = _user_data / "sample_data"
    SAMPLE_DATA_DIR.mkdir(exist_ok=True)
    STATIC_DIR = _bundle_dir / "static"
    DB_PATH = _user_data / "statement_analyzer.db"
else:
    UPLOAD_DIR = PROJECT_ROOT / "uploads"
    SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"
    STATIC_DIR = PROJECT_ROOT / "static"
    DB_PATH = PROJECT_ROOT / "statement_analyzer.db"
    UPLOAD_DIR.mkdir(exist_ok=True)
    SAMPLE_DATA_DIR.mkdir(exist_ok=True)
