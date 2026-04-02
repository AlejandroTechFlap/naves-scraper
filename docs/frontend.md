# Frontend — Next.js Dashboard

**Stack:** Next.js 15 (App Router) · React 19 · TypeScript · Tailwind CSS · shadcn/ui · SWR
**Port:** 3000
**Auth:** Password login → API key stored in `localStorage`

---

## Quick Start

```bash
# From project root
bash run_frontend.sh

# Or manually
cd frontend
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL if API not on :8000
npm install
npm run dev     # dev server on :3000
npm run build   # production build
npm start       # serve production build
```

The frontend proxies all `/api/*` requests to FastAPI (configured in `next.config.ts`) so no CORS issues in dev.

---

## Directory Structure

```
frontend/src/
  app/
    layout.tsx                  # Root layout (Toaster)
    login/page.tsx              # Login page
    (app)/                      # Authenticated route group
      layout.tsx                # Sidebar + AlertBanner + AuthGuard + CaptchaModal
      page.tsx                  # Redirect → /control
      resumen/page.tsx          # Redirect → /control (legacy bookmarks)
      control/page.tsx          # Unified panel (scraper, session, cron, logs)
      anuncios/page.tsx         # Listings browser with filters
  components/
    layout/
      sidebar.tsx               # Fixed left nav — 2 links: Panel, Anuncios
      alert-banner.tsx          # Sticky top status banner
    panel/
      stats-row.tsx             # 4 metric cards (total, webflow synced/pending/total)
      cron-card.tsx             # Cron scheduling form (presets + custom)
      logs-panel.tsx            # Log viewer with limit + auto-refresh controls
    scraper/
      run-form.tsx              # Start/stop/configure scraper
      status-badge.tsx          # Colored badge for scraper state
    captcha/
      captcha-modal.tsx         # Captcha alert modal with CTA buttons
    chrome/
      chrome-popup.tsx          # Fullscreen noVNC viewer dialog
    listings/
      listings-table.tsx        # Paginated listings table
      listings-filters.tsx      # Province/surface/price filter controls
    logs/
      log-viewer.tsx            # Scrollable log output
    ui/                         # shadcn/ui primitives (Button, Card, Badge, etc.)
  hooks/
    use-scraper-status.ts       # SWR hook for /api/scraper/status
    use-session-status.ts       # SWR hook for /api/session/status
    use-webflow-status.ts       # SWR hook for /api/webflow/status
    use-captcha-alert.ts        # Captcha transition detection + browser notifications
    use-vnc-status.ts           # SWR hook for /api/vnc/status
  lib/
    api.ts                      # All API calls (fetcher, runScraper, etc.)
    auth.ts                     # localStorage API key helpers
    auth-context.tsx            # (unused, auth is guard-based)
    auth-guard.tsx              # Redirects to /login if no API key
    notification-sound.ts       # Web Audio chime utility
    send-notification.ts        # Browser Notification + sound dispatch
    types.ts                    # TypeScript interfaces mirroring API shapes
    utils.ts                    # formatDate, formatNumber, cn()
```

---

## Authentication Flow

1. User visits any route → `AuthGuard` checks `localStorage` for `naves_api_key`
2. If absent → redirect to `/login`
3. Login page: user enters `DASHBOARD_PASSWORD` → `POST /api/auth/login` → API returns `api_key`
4. Key saved via `saveApiKey()` → `localStorage.setItem("naves_api_key", key)`
5. All subsequent requests include `x-api-key: <key>` header
6. On 401/403 response → `removeApiKey()` + redirect to `/login`

---

## API Client (`lib/api.ts`)

```ts
fetcher(url)          // SWR fetcher — GET with auth headers, handles 401
runScraper(body)      // POST /api/scraper/run
stopScraper()         // POST /api/scraper/stop
renewSession()        // POST /api/session/renew
cancelSession()       // POST /api/session/stop
updateCron(body)      // PUT /api/cron
syncWebflow()         // POST /api/webflow/sync
```

All `post/put` helpers throw `Error` with `detail` from API response body on non-2xx.

---

## SWR Hooks

### `useScraperStatus()`
Polls `/api/scraper/status` every 3s when active:
```ts
refreshInterval: (data) => {
  if (data?.state === "running" || data?.challenge_waiting || data?.needs_session_renewal)
    return 3000;
  return 0;  // stop polling when idle
}
```
Returns: `{ status, isRunning, hasCaptcha, needsRenewal, mutate }`

### `useSessionStatus()`
Polls `/api/session/status` every 3s when `state=running`, stops otherwise.
Returns: `{ session, isRenewing, mutate }`

### `useWebflowStatus()`
Single fetch (no auto-poll).
Returns: `{ webflow, isLoading, mutate }`

---

## Alert Banner (`components/layout/alert-banner.tsx`)

Sticky banner rendered above all page content. Shows the highest-priority active alert:

