# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated scraper for industrial warehouse listings (naves industriales) from MilAnuncios.com. Microservices architecture: CLI scraper + FastAPI REST API + Streamlit dashboard + APScheduler cron, with Webflow CMS integration.

**Target site:** milanuncios.com — protected by Kasada (hard bot block) and F5/Incapsula reese84 (interactive captcha). The anti-bot strategy is the core engineering challenge.

---

## Quick Start (Development)

```bash
source venv/bin/activate
pip install -r requirements.txt

# First time only: create session (opens Chrome, login manually)
python save_session.py

# Run scraper directly
python scraper_engine.py --pages 2 --dry-run

# Start services
bash run_api.sh        # FastAPI on :8000
bash run_dashboard.sh  # Streamlit on :8501
```

**Access the dashboard:** http://localhost:8501 (password from `.env → DASHBOARD_PASSWORD`)

---

## Architecture

### Data Flow
```
save_session.py → session.json
        ↓
scraper_engine.py
        ↓
integrations/milanuncios.py  ←→  zendriver headful Chrome
        ↓
integrations/parser.py  (window.__INITIAL_PROPS__ JSON)
        ↓
db.py  (SQLite WAL, INSERT OR IGNORE)
        ↓
integrations/webflow_sync.py → Webflow CMS API
```

The API (`api/main.py`) wraps the scraper as a subprocess via `api/scraper_job.py`, enabling the dashboard and external cron triggers to control scraping without sharing the asyncio loop.

### Service Communication

```
dashboard/app.py (Streamlit :8501)
        ↓  HTTP + x-api-key
api/main.py (FastAPI :8000)
        ↓  subprocess stdout + scraper_status.json
scraper_engine.py (Python process)
        ↓  async
integrations/milanuncios.py → Chrome (headful)
```

---

## Key Components

### `integrations/milanuncios.py` — Core scraping engine

- Uses **zendriver** (not playwright/selenium) — required to bypass Kasada (avoids `Runtime.enable()` CDP call that Kasada detects)
- Must run **headful** (`headless=False`) — Kasada and F5 detect `--headless=new`
- Persistent Chrome profile in `chrome_profile/` — accumulates fingerprint trust; **never delete this folder**
- **Warm-up sequence** on each browser start: homepage → scroll → category page (lets reese84 anti-bot scripts generate a trust token before any search request)
- **Browser rotation:** closes and reopens Chrome every 10 listing requests (`_BROWSER_REFRESH_EVERY = 10`)
- **Keep-alive task:** disabled — the scraper's continuous navigation renews the reese84 token automatically

**Custom exceptions** (all in `integrations/milanuncios.py`):

| Exception | When raised | Recovery |
|-----------|-------------|----------|
| `ScrapeBanException` | Hard ban: Cloudflare "Just a Moment", Kasada header | Exponential backoff + browser reopen |
| `SessionExpiredException` | Redirected to `/login` or `/acceder` | Exit immediately, user must run `save_session.py` |
| `ListingNotFoundException` | 404 or "página no encontrada" in title | Skip listing, continue |
| `CaptchaRequiredException` | Interactive captcha: F5/Incapsula "Pardon Our Interruption", GeeTest | Pause and wait up to 10 min for user to solve in open Chrome window |

**Ban detection (`_check_for_ban`):**
- Cloudflare → `ScrapeBanException`
- F5/Incapsula reese84 ("pardon our interruption") → `CaptchaRequiredException`
- Kasada (`kasada` in HTML, `x-kpsdk` header) → `ScrapeBanException`
- GeeTest (`geetest` + `captcha` in HTML) → `CaptchaRequiredException`
- `/login` redirect → `SessionExpiredException`

**Captcha pause-and-wait (`_wait_for_captcha_solve`):**
When `CaptchaRequiredException` is raised during scraping, instead of crashing, the scraper:
1. Keeps Chrome open on screen
2. Prints `[CAPTCHA_REQUIRED]` marker → dashboard shows orange alert
3. Polls page every 5 sec for up to 10 min
4. When captcha markers disappear → prints `[CAPTCHA_SOLVED]` → resumes scraping
5. If timeout → prints `[CAPTCHA_TIMEOUT]` → raises `ScrapeBanException`

