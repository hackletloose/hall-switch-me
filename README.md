# Discord SWITCH ME Bot

A Discord bot that lets registered players switch to the opposite team on your Hell Let Loose servers via a simple command—no admin pinging required. Now supports **multiple CRCON instances** and automatically picks the correct server based on where the player is currently connected. This README replaces the earlier version of the file. 

---

## Features

* **`!switch` in one line:** Players trigger a team switch themselves.
* **One-time registration:** Link Discord ↔ Steam64 via `!reg <Steam64>`.
* **Multi-CRCON aware:** Provide multiple CRCON base URLs; the bot finds the right one dynamically.
* **Queue that follows the player:** When a team is full, the bot queues the request and re-detects the player’s current server before executing.
* **i18n messages:** Language set via `.env` (e.g., `LANGUAGE=de`).

---

## Requirements

* Python 3.10+
* A Discord bot token
* CRCON HTTP API(s) reachable from the bot
* Shared API token across CRCON instances (recommended)

---

## Quick start

```bash
git clone <your-repo>
cd <your-repo>
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
cp default.env .env   # if you have a template; otherwise create .env as below
python bot.py
```

---

## Configuration (.env)

### 🚨 Breaking change (v2+)

Use **`API_BASE_URLS`** (plural) instead of `API_BASE_URL`. This enables multiple CRCON instances.

**Minimal example:**

```env
# Discord
DISCORD_BOT_TOKEN=your-discord-bot-token
ALLOWED_CHANNEL_ID=123456789012345678

# Language / DB / Commands
LANGUAGE=de
DB_FILE=switch.db
COMMAND_SWITCH=switch
COMMAND_REG=reg

# CRCON auth (shared across instances)
API_TOKEN=your-shared-crcon-api-token

# Multiple CRCON endpoints (comma-separated OR JSON array; use one style)
API_BASE_URLS=https://rcon.example.com,https://rcon2.example.com
# API_BASE_URLS=["https://rcon.example.com","https://rcon2.example.com"]

# (Fallback for single endpoint—discouraged; will be removed in a future release)
# API_BASE_URL=https://rcon.example.com
```

**Notes**

* Do **not** include trailing slashes in base URLs.
* `USERNAME`/`PASSWORD` are not used; the bot authenticates with `API_TOKEN` (Bearer).
* Keep `.env` out of version control (`.gitignore`).

---

## Commands

* **Register:** `!reg <Steam64>`
  Links your Discord user to your Steam64 ID and stores the current in-game name.
* **Switch team:** `!switch`
  The bot finds the CRCON instance where you are currently playing, checks the opposite team’s capacity, and switches you if possible. If the team is full, you’re added to a queue.

> Command keywords are configurable via `.env` (`COMMAND_REG`, `COMMAND_SWITCH`).

---

## How it works

1. **Player lookup:** For each CRCON in `API_BASE_URLS`, the bot calls `GET /api/get_detailed_players` and searches by **player_id (Steam64)** with a safe fallback to the stored nickname.
2. **Server selection:** It picks the CRCON that actually contains the player.
3. **Capacity check:** It fetches `GET /api/get_gamestate` on that CRCON and checks the opposite team’s player count.
4. **Switch request:** It calls `POST /api/switch_player_now` with body `{ "player_id": "<Steam64>" }`.
5. **Queue behavior:** If full, the bot places a queue item (with `player_id`) and periodically re-checks across all CRCONs before executing.

---

## Upgrading from v1.x

* **`.env` rename:** `API_BASE_URL` → **`API_BASE_URLS`** (plural).
  Example:

  ```diff
  - API_BASE_URL=https://rcon.example.com
  + API_BASE_URLS=https://rcon.example.com,https://rcon2.example.com
  ```
* **Request body change:** `switch_player_now` now expects **`player_id`** instead of `player_name`. The included code already uses the ID.

No database migration is required. The existing table

```
users(discord_id TEXT PRIMARY KEY, steam_id TEXT, player_name TEXT)
```

continues to work; `steam_id` is used as `player_id`.

---

## File overview

* `bot.py` – Discord client, command handling, multi-CRCON selection, queue.
* `api_client.py` – HTTP client for CRCON (`get_detailed_players`, `get_gamestate`, `switch_player_now`, `get_player_profile`).
* `database.py` – SQLite storage for Discord↔Steam link.
* `utils.py` – Helpers (e.g., Steam64 validation).
* `translations.json` – Localized bot messages.

---

## Troubleshooting

* **“Player not in game”**
  Ensure the Steam64 is correct (`!reg <Steam64>`), and verify the player actually joined a server.
* **“Queue full”**
  Default queue size is limited (see `bot.py`). Reduce traffic or raise the limit if needed.
* **No CRCON found**
  Check `API_BASE_URLS` formatting (comma-separated or valid JSON array) and that all instances share a valid `API_TOKEN`.
* **403/401 errors**
  The CRCON permissions must allow `switch_player_now` for your token.

---

## Security

* **Do not** commit real tokens or `.env`.
* Rotate tokens if they were ever exposed.
* Restrict the bot to a dedicated Discord channel via `ALLOWED_CHANNEL_ID`.

---

## Acknowledgements

* CRCON community & maintainers.
* Original README content updated for v3 and multi-instance support. 

Happy switching! 🎮
