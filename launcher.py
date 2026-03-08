#!/usr/bin/env python3
"""
Launcher for Credit Card Statement Analyzer.
Starts the FastAPI server and opens the default browser.
Use this when packaging as a standalone app for macOS/Windows.

Friends on the same WiFi can access via the printed LAN URL.
"""

import os
import socket
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


def get_lan_ip() -> str:
    """Get the machine's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def run_server():
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",   # Bind to all interfaces → LAN accessible
        port=PORT,
        log_level="warning",
    )


def wait_for_server(url: str, retries: int = 30) -> bool:
    import urllib.request
    for _ in range(retries):
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def kill_port(port: int) -> None:
    """Kill any process already using the port."""
    import subprocess
    try:
        result = subprocess.run(
            ["lsof", "-t", f"-i:{port}"],
            capture_output=True, text=True
        )
        pids = result.stdout.strip().split()
        for pid in pids:
            if pid:
                subprocess.run(["kill", "-9", pid], capture_output=True)
                print(f"  Eski process durduruldu (PID {pid})")
    except Exception:
        pass  # Windows veya lsof yoksa geç


def main():
    lan_ip = get_lan_ip()
    local_url = f"http://127.0.0.1:{PORT}"
    lan_url   = f"http://{lan_ip}:{PORT}"

    print("=" * 52)
    print("   Credit Card Statement Analyzer")
    print("=" * 52)

    # Eski process varsa öldür
    kill_port(PORT)
    print(f"  Local:   {local_url}")
    print(f"  Network: {lan_url}  ← share with friends on same WiFi")
    print("=" * 52)
    print("  Press Ctrl+C to stop.\n")

    server = threading.Thread(target=run_server, daemon=True)
    server.start()

    if not wait_for_server(local_url):
        print("ERROR: Server failed to start. Is port 8000 already in use?")
        sys.exit(1)

    webbrowser.open(local_url)
    print("Browser opened. Server is running.\n")

    try:
        server.join()
    except KeyboardInterrupt:
        print("\nStopping server. Goodbye!")


if __name__ == "__main__":
    main()