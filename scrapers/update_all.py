#!/usr/bin/env python3
"""
Master update script — runs all scrapers and refreshes data files.
"""

import sys
import os

# Add scrapers directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from minecraft_scraper import update_tracker as update_minecraft
from bgmi_scraper import update_tracker as update_bgmi


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
