"""Explicit optional source download. Never imported by the offline library."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import time

# CONFIG: raw downloads, timeout, throttle, and primary source documents.
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data" / "extension" / "raw"
MANIFEST = OUTPUT / "manifest.json"
TIMEOUT = 30
INTERVAL = 1.0
SOURCES = {
    "apple_2025.html": "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm",
    "jpm_2025.html": "https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm",
    "dutchess_2025.html": "https://www.dutchessny.gov/Departments/Comptroller/Independent-Audit-of-Basic-Financial-Statements-for-2025.htm",
    "water_2025.pdf": "https://www.nyc.gov/assets/nycwaterboard/downloads/pdf/statements_and_reports/wb-financial-statements-2025.pdf",
    "rule_2a7.html": "https://www.ecfr.gov/current/title-17/chapter-II/part-270/section-270.2a-7",
}


def main():
    agent = os.environ.get("SEC_USER_AGENT", "")
    if "@" not in agent or "example.com" in agent:
        raise ValueError("Set SEC_USER_AGENT to an organization and actual contact email.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []
    failures = []
    for filename, url in SOURCES.items():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        record = {"url": url, "attempted_at": datetime.now(timezone.utc).isoformat()}
        try:
            with urlopen(Request(url, headers={"User-Agent": agent}), timeout=TIMEOUT) as response:
                raw = response.read()
            path = OUTPUT / f"{stamp}_{filename}"
            path.write_bytes(raw)
            record.update({"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(raw).hexdigest(),
                           "retrieved_at": datetime.now(timezone.utc).isoformat(), "status": "downloaded"})
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            record.update({"status": "failed", "error": str(error), "retrieved_at": None})
            failures.append(filename)
        records.append(record)
        MANIFEST.write_text(json.dumps(records, indent=2), encoding="utf-8")
        time.sleep(INTERVAL)
    if failures:
        raise SystemExit(f"Source download failed: {', '.join(failures)}")


if __name__ == "__main__":
    main()
