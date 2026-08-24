# TRACKER- 🎮

**Minecraft Bedrock Edition + BGMI (Battlegrounds Mobile India) Tracker**

A live dashboard that tracks game versions, seasons, events, weapon meta, esports, and more — auto-updated via GitHub Actions.

## 🚀 Live Dashboard

**[View Dashboard →](https://riteshkumarmaurya42-bit.github.io/TRACKER-/)**

## 📂 Project Structure

```
TRACKER-/
├── index.html                    # Live dashboard (HTML/CSS/JS)
├── data/
│   ├── minecraft_bedrock.json    # Minecraft Bedrock version & marketplace data
│   └── bgmi.json                 # BGMI season, maps, weapons, esports data
├── scrapers/
│   ├── minecraft_scraper.py      # Minecraft data scraper
│   ├── bgmi_scraper.py           # BGMI data scraper
│   └── update_all.py             # Master update script
├── .github/
│   └── workflows/
│       └── auto-update.yml       # Auto-update every 6 hours
└── README.md
```

## ⛏️ Minecraft Bedrock Tracking

- Current & upcoming versions
- Version changelogs
- Mojang service status
- Marketplace stats (add-ons, skins, worlds)
- Platform availability

## 🔫 BGMI Tracking

- Current season info & tier rewards
- Active events & crate rotations
- Map rotation & game modes
- Weapon meta (tier rankings & pick rates)
- Esports tournaments & results
- Server status

## ⚙️ Auto-Update

The tracker runs automatically every **6 hours** via GitHub Actions:

1. Scrapers fetch latest data from official sources
2. JSON data files are updated
3. Changes are committed and pushed automatically

You can also trigger a manual update from the [Actions tab](https://github.com/riteshkumarmaurya42-bit/TRACKER-/actions).

## 🛠️ Local Development

```bash
# Run scrapers manually
python scrapers/update_all.py

# Open dashboard locally
# Just open index.html in a browser, or:
python -m http.server 8000
# Then visit http://localhost:8000
```

## 📊 Data Sources

- [Minecraft Wiki](https://minecraft.wiki)
- [Mojang Status](https://status.mojang.com)
- [BGMI Official](https://www.battlegroundsmobileindia.com)

---

*Auto-updated by GitHub Actions · Last build: 2026-08-24*
