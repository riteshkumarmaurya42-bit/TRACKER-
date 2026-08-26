#!/usr/bin/env python3
"""
Shared helpers for TRACKER- scrapers.

Used by minecraft_scraper.py and bgmi_scraper.py. Standard library only so
the GitHub Actions workflow needs no dependencies to install.
"""

import json
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER_AGENT = (
    "TRACKER-/1.0 (GitHub Actions; "
    "+https://github.com/riteshkumarmaurya42-bit/TRACKER-)"
)


def utcnow_iso():
    """Current UTC time as an ISO-8601 string with 'Z' suffix."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def fetch_url(url, timeout=20, headers=None):
    """Fetch a URL and return the response text (or None on failure)."""
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    req = Request(url, headers=h)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError, OSError, ValueError) as e:
        print(f"[WARN] fetch failed {url}: {e}", file=sys.stderr)
        return None


def fetch_json(url, timeout=20, headers=None):
    """Fetch a URL and parse it as JSON (or None on failure)."""
    text = fetch_url(url, timeout=timeout, headers=headers)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"[WARN] invalid JSON from {url}", file=sys.stderr)
        return None


def read_json(path):
    """Read a JSON file, returning None if missing or malformed."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def write_json(path, data):
    """Atomically write a JSON file (tmp file + rename)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    import os
    os.replace(tmp, path)
