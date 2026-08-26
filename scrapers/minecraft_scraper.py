#!/usr/bin/env python3
"""
Minecraft Bedrock Edition Tracker Scraper

Fetches live data from:
  - Minecraft Wiki MediaWiki API (latest versions, release dates, changelogs)
  - Mojang status API (service statuses)

Every section records when it was last successfully checked so the dashboard
can show real freshness. If a live source is unavailable the previous values
are kept (graceful degradation) — nothing is ever hardcoded as fresh.
"""

import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import fetch_json, fetch_url, read_json, utcnow_iso, write_json

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "minecraft_bedrock.json")

WIKI_API = "https://minecraft.wiki/api.php"
MOJANG_STATUS_URL = "https://status.mojang.com/check"
MARKETPLACE_URL = "https://www.minecraft.net/en-us/marketplace"

VERSION_RE = re.compile(r"(?<!\d)(1\.\d{1,2}\.\d{1,3})(?![\d.])")
DATE_ISO_RE = re.compile(r"(20\d{2})-(\d{1,2})-(\d{1,2})")
DATE_TEMPLATE_RE = re.compile(r"\{\{\s*[Dd]ate\s*\|\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})\s*\}\}")
MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}
MONTH_NAME_RE = re.compile(
    r"(" + "|".join(MONTHS) + r")\s+(\d{1,2}),?\s+(\d{4})", re.I
)

# Curated values that don't change often and cannot be reliably scraped.
CURATED_PLATFORMS = ["Windows 10/11", "Xbox", "PlayStation", "Nintendo Switch", "iOS", "Android", "Chromebook"]


def version_key(v):
    """Sort key for version strings like '1.21.80'."""
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0, 0, 0)


def wiki_wikitext(page):
    """Return the raw wikitext of a Minecraft Wiki page (or None)."""
    url = WIKI_API + "?" + urlencode({
        "action": "parse",
        "page": page,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
    })
    data = fetch_json(url, timeout=30)
    try:
        return data["parse"]["wikitext"]
    except (KeyError, TypeError):
        return None


def strip_wikitext(text):
    """Best-effort removal of wiki markup from a text fragment."""
    # Nested templates: strip iteratively until nothing changes.
    for _ in range(6):
        new = re.sub(r"\{\{[^{}]*\}\}", "", text)
        if new == text:
            break
        text = new
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)  # links -> label
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)    # refs
    text = re.sub(r"<[^>]+>", "", text)                            # other tags
    text = re.sub(r"''+'?", "", text)                              # italics/bold
    return text.strip()


