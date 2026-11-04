"""Explicit SEC fetch command and hash-verified local snapshot loading."""

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from . import config as cfg


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_path() -> Path:
    return cfg.RAW / "edgar" / "manifest.json"


def read_manifest() -> list[dict]:
    path = manifest_path()
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def snapshot(url: str, name: str, user_agent: str, opener=urlopen) -> dict:
    if "example.com" in user_agent or "@" not in user_agent:
        raise ValueError("Set SEC_USER_AGENT to a descriptive name and actual contact email.")
    if cfg.REQUEST_INTERVAL <= .1:
        raise ValueError("SEC requests must remain below ten per second.")
    request = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    with opener(request, timeout=cfg.REQUEST_TIMEOUT) as response:
        raw = response.read()
    payload = json.loads(raw)
    retrieved = datetime.now(timezone.utc)
    digest = hashlib.sha256(raw).hexdigest()
    folder = manifest_path().parent
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{name}_{retrieved:%Y%m%dT%H%M%S%fZ}_{digest[:12]}.json"
    path = folder / filename
    path.write_bytes(raw)
    record = {"name": name, "url": url, "retrieved_at": retrieved.isoformat(),
              "sha256": digest, "path": filename}
    records = read_manifest()
    records.append(record)
    manifest_path().write_text(json.dumps(records, indent=2), encoding="utf-8")
    return payload


def resolve_ciks(tickers: dict, requested=cfg.TICKERS) -> dict[str, int]:
    lookup = {row["ticker"].upper(): int(row["cik_str"]) for row in tickers.values()}
    missing = set(requested) - lookup.keys()
    if missing:
        raise ValueError(f"Tickers absent from SEC directory: {sorted(missing)}")
    return {ticker: lookup[ticker] for ticker in requested}


def fetch_all(user_agent=cfg.SEC_USER_AGENT) -> None:
    directory = snapshot(cfg.SEC_TICKERS_URL, "company_tickers", user_agent)
    for ticker, cik in resolve_ciks(directory).items():
        time.sleep(cfg.REQUEST_INTERVAL)
        snapshot(cfg.SEC_FACTS_URL.format(cik=cik), ticker, user_agent)


def load_snapshot(ticker: str) -> tuple[dict, dict]:
    records = [row for row in read_manifest() if row["name"] == ticker]
    if not records:
        raise FileNotFoundError(f"No SEC snapshot for {ticker}. Run credit_pack.edgar separately.")
    record = max(records, key=lambda row: row["retrieved_at"])
    # Paths are stored relative to the manifest folder so snapshots stay portable.
    folder = manifest_path().parent.resolve()
    path = folder / record["path"]
    if not path.resolve().is_relative_to(folder):
        raise ValueError("Snapshot manifest path escapes the snapshot folder.")
    if sha256(path) != record["sha256"]:
        raise ValueError(f"Snapshot SHA-256 mismatch: {path.name}")
    return json.loads(path.read_text(encoding="utf-8")), record


if __name__ == "__main__":
    # Env override keeps a real contact email out of the public repo.
    fetch_all(os.environ.get("SEC_USER_AGENT", cfg.SEC_USER_AGENT))