**Print marker protocol** (stdout → `api/scraper_job.py` parses these):
- `[CAPTCHA_REQUIRED]` — captcha detected, waiting
- `[CAPTCHA_WAITING]` — still waiting (printed every 5 sec)
- `[CAPTCHA_SOLVED]` — captcha resolved, resuming
- `[CAPTCHA_TIMEOUT]` — 10 min expired without resolution
- `[LOGIN_WAITING]` (in `save_session.py`) — waiting for manual login

### `api/scraper_job.py` — Subprocess management

- Launches `scraper_engine.py` as a subprocess (separate asyncio loop, headful Chrome)
- Monitors stdout line-by-line → parses progress markers → writes `scraper_status.json`
- Detects captcha markers and sets `challenge_waiting: true` in status
- **`scraper_status.json` fields:**
  - `state`: `"idle"` | `"running"` | `"error"` | `"stopped"`
  - `pid`: process ID
  - `current_page`, `total_new`, `total_skipped`: live progress
  - `challenge_waiting: bool` — true while interactive captcha is pending
  - `needs_session_renewal: bool` — true after hard ban or captcha timeout
  - `last_error`, `started_at`, `finished_at`
- Also manages `save_session.py` subprocess for session renewal
- Recovers zombie state on API startup (process died without cleanup)

### `api/main.py` — FastAPI microservice

