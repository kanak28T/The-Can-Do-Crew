"""
UrbanPulse — Keep-Warm Ping
============================
Owner : Priyanshu (A1) — Task A1.20

Pings the API /health endpoint periodically to prevent free-tier cloud
instances (Railway, Render, Fly.io) from sleeping during the demo.

Usage:
    python deploy/keep_warm.py [API_URL] [INTERVAL_SECONDS]
"""

import os
import sys
import time
from datetime import datetime, timezone
import requests

DEFAULT_URL = os.getenv("API_URL", "http://localhost:8000")
DEFAULT_INTERVAL = int(os.getenv("PING_INTERVAL", "600"))  # 10 minutes


def ping(url: str = DEFAULT_URL) -> bool:
    target = url.rstrip("/") + "/health"
    try:
        r = requests.get(target, timeout=10)
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        if r.status_code == 200:
            print(f"[{ts}] Ping SUCCESS ({r.status_code}) -> {target} | cells: {r.json().get('cells')}")
            return True
        else:
            print(f"[{ts}] Ping WARN ({r.status_code}) -> {target}")
            return False
    except Exception as e:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        print(f"[{ts}] Ping FAILED -> {target} ({e})")
        return False


def run_loop(url: str = DEFAULT_URL, interval: int = DEFAULT_INTERVAL):
    print(f"[keep-warm] Starting keep-warm loop for {url} every {interval}s")
    while True:
        ping(url)
        time.sleep(interval)


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    interval_s = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_INTERVAL
    run_loop(target_url, interval_s)
