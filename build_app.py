#!/usr/bin/env python3
"""
Build standalone app for macOS and Windows.
Run: python build_app.py

Output:
  - dist/StatementAnalyzer (macOS) or dist/StatementAnalyzer.exe (Windows)
  - On macOS, optionally create StatementAnalyzer.app bundle
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=PROJECT_ROOT)


def main():
    if "venv" in sys.executable or "VIRTUAL_ENV" in os.environ:
        pip = "pip"
        py = sys.executable
    else:
        pip = f"{sys.executable} -m pip"
        py = sys.executable

    # Use project-local PyInstaller cache (avoids permission issues)
    cache_dir = PROJECT_ROOT / "build" / "pyinstaller_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["PYINSTALLER_CONFIG_DIR"] = str(cache_dir)

    # Install PyInstaller if needed
    run([py, "-m", "pip", "install", "pyinstaller", "-q"])

    # Build
    run([py, "-m", "PyInstaller", "--clean", "--noconfirm", "statement_analyzer.spec"])

    dist = PROJECT_ROOT / "dist"
    if not dist.exists():
        print("Build failed: dist/ not found")
        sys.exit(1)

    plat = platform.system()
    if plat == "Darwin":
        exe = dist / "StatementAnalyzer"
        if exe.exists():
            print(f"\n✓ macOS app built: {exe}")
            print("  Double-click or run from terminal: ./dist/StatementAnalyzer")
            # Create .app bundle for macOS
            app_dir = dist / "StatementAnalyzer.app"
            app_dir.mkdir(exist_ok=True)
            (app_dir / "Contents").mkdir(exist_ok=True)
            (app_dir / "Contents/MacOS").mkdir(exist_ok=True)
            shutil.copy(exe, app_dir / "Contents/MacOS/StatementAnalyzer")
            (app_dir / "Contents/MacOS/StatementAnalyzer").chmod(0o755)
            plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>StatementAnalyzer</string>
  <key>CFBundleIdentifier</key>
  <string>com.creditcard.analyzer</string>
  <key>CFBundleName</key>
  <string>Statement Analyzer</string>
</dict>
</plist>'''
            (app_dir / "Contents/Info.plist").write_text(plist)
            print(f"  macOS .app bundle: {app_dir}")
    elif plat == "Windows":
        exe = dist / "StatementAnalyzer.exe"
        if exe.exists():
            print(f"\n✓ Windows app built: {exe}")
            print("  Double-click to run.")
    else:
        print(f"\n✓ Built for {plat}: {dist / 'StatementAnalyzer'}")

    print("\nShare the file in dist/ with your friends. No Python needed!")


if __name__ == "__main__":
    main()
