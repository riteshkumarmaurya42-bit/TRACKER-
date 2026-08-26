#!/usr/bin/env python3
"""
BGMI (Battlegrounds Mobile India) Tracker Scraper

Fetches live data from:
  - Official site news/updates pages (season, version, event dates)
  - Server reachability probes (login, match, shop, news)

Every section records when it was last successfully checked so the dashboard
can show real freshness. If a live source is unavailable the previous values
are kept (graceful degradation).
"""

import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import fetch_url, read_json, utcnow_iso, write_json

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "bgmi.json")

BGMI_NEWS_URL = "https://www.battlegroundsmobileindia.com/news"
BGMI_UPDATES_URL = "https://www.battlegroundsmobileindia.com/updates"
BGMI_ESPORTS_URL = "https://www.battlegroundsmobileindia.com/esports"

SEASON_RE = re.compile(r"[Ss]eason\s*(\d{1,2})")
VERSION_FULL_RE = re.compile(r"(?<!\d)(\d{1,2}\.\d{1,2}\.\d{1,3})(?![\d.])")
VERSION_KEYWORD_RE = re.compile(r"(?:version|update)\s*:?\s*(\d{1,2}(?:\.\d+){1,3})", re.I)

# Servers that can be probed over HTTP(S) from GitHub Actions.
SERVER_PROBES = {
    "login_server": "https://www.battlegroundsmobileindia.com/",
    "match_server": "https://www.battlegroundsmobileindia.com/news",
    "shop_server": "https://www.battlegroundsmobileindia.com/updates",
}


def check_server_status():
    """Probe BGMI endpoints; returns (status_dict, any_reachable)."""
    print("[INFO] Checking BGMI server status...")
    status = {name: "unknown" for name in SERVER_PROBES}
    reachable = False
    for name, url in SERVER_PROBES.items():
        data = fetch_url(url, timeout=15)
        if data is not None:
            status[name] = "reachable"
            reachable = True
            print(f"[INFO]   {name}: reachable ({len(data)} bytes)")
        else:
            status[name] = "unreachable"
    return status, reachable


def extract_season_and_version(text):
    """Best-effort extraction of season number and game version from page text."""
    season = None
    version = None
    for m in SEASON_RE.finditer(text):
        n = int(m.group(1))
        if 1 <= n <= 99:
            season = n
            break
    # Prefer a full dotted version (e.g. "3.6.0") anywhere on the page.
    for m in VERSION_FULL_RE.finditer(text):
        version = m.group(1)
        break
    if version is None:
        for m in VERSION_KEYWORD_RE.finditer(text):
            version = m.group(1)
            break
    return season, version


def scrape_official_site(existing):
    """
    Pull the latest news/updates pages and extract season + version signals.

    Returns (changes, season_number, version) where `changes` is a list of
    headline strings from the news feed, or (None, None, None) on total
    failure.
    """
    news = fetch_url(BGMI_NEWS_URL, timeout=20,
                     headers={"User-Agent": "Mozilla/5.0 (compatible; TRACKER-/1.0)"})
    updates = fetch_url(BGMI_UPDATES_URL, timeout=20,
                        headers={"User-Agent": "Mozilla/5.0 (compatible; TRACKER-/1.0)"})
    if news is None and updates is None:
        return None, None, None

    text = (news or "") + "\n" + (updates or "")
    season, version = extract_season_and_version(text)

    # Extract headline-ish entries from the news page HTML.
    changes = []
    if news:
        for m in re.finditer(r"<h[23][^>]*>(.*?)</h[23]>", news, flags=re.S | re.I):
            title = re.sub(r"<[^>]+>", "", m.group(1))
            title = title.strip()
            if 8 < len(title) < 140 and title not in changes:
                changes.append(title)
            if len(changes) >= 6:
                break
    return changes, season, version


def extract_event_dates(text):
    """Find ISO-ish date pairs on the page (for event start/end hints)."""
    pattern = r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})"
    dates = []
    for m in re.finditer(pattern, text):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        year = y if y >= 2000 else 2000 + y
        if 1 <= d <= 31 and 1 <= mo <= 12 and year <= 2030:
            dates.append(f"{year:04d}-{mo:02d}-{d:02d}")
    return dates


def update_tracker():
    """Main update function. Always writes output; never raises on network errors."""
    print("[INFO] Starting BGMI tracker update...")
    now = utcnow_iso()
    existing = read_json(OUTPUT_FILE) or {}
    data = dict(existing)
    data.setdefault("game", "BGMI (Battlegrounds Mobile India)")

    sources = dict(data.get("sources") or {})

    # 1. Official site (news/updates) ---------------------------------------
    changes, season, version = scrape_official_site(existing)
    if changes is not None:
        data["news_headlines"] = changes
        data["last_updated"] = now
        if season is not None:
            old_season = data.get("season") or {}
            data["season"] = {
                "number": season,
                "name": old_season.get("name") or f"Season {season}",
                "start_date": old_season.get("start_date") or None,
                "end_date": old_season.get("end_date") or None,
                "rank_reset_date": old_season.get("rank_reset_date") or None,
                "tier_rewards": old_season.get("tier_rewards") or [],
                "detected_at": now,
            }
            print(f"[INFO] Season detected: S{season}")
        if version is not None:
            data["current_version"] = version
            print(f"[INFO] Version detected: {version}")
        sources["official_site"] = {"ok": True, "checked_at": now, "error": None}
    else:
        sources["official_site"] = {"ok": False, "checked_at": now,
                                    "error": "official site unreachable"}
        print("[WARN] Official site unreachable — keeping existing data", file=sys.stderr)

    # 2. Server status -------------------------------------------------------
    server_status, reachable = check_server_status()
    data["server_status"] = server_status
    data["server_status"]["checked_at"] = now
    if reachable:
        sources["server_probes"] = {"ok": True, "checked_at": now, "error": None}
    else:
        sources["server_probes"] = {"ok": False, "checked_at": now,
                                    "error": "all probes failed"}

    # 3. Esports page (best-effort reachability + headline) ------------------
    esports_html = fetch_url(BGMI_ESPORTS_URL, timeout=20,
                             headers={"User-Agent": "Mozilla/5.0 (compatible; TRACKER-/1.0)"})
    if esports_html is not None:
        sources["esports"] = {"ok": True, "checked_at": now, "error": None}
        esports = dict(data.get("esports") or {})
        esports["last_checked"] = now
        for m in re.finditer(r"<h[23][^>]*>(.*?)</h[23]>", esports_html, flags=re.S | re.I):
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if 8 < len(title) < 140:
                esports["recent_headline"] = title
                break
        data["esports"] = esports
    else:
        sources["esports"] = {"ok": False, "checked_at": now,
                              "error": "esports page unreachable"}

    # 4. Freshness bookkeeping -----------------------------------------------
    data["last_attempt"] = now
    site_ok = sources["official_site"]["ok"]
    probes_ok = sources["server_probes"]["ok"]
    if site_ok:
        data["data_quality"] = "live"
    elif probes_ok:
        data["data_quality"] = "partial"
    else:
        data["data_quality"] = "stale"
    data["sources"] = sources

    write_json(OUTPUT_FILE, data)
    print(f"[INFO] BGMI data written ({data['data_quality']})")
    return data


if __name__ == "__main__":
    update_tracker()
