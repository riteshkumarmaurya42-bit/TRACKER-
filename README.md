# TRACKER- 🎮

**Minecraft Bedrock Edition + BGMI (Battlegrounds Mobile India) Tracker**

A live dashboard that tracks game versions, seasons, events, weapon meta, esports, and more — auto-updated via GitHub Actions every **6 hours**.

## 🚀 Live Dashboard

**[View Dashboard →](https://riteshkumarmaurya42-bit.github.io/TRACKER-/)**

The dashboard **auto-refreshes every 60 seconds**, so new data pushed by the GitHub Actions workflow appears without a manual page reload. A LIVE/PARTIAL/STALE indicator and per-section "updated X ago" timestamps show exactly how fresh the data is.

## 📂 Project Structure

```
TRACKER-/
├── index.html                    # Live dashboard (HTML/CSS/JS, auto-refresh)
├── data/
│   ├── minecraft_bedrock.json    # Minecraft Bedrock version & status data
│   └── bgmi.json                 # BGMI season, events, esports data
├── scrapers/
│   ├── common.py                 # Shared HTTP/JSON helpers (stdlib only)
│   ├── minecraft_scraper.py      # Minecraft Wiki API + Mojang status scraper
│   ├── bgmi_scraper.py           # BGMI official site scraper
│   └── update_all.py             # Master update script
├── .github/
│   └── workflows/
│       └── auto-update.yml       # Auto-update every 6 hours
└── README.md
```

## ⛏️ Minecraft Bedrock Tracking (live)

- Current & upcoming versions — parsed from the [Minecraft Wiki API](https://minecraft.wiki)
- Version history with release dates & changelogs
- [Mojang service status](https://status.mojang.com/check) (checked every run)
- Marketplace stats & platform availability (curated, timestamped)

## 🔫 BGMI Tracking (live)

- Current season & version — detected from the official site news/updates feed
- Latest official headlines
- Server reachability probes (login / match / shop / news)
- Events, map rotation, game modes, weapon meta, esports & tier rewards

## ⚙️ Auto-Update

The tracker runs automatically every **6 hours** via GitHub Actions (`.github/workflows/auto-update.yml`):

1. Scrapers fetch latest data from official sources
2. JSON data files are updated with fresh timestamps (`last_updated`, per-source `checked_at`, `data_quality`)
3. Changes are committed and pushed automatically

You can also trigger a manual update from the [Actions tab](https://github.com/riteshkumarmaurya42-bit/TRACKER-/actions) → *Auto-Update Tracker Data* → **Run workflow**.

> **Note:** the workflow writes to the `main` branch, which GitHub Pages then deploys automatically (Pages is configured as *Deploy from branch*).

## 🛠️ Local Development

```bash
# Run scrapers manually (no dependencies needed — Python 3 stdlib only)
python scrapers/update_all.py

# Open dashboard locally
python -m http.server 8000
# Then visit http://localhost:8000
```

If a live source is unreachable, the scrapers keep the previous data and mark
`data_quality: "partial"`/`"stale"` — the dashboard shows this instead of
failing silently.

## 📊 Data Sources

- [Minecraft Wiki API](https://minecraft.wiki)
- [Mojang Status](https://status.mojang.com)
- [BGMI Official](https://www.battlegroundsmobileindia.com)

---

*Auto-updated by GitHub Actions · Last build: see dashboard "Updated" indicator*