def normalize_date(text):
    """Normalize a date found in wikitext to YYYY-MM-DD (or None)."""
    m = DATE_TEMPLATE_RE.search(text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = DATE_ISO_RE.search(text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = MONTH_NAME_RE.search(text)
    if m:
        return f"{int(m.group(3)):04d}-{MONTHS[m.group(1).capitalize()]:02d}-{int(m.group(2)):02d}"
    return None


def extract_changes(wikitext, limit=6):
    """Extract bullet-point changelog entries from a version page."""
    out = []
    headings = re.finditer(
        r"\n==+\s*(?:Additions|Changes|Fixes|Additions and changes|General)\s*==+",
        wikitext,
    )
    for m in headings:
        body = wikitext[m.end():]
        nxt = re.search(r"\n==+[^=]", body)
        if nxt:
            body = body[:nxt.start()]
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("*"):
                clean = strip_wikitext(line[1:].strip())
                if len(clean) > 3 and clean not in out:
                    out.append(clean)
                if len(out) >= limit:
                    break
        if len(out) >= limit:
            break
    return out


def parse_wiki_versions():
    """
    Pull the latest Bedrock releases from the Minecraft Wiki.

    Returns (versions, upcoming, latest_version) where each version dict has
    version/release_date/status/changes, or (None, None, None) on failure.
    """
    print("[INFO] Fetching Minecraft Wiki: Bedrock Edition...")
    main_text = wiki_wikitext("Bedrock_Edition")
    if main_text is None:
        print("[WARN] Could not fetch Bedrock_Edition page", file=sys.stderr)
        return None, None, None

    # Highest 3-part version mentioned on the main page = latest release line.
    candidates = sorted({m.group(1) for m in VERSION_RE.finditer(main_text)}, key=version_key)
    if not candidates:
        print("[WARN] No version numbers found on Bedrock_Edition page", file=sys.stderr)
        return None, None, None
    latest = candidates[-1]

    print(f"[INFO] Fetching Minecraft Wiki: version history (latest: {latest})...")
    hist_text = wiki_wikitext("Bedrock_Edition_version_history")
    if hist_text is None:
        print("[WARN] Could not fetch version history page", file=sys.stderr)
        return [], {"version": latest, "expected_date": None, "features_preview": []}, latest

    today = datetime.now(timezone.utc).date().isoformat()
    version_dates = {}

    # Preferred: map each "=== 1.21.80 ===" section heading to the date inside
    # its body. This ignores version numbers that only appear inside templates
    # like {{Version nav|...}}.
    parts = re.split(r"\n(={2,6})\s*([^=\n]+?)\s*\1\s*\n", hist_text)
    for i in range(1, len(parts), 3):
        heading = parts[i + 1] if i + 1 < len(parts) else ""
        body = parts[i + 2] if i + 2 < len(parts) else ""
        m = VERSION_RE.search(heading)
        if not m:
            continue
        date = normalize_date(body) or normalize_date(heading)
        if date:
            version_dates[m.group(1)] = date

    # Fallback: any version mention followed shortly by a date.
    if not version_dates:
        for m in VERSION_RE.finditer(hist_text):
            window = hist_text[m.end():m.end() + 300]
            date = normalize_date(window)
            if date:
                version_dates.setdefault(m.group(1), date)

    # Always include the main-page latest even if the history page lacks it.
    version_dates.setdefault(latest, None)

    # Build the version list (released only; upcoming goes in `upcoming`).
    versions = []
    for v in sorted(version_dates, key=version_key, reverse=True)[:8]:
        date = version_dates[v]
        if date and date > today:
            continue  # not released yet -> handled as "upcoming"
        versions.append({
            "version": v,
            "release_date": date or "recently",
            "type": "release",
            "status": "stable",
            "changes": [],  # filled in below, best-effort
            "source": "wiki",
        })

    # Best-effort changelogs for the newest few versions.
    for entry in versions[:4]:
        page = f"Bedrock_Edition_{entry['version']}"
        wt = wiki_wikitext(page)
        if wt:
            entry["changes"] = extract_changes(wt)
        print(f"[INFO]   v{entry['version']}: {len(entry['changes'])} change(s) parsed")

    latest_stable = versions[0]["version"] if versions else latest

    # Upcoming: a future-dated version from the history page, else a hint
    # pointing at the newest known line with no released date.
    upcoming = None
    future = []
    for v in sorted(version_dates, key=version_key, reverse=True)[:8]:
        date = version_dates[v]
        if date and date > today:
            future.append((v, date))
    if future:
        v, date = future[0]
        upcoming = {"version": v, "expected_date": date, "features_preview": []}
    else:
        upcoming = {"version": latest, "expected_date": None, "features_preview": []}

    return versions, upcoming, latest_stable


def check_mojang_services():
    """Check Mojang/Microsoft service statuses (dict of name -> status)."""
    print("[INFO] Checking Mojang service statuses...")
    data = fetch_json(MOJANG_STATUS_URL, timeout=15)
    if data is None:
        return None
    service_map = {
        "minecraft.net": "Minecraft.net",
        "session.minecraft.net": "Multiplayer Sessions",
        "account.mojang.com": "Mojang Accounts",
        "authserver.mojang.com": "Authentication",
        "api.mojang.com": "Mojang API",
        "textures.minecraft.net": "Textures/Skins",
        "mojang.com": "Mojang.com",
    }
    services = {}
    for entry in data:
        for key, status in entry.items():
            name = service_map.get(key, key)
            services[name] = status if status in ("green", "yellow", "red") else "yellow"
    return services


def check_marketplace():
    """
    Best-effort marketplace probe. Returns (stats, ok). The marketplace is a
    JS-heavy page, so this usually only records reachability — curated counts
    are preserved either way.
    """
    html = fetch_url(MARKETPLACE_URL, timeout=20,
                     headers={"User-Agent": "Mozilla/5.0 (compatible; TRACKER-/1.0)"})
    if html is None:
        return None, False
    print("[INFO] Marketplace page reachable")
    return {}, True


def merge_curated(existing, versions, upcoming, latest):
    """
    Keep previously curated changelogs / upcoming features for versions that
    already existed, and preserve curated marketplace/platform data.
    """
    old_versions = {v.get("version"): v for v in (existing or {}).get("versions", [])}
    for entry in versions:
        old = old_versions.get(entry["version"])
        if old and not entry["changes"]:
            entry["changes"] = old.get("changes", [])
            entry["type"] = old.get("type", entry["type"])
            entry["status"] = old.get("status", entry["status"])
        entry["checked_at"] = utcnow_iso()

    old_upcoming = (existing or {}).get("upcoming") or {}
    if upcoming is None:
        upcoming = old_upcoming
    else:
        if not upcoming.get("features_preview"):
            upcoming["features_preview"] = old_upcoming.get("features_preview", [])
        if not upcoming.get("expected_date"):
            upcoming["expected_date"] = old_upcoming.get("expected_date")

    return versions, upcoming, latest


def update_tracker():
    """Main update function. Always writes output; never raises on network errors."""
    print("[INFO] Starting Minecraft Bedrock tracker update...")
    now = utcnow_iso()
    existing = read_json(OUTPUT_FILE) or {}
    data = dict(existing)
    data.setdefault("game", "Minecraft Bedrock Edition")

    sources = dict(data.get("sources") or {})

    # 1. Minecraft Wiki versions --------------------------------------------
    versions, upcoming, latest = parse_wiki_versions()
    if versions is not None:
        versions, upcoming, latest = merge_curated(existing, versions, upcoming, latest)
        data["versions"] = versions
        if latest:
            data["current_version"] = latest
        if upcoming:
            data["upcoming"] = upcoming
        data["last_updated"] = now
        sources["minecraft_wiki"] = {"ok": True, "checked_at": now, "error": None}
        print(f"[INFO] Latest Bedrock version: {latest}")
    else:
        sources["minecraft_wiki"] = {"ok": False, "checked_at": now,
                                     "error": "could not parse wiki pages"}
        print("[WARN] Wiki unavailable — keeping existing version data", file=sys.stderr)

    # 2. Mojang service status ---------------------------------------------
    services = check_mojang_services()
    if services is not None:
        data["service_status"] = services
        data["service_status"]["checked_at"] = now
        sources["mojang_status"] = {"ok": True, "checked_at": now, "error": None}
    else:
        sources["mojang_status"] = {"ok": False, "checked_at": now,
                                    "error": "status.mojang.com unreachable"}
        print("[WARN] Mojang status unreachable — keeping previous statuses", file=sys.stderr)

    # 3. Marketplace (best-effort reachability probe) ----------------------
    stats, ok = check_marketplace()
    if ok:
        old_stats = dict(existing.get("marketplace_stats") or {})
        old_stats["last_checked"] = now
        data["marketplace_stats"] = old_stats
        sources["marketplace"] = {"ok": True, "checked_at": now, "error": None}
    else:
        sources["marketplace"] = {"ok": False, "checked_at": now,
                                  "error": "marketplace page unreachable"}
        print("[WARN] Marketplace unreachable — keeping curated counts", file=sys.stderr)

    # 4. Platforms (curated, timestamped) ----------------------------------
    old_platforms = existing.get("platforms") or CURATED_PLATFORMS
    if old_platforms:
        data["platforms"] = old_platforms
    data["platforms_checked_at"] = now

    # 5. Freshness bookkeeping ----------------------------------------------
    data["last_attempt"] = now
    wiki_ok = sources["minecraft_wiki"]["ok"]
    status_ok = sources["mojang_status"]["ok"]
    if wiki_ok:
        data["data_quality"] = "live"
    elif status_ok:
        data["data_quality"] = "partial"
    else:
        data["data_quality"] = "stale"
    data["sources"] = sources

    write_json(OUTPUT_FILE, data)
    print(f"[INFO] Minecraft Bedrock data written ({data['data_quality']})")
    return data


if __name__ == "__main__":
    update_tracker()