| Priority | Condition | Color | Action buttons |
|----------|-----------|-------|----------------|
| 1 | `challenge_waiting = true` | Amber | "Parar y renovar sesion" |
| 2 | `needs_session_renewal = true` AND `isRenewing = true` | Blue | "Cancelar" (calls `POST /api/session/stop`) |
| 3 | `needs_session_renewal = true` | Red | "Abrir Chrome" (calls `POST /api/session/renew`) |
| — | None of the above | Hidden | — |

When in blue (renewing) state, shows step-by-step instructions if `waiting_for_login=true`:
1. Solve captcha if Chrome shows one
2. Log in to your Milanuncios account
3. Navigate to "Mis Anuncios" — the script detects it automatically

---

## Captcha Notification System

When a captcha is detected (`challenge_waiting=true`), the dashboard fires a 3-layer alert:

1. **Browser push notification** — `Notification` API with `tag: "captcha-alert"` (deduplicates). Works even when the tab is in the background. Permission requested once on first authenticated page load.
2. **Sound chime** — Web Audio API plays a 3-tone ascending major chord (C5-E5-G5). No external audio files needed.
3. **Modal overlay** — `CaptchaModal` component (Dialog, z-50) appears centered with amber styling, pulsing alert icon, and CTA buttons: "Ver Chrome" (opens VNC viewer) and "Parar y renovar sesion".

**Transition detection:** `useCaptchaAlert` hook uses `useRef` to track `hasCaptcha` previous value. Notifications only fire on false-to-true edge, not on every 3s SWR poll.

**Auto-close:** Modal closes automatically when `hasCaptcha` returns to false (captcha resolved).

**Files:**
- `lib/notification-sound.ts` — Web Audio chime utility
- `lib/send-notification.ts` — Notification + sound dispatch
- `hooks/use-captcha-alert.ts` — Transition detection + permission request
- `components/captcha/captcha-modal.tsx` — Modal overlay component

---

## Pages

### `/control` (Panel de Control) — Unified dashboard
All scraper management in a single page:
1. **Stats row** — 4 metric cards: total listings, Webflow synced, pending sync, Webflow total
2. **Scraper control + Cron scheduling** — side by side in 2-col grid. RunForm (max_pages, dry_run, reset, start/stop) + CronCard (preset dropdown, custom cron expression, max pages, next run)
3. **Live logs** — full-width LogViewer with fixed height (400px), internal scroll, line limit (50-1000), and auto-refresh toggle

Session renewal is handled entirely by `AlertBanner` in the app layout (red/blue banners + ChromePopup). No session card on this page.

### `/anuncios`
- `ListingsFilters` — province select, min surface, max price
- `ListingsTable` — paginated (50/page), sortable; columns: title, price, surface, province, location, scraped date, Webflow status

### Auto Webflow Sync
Webflow sync triggers automatically server-side in `api/scraper_job.py` after every successful scrape (`rc == 0`). No manual sync button needed. The WebflowCard on the dashboard shows read-only status that updates via SWR.

---

## Key Components

### `RunForm`
- Inputs: max pages (0=unlimited), dry run toggle, reset checkpoint toggle
- "Iniciar" button → `POST /api/scraper/run`
- "Detener" button (when running) → `POST /api/scraper/stop`
- Disabled when scraper is running or session renewal in progress

### `StatusBadge`
Color-coded badge:
- `idle` → gray
- `running` → blue (pulsing dot)
- `error` → red
- `stopped` → yellow

---

## Types (`lib/types.ts`)

```ts
ScraperStatus     // mirrors scraper_status.json
SessionStatus     // mirrors session_status.json (+ waiting_for_login, login_detected, navigating)
WebflowStatus     // { total, synced, pending, last_sync_at }
CronConfig        // { cron_expr, max_pages, next_run }
Listing           // flat listing row from /api/listings
ListingsResponse  // { items, total, page, page_size, pages }
ScrapeRunRequest  // { max_pages, dry_run, reset }
CronConfigRequest // { cron_expr, max_pages }
```

---

## Chrome Remote Viewer (VNC)

The `ChromePopup` component (`components/chrome/chrome-popup.tsx`) renders a fullscreen noVNC viewer inside a Dialog overlay. Uses `react-vnc` (dynamically imported, SSR disabled) connecting via WebSocket to `websockify :6080 → x11vnc :5900 → Xvfb :99`.

**Auto-open/close behavior:**
- Opens automatically when session renewal is triggered (`handleRenew` / `handleStopAndRenew`)
- Closes automatically via `useEffect` when `isRenewing` transitions to `false` (session saved or cancelled)
- "Ver Chrome" button only visible while `isRenewing = true`

**twMerge class conflict pattern:** The shadcn `DialogContent` wrapper merges default classes with custom overrides via `cn()` (twMerge). Two default classes survive unless explicitly overridden:
- `sm:max-w-sm` — must add `sm:max-w-none` (responsive variants need matching prefix)
- `-translate-x-1/2 -translate-y-1/2` — must add `translate-x-0 translate-y-0` (different CSS property group)

---

## Environment

`frontend/.env.local` (optional — only needed if API is not on localhost:8000):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

API proxying is handled in `next.config.ts` via `rewrites()` so the browser never needs a direct API URL in production when served from the same host.
