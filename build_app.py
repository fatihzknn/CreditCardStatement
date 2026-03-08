#!/usr/bin/env python3
"""
macOS .app builder for Credit Card Statement Analyzer.

Kullanım:
    python build_app.py

Çıktı:
    dist/StatementAnalyzer.app  ← arkadaşlara bu klasörü zip'leyip gönder
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> None:
    print("►", " ".join(cmd))
    subprocess.check_call(cmd, cwd=PROJECT_ROOT)


def main():
    if platform.system() != "Darwin":
        print("Bu script sadece macOS'ta çalışır.")
        sys.exit(1)

    py = sys.executable
    print("\n=== Adım 1: Gerekli kütüphaneler yükleniyor ===")
    run([py, "-m", "pip", "install", "-q",
         "pyinstaller", "fastapi", "uvicorn[standard]",
         "pdfplumber", "pymupdf", "pydantic"])

    # PyInstaller cache
    cache_dir = PROJECT_ROOT / "build" / "pyinstaller_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["PYINSTALLER_CONFIG_DIR"] = str(cache_dir)

    print("\n=== Adım 2: .app build ediliyor (2-3 dakika sürebilir) ===")
    run([py, "-m", "PyInstaller", "--clean", "--noconfirm",
         "statement_analyzer.spec"])

    app_path = PROJECT_ROOT / "dist" / "StatementAnalyzer.app"
    if not app_path.exists():
        # Fallback: spec yoksa direkt build et
        print("Spec dosyası bulunamadı, direkt build yapılıyor...")
        run([py, "-m", "PyInstaller",
             "--clean", "--noconfirm", "--onefile",
             "--name", "StatementAnalyzer",
             "--add-data", f"{PROJECT_ROOT / 'static'}:static",
             "--collect-all", "pdfplumber",
             "--collect-all", "pdfminer",
             "--collect-all", "uvicorn",
             "--collect-all", "fastapi",
             "--hidden-import", "fitz",
             "--hidden-import", "sqlite3",
             "--console",
             "launcher.py"])

    # .app bundle oluştur
    exe_path = PROJECT_ROOT / "dist" / "StatementAnalyzer"
    if exe_path.exists() and not app_path.exists():
        print("\n=== Adım 3: .app bundle oluşturuluyor ===")
        app_path.mkdir(parents=True, exist_ok=True)
        (app_path / "Contents" / "MacOS").mkdir(parents=True, exist_ok=True)
        (app_path / "Contents" / "Resources").mkdir(parents=True, exist_ok=True)

        shutil.copy(exe_path, app_path / "Contents" / "MacOS" / "StatementAnalyzer")
        (app_path / "Contents" / "MacOS" / "StatementAnalyzer").chmod(0o755)

        plist = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>      <string>StatementAnalyzer</string>
  <key>CFBundleIdentifier</key>      <string>com.creditcard.analyzer</string>
  <key>CFBundleName</key>            <string>Statement Analyzer</string>
  <key>CFBundleDisplayName</key>     <string>Statement Analyzer</string>
  <key>CFBundleVersion</key>         <string>1.0.0</string>
  <key>CFBundleShortVersionString</key> <string>1.0.0</string>
  <key>NSHighResolutionCapable</key> <true/>
</dict>
</plist>"""
        (app_path / "Contents" / "Info.plist").write_text(plist)

    # Zip for sharing
    zip_path = PROJECT_ROOT / "dist" / "StatementAnalyzer_macOS"
    shutil.make_archive(str(zip_path), "zip", str(PROJECT_ROOT / "dist"),
                        "StatementAnalyzer.app")

    print(f"""
╔══════════════════════════════════════════════════════╗
║  ✅  Build tamamlandı!                               ║
╠══════════════════════════════════════════════════════╣
║  📁  dist/StatementAnalyzer.app                      ║
║  📦  dist/StatementAnalyzer_macOS.zip  ← bunu gönder ║
╠══════════════════════════════════════════════════════╣
║  Arkadaşlara söyleyeceklerin:                        ║
║  1. Zip'i aç                                         ║
║  2. StatementAnalyzer.app'e SAĞ TIKLA → "Aç"         ║
║  3. "Yine de Aç" butonuna bas                        ║
║  4. Terminalde URL görünür, tarayıcı açılır          ║
╚══════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()