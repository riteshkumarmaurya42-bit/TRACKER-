#!/usr/bin/env python3
"""
Minecraft Bedrock Edition Tracker Scraper
Fetches latest version info, changelogs, and marketplace data.
"""

import json
import os
import sys
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "minecraft_bedrock.json")

MINECRAFT_WIKI_API = "https://minecraft.wiki/w/Bedrock_Edition"
MOJANG_STATUS_URL = "https://status.mojang.com/check"


def fetch_url(url, timeout=15):
    """Fetch a URL and return the response text."""
    headers = {
        "User-Agent": "MinecraftTracker/1.0 (GitHub Actions; +https://github.com/riteshkumarmaurya42-bit/TRACKER-)"
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except URLError as e:
        print(f"[WARN] Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def check_mojang_services():
    """Check Mojang/Microsoft service statuses."""
    print("[INFO] Checking Mojang service statuses...")
    data = fetch_url(MOJANG_STATUS_URL)
    services = {}
    if data:
        try:
            statuses = json.loads(data)
            service_map = {
                "minecraft.net": "Minecraft.net",
                "session.minecraft.net": "Multiplayer Sessions",
                "account.mojang.com": "Mojang Accounts",
                "authserver.mojang.com": "Authentication",
                "api.mojang.com": "Mojang API",
                "textures.minecraft.net": "Textures/Skins",
                "mojang.com": "Mojang.com"
            }
            for entry in statuses:
                for key, status in entry.items():
                    name = service_map.get(key, key)
                    services[name] = "green" if status == "green" else ("yellow" if status == "yellow" else "red")
        except json.JSONDecodeError:
            print("[WARN] Could not parse Mojang status response", file=sys.stderr)
    return services


def load_existing_data():
    """Load existing tracker data if available."""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            return json.load(f)
    return {
        "game": "Minecraft Bedrock Edition",
        "last_updated": None,
        "current_version": "unknown",
        "versions": [],
        "upcoming": {},
        "platforms": [],
        "marketplace_stats": {}
    }


def update_tracker():
    """Main update function."""
    print("[INFO] Starting Minecraft Bedrock tracker update...")
    
    data = load_existing_data()
    
    # Check service statuses
    services = check_mojang_services()
    if services:
        data["service_status"] = services
    
    # Update timestamp
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    # Write updated data
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"[INFO] Minecraft Bedrock data updated at {data['last_updated']}")
    print(f"[INFO] Current version: {data.get('current_version', 'unknown')}")
    print(f"[INFO] Service statuses: {len(services)} checked")
    
    return data


if __name__ == "__main__":
    update_tracker()
