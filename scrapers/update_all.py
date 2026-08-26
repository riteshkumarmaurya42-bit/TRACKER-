#!/usr/bin/env python3
"""
Master update script — runs all scrapers and refreshes data files.
"""

import json
import os
import sys

# Add scrapers directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from minecraft_scraper import update_tracker as update_minecraft
from bgmi_scraper import update_tracker as update_bgmi

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def freshness_summary(path):
    """Return a short human-readable freshness line for a data file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return f"  ⚠️  {os.path.basename(path)}: unreadable ({e})"
    updated = data.get("last_updated") or data.get("last_attempt") or "never"
    quality = data.get("data_quality", "unknown")
    return f"  📦 {os.path.basename(path)} — {quality} · last update {updated}"


def main():
    print("=" * 60)
    print("  TRACKER- Auto Update")
    print("  Minecraft Bedrock + BGMI")
    print("=" * 60)
    print()

    errors = []

    # Update Minecraft Bedrock
    try:
        print("[1/2] Updating Minecraft Bedrock Edition data...")
        update_minecraft()
        print("[1/2] ✅ Minecraft Bedrock update complete\n")
    except Exception as e:
        print(f"[1/2] ❌ Minecraft Bedrock update failed: {e}\n")
        errors.append(("Minecraft Bedrock", str(e)))

    # Update BGMI
    try:
        print("[2/2] Updating BGMI data...")
        update_bgmi()
        print("[2/2] ✅ BGMI update complete\n")
    except Exception as e:
        print(f"[2/2] ❌ BGMI update failed: {e}\n")
        errors.append(("BGMI", str(e)))

    # Freshness summary
    print("-" * 60)
    print("Freshness:")
    for name in ("minecraft_bedrock.json", "bgmi.json"):
        print(freshness_summary(os.path.join(DATA_DIR, name)))
    print("-" * 60)

    # Summary
    print("=" * 60)
    if errors:
        print(f"  Completed with {len(errors)} error(s):")
        for name, err in errors:
            print(f"    - {name}: {err}")
        sys.exit(1)
    else:
        print("  ✅ All updates completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
