#!/usr/bin/env python3
"""
BGMI (Battlegrounds Mobile India) Tracker Scraper
Fetches latest season info, events, map rotations, and esports data.
"""

import json
import os
import sys
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "bgmi.json")

BGMI_NEWS_URL = "https://www.battlegroundsmobileindia.com/news"
BGMI_UPDATES_URL = "https://www.battlegroundsmobileindia.com/updates"


def fetch_url(url, timeout=15):
    """Fetch a URL and return the response text."""
    headers = {
        "User-Agent": "BGMITracker/1.0 (GitHub Actions; +https://github.com/riteshkumarmaurya42-bit/TRACKER-)"
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except URLError as e:
        print(f"[WARN] Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def load_existing_data():
    """Load existing tracker data if available."""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            return json.load(f)
    return {
        "game": "BGMI (Battlegrounds Mobile India)",
        "last_updated": None,
        "current_version": "unknown",
        "season": {},
        "current_crate_events": [],
        "maps": [],
        "modes": [],
        "weapon_meta": {},
        "esports": {}
    }


def check_server_status():
    """Check BGMI server status."""
    print("[INFO] Checking BGMI server status...")
    data = fetch_url(BGMI_NEWS_URL)
    status = {
        "login_server": "unknown",
        "match_server": "unknown",
        "shop_server": "unknown"
    }
    if data:
        status["news_page"] = "reachable"
    else:
        status["news_page"] = "unreachable"
    return status


def update_tracker():
    """Main update function."""
    print("[INFO] Starting BGMI tracker update...")
    
    data = load_existing_data()
    
    # Check server status
    server_status = check_server_status()
    data["server_status"] = server_status
    
    # Update timestamp
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    # Write updated data
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"[INFO] BGMI data updated at {data['last_updated']}")
    print(f"[INFO] Current season: S{data.get('season', {}).get('number', '?')}")
    print(f"[INFO] Current version: {data.get('current_version', 'unknown')}")
    print(f"[INFO] Active maps: {len([m for m in data.get('maps', []) if m.get('status') == 'active'])}")
    print(f"[INFO] Active modes: {len([m for m in data.get('modes', []) if m.get('status') == 'active'])}")
    
    return data


if __name__ == "__main__":
    update_tracker()
