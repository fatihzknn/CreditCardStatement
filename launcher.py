#!/usr/bin/env python3
"""
Launcher for Credit Card Statement Analyzer.
Starts the FastAPI server and opens the default browser.
Use this when packaging as a standalone app for macOS/Windows.
"""

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# For PyInstaller: ensure bundle dir is on path
if getattr(sys, "frozen", False):
    bundle_dir = Path(sys._MEIPASS)
    if str(bundle_dir) not in sys.path:
        sys.path.insert(0, str(bundle_dir))
    os.chdir(bundle_dir)
else:
    os.chdir(Path(__file__).resolve().parent)

PORT = 8000
URL = f"http://127.0.0.1:{PORT}"


def run_server():
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=PORT,
        log_level="warning",
    )


def main():
    print("Starting Credit Card Statement Analyzer...")
    print(f"Server will run at {URL}")
    print("Press Ctrl+C to stop.\n")

    server = threading.Thread(target=run_server, daemon=True)
    server.start()

    # Wait for server to be ready
    for _ in range(30):
        try:
            import urllib.request
            urllib.request.urlopen(URL, timeout=1)
            break
        except Exception:
            time.sleep(0.3)
    else:
        print("Server failed to start. Check if port 8000 is in use.")
        sys.exit(1)

    webbrowser.open(URL)
    print("Browser opened. Close this window or press Ctrl+C to stop the server.")

    try:
        server.join()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