Key endpoints (all require `x-api-key` header):

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/scraper/run` | Launch scraper (`max_pages`, `dry_run`, `reset`) |
| GET | `/api/scraper/status` | Read `scraper_status.json` |
| POST | `/api/scraper/stop` | Send SIGTERM |
| GET | `/api/listings` | Paginated listings with filters |
| GET | `/api/logs` | Last N lines of scraper log |
| GET/PUT | `/api/cron` | Read/update cron schedule |
| POST | `/api/session/renew` | Launch `save_session.py` |
| GET | `/api/session/status` | Session renewal progress |
| POST | `/api/webflow/sync` | Trigger Webflow sync |
| GET | `/api/webflow/status` | Sync statistics |

### `dashboard/app.py` — Streamlit dashboard

6 pages (sidebar navigation):
1. **Resumen** — metrics overview, scraper state, Webflow sync status
2. **Control del scraper** — start/stop, configure options, session renewal
3. **Programacion** — cron schedule presets + custom expression
4. **Registros** — real-time log viewer
5. **Anuncios** — paginated listing table with province/surface/price filters
6. **Webflow** — sync status and trigger

Key UX behaviors:
- Password protected (from `DASHBOARD_PASSWORD` env var)
- `mostrar_alerta_sesion()` shown on every page — displays captcha or session alerts
- Auto-refreshes every 5 sec when `state == "running"` or `challenge_waiting == True`
- Session renewal toast notification on state transitions

### `save_session.py` — Manual login

Opens headful Chrome → user logs in manually → detects navigation to `mis-anuncios/` → extracts all cookies via CDP (including http-only) → saves to `session.json`. Prints `[LOGIN_WAITING]` every 30 sec during wait.

### `scraper_engine.py` — Orchestration

- Reads `checkpoint.json` to resume from last position
- Paginates search results, deduplicates per listing
- Stops on 10 consecutive duplicates (reverse-chronological sort → incremental update)
- Ban recovery: exponential backoff 10→20→40→60 min, max 6 retries
- Downloads images if `DOWNLOAD_IMAGES=true`
- Writes per-run CSV log to `logs/`

### `integrations/parser.py` — Data extraction

- Primary: `window.__INITIAL_PROPS__` JSON embedded in HTML (30+ fields)
- Fallback: CSS selectors + regex
- Extracts: title, price, surface, location, seller, phone, photos, dates

### `db.py` — SQLite layer

- 30+ columns with `INSERT OR IGNORE` on `listing_id` (UNIQUE)
- WAL mode for concurrent reads
- `init_db()` auto-migrates — adds missing columns from `_NEW_COLUMNS` list
- Indices on: `listing_id`, `scraped_at`, `surface_m2`, `province`, `price_numeric`, `webflow_item_id`

### `scheduler.py` — APScheduler

- SQLAlchemy job store → `scheduler.db` (persists across restarts)
- Default cron: `0 6 * * *` (6am Europe/Madrid)
- Hot reload via `PUT /api/cron`

---

## Anti-Detection Strategy

1. **zendriver** — does NOT call `Runtime.enable()` (Kasada's main detection vector)
2. **Persistent `chrome_profile/`** — fingerprint continuity; Kasada trusts returning browsers
3. **Headful mode** — Kasada and F5 detect `--headless=new`
4. **Session cookies** — reese84 trusts authenticated sessions
5. **Warm-up sequence** — lets anti-bot scripts initialize trust token before searching
6. **Browser rotation** — reopen Chrome every 10 requests to refresh state
7. **Jitter** (`utils/jitter.py`) — 3–12 sec delays between requests, 5–8 sec between pages
8. **Viewport randomization** — cycles through 4 common resolutions

---

## Ban / Captcha Recovery

| Situation | Behavior | User action |
|-----------|----------|-------------|
| Cloudflare challenge | `ScrapeBanException` → exponential backoff, browser reopen | Wait for auto-retry |
| F5/Incapsula captcha | `CaptchaRequiredException` → Chrome stays open, dashboard shows orange alert | Solve captcha in Chrome window |
| GeeTest captcha | Same as F5 | Same |
| Kasada detection | `ScrapeBanException` → backoff | Likely need new session |
| Session expired | `SessionExpiredException` → scraper exits | Run `save_session.py` or click "Renovar sesión" in dashboard |
| Captcha timeout (10 min) | `ScrapeBanException` → `needs_session_renewal = true` | Dashboard prompts session renewal |

---

## Environment Variables (`.env`)

```
DB_PATH=naves.db
MAX_PAGES=0               # 0 = unlimited
MIN_SURFACE_M2=1000
DOWNLOAD_IMAGES=true
IMAGES_DIR=images
WEBFLOW_TOKEN=...
WEBFLOW_COLLECTION_ID=...
API_SECRET_KEY=...         # auto-generated by install.sh
DASHBOARD_PASSWORD=...
API_BASE_URL=http://localhost:8000
```

---

## Runtime Files

| File | Purpose |
|------|---------|
| `session.json` | Login cookies — regenerate with `save_session.py` when expired |
| `checkpoint.json` | Last scraped page + listing ID for resume |
| `scraper_status.json` | Live scraper state (state, progress, challenge_waiting, etc.) |
| `session_status.json` | Session renewal subprocess state |
| `naves.db` | Main SQLite database (30+ column listings table) |
| `scheduler.db` | APScheduler persistent job store |
| `chrome_profile/` | **Do not delete** — persistent Chrome fingerprint trust |
| `logs/scraper.log` | Rotating scraper log (10 MB × 5 files) |
| `logs/*.csv` | Per-run listing results |

---

## Scraper CLI Reference

```bash
python scraper_engine.py                   # Incremental, resume from checkpoint
python scraper_engine.py --pages 5         # Limit to 5 pages
python scraper_engine.py --batch 50        # Stop after 50 new listings
python scraper_engine.py --pages 1 --dry-run   # No DB writes (test mode)
python scraper_engine.py --reset           # Ignore checkpoint, start from page 1
```

---

## Common Tasks for Claude

**Adding a new parsed field:**
1. Extract it in `integrations/parser.py` (add to the return dict)
2. Add column in `db.py → SCHEMA` and `_NEW_COLUMNS` list (for auto-migration)
3. Optionally expose it in `api/main.py → get_listings` response
4. Add to `dashboard/app.py → page_anuncios` display columns

**Adding a new API endpoint:**
1. Add Pydantic model in `api/main.py` if needed
2. Add route with `dependencies=[Depends(verify_api_key)]`
3. If it modifies scraper state, update `ScraperStatus` TypedDict in `api/scraper_job.py`

**Changing ban detection logic:**
- Edit `_check_for_ban()` in `integrations/milanuncios.py`
- Hard bans → raise `ScrapeBanException`
- Interactive captchas → raise `CaptchaRequiredException` (scraper will wait for user)

**Debugging a scrape run:**
```bash
tail -f logs/scraper.log       # live log
cat scraper_status.json        # current state
cat session_status.json        # session renewal state
```

---

## Important Notes

- **Never delete `chrome_profile/`** — accumulated anti-bot trust, hard to rebuild
- **`DISPLAY` env var** must be set on Linux for headful Chrome (handled by `run_api.sh`)
- **Workers must be 1** — `uvicorn ... --workers 1` (multiple workers = multiple browser instances, breaks singleton pattern)
- **No emojis in UI** — use SVG icons or plain text (project convention)
- Incremental mode stops on first duplicate (assumes reverse-chronological sort)
- `docs/init_milanuncios.md` — detailed setup notes and lessons from previous projects
