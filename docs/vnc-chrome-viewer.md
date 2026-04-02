# VNC Chrome Viewer — Panel embebido en dashboard [IMPLEMENTED]

## Proposito

Permite interactuar con Chrome (resolver captchas, renovar sesion) desde el dashboard Next.js sin acceso fisico al VPS.

## Arquitectura

```
Xvfb :99  →  x11vnc :5900 (localhost)  →  websockify :6080  →  react-vnc (dashboard)
```

- **Xvfb :99** — display virtual donde corre Chrome (ya existente en `run_api.sh`)
- **x11vnc** — expone el display como VNC en puerto 5900, solo localhost
- **websockify** — traduce VNC a WebSocket en puerto 6080
- **react-vnc** — componente React (`VncScreen`) embebido en el dashboard

## Comportamiento

- El popup se abre automaticamente cuando hay captcha activo o sesion renovandose
- Se cierra automaticamente cuando el captcha se resuelve y la sesion no esta renovandose
- Si VNC no esta disponible (Mac, o sin x11vnc instalado), el popup no se muestra
- En Mac, Chrome ya es visible en pantalla — no necesita VNC
- Solo existe una conexion VNC activa (instancia unica via ChromePopupProvider)

## Endpoint API

```
GET /api/vnc/status → { available: bool, ws_port: number | null }
```

El hook `useVncStatus` consulta este endpoint con polling cada 30 segundos.

## Componentes frontend

### Provider (instancia unica)
- `providers/chrome-popup-provider.tsx` — React Context que gestiona el estado global del popup. Renderiza la unica instancia de `ChromePopup`. Auto-abre/cierra segun estado del scraper y session.
- `hooks/use-chrome-popup.ts` — hook para abrir/cerrar el popup desde cualquier componente

### Popup VNC
- `components/chrome/chrome-popup.tsx` — Dialog full-screen con `VncScreen`. Usa inline styles para posicionamiento (evita conflictos con tailwind-merge). Maneja conexion/desconexion/errores.

### Integracion
- `components/layout/alert-banner.tsx` — Boton "Ver Chrome" en banners de captcha/sesion. Usa `useChromePopup()` para abrir el popup global.
- `app/(app)/layout.tsx` — Wrappea la app con `ChromePopupProvider`

## Seguridad

- x11vnc escucha solo en localhost (`-localhost`)
- websockify en `0.0.0.0:6080` — asegurado por firewall del VPS (solo exponer 3000/8000)
- Autenticacion via DASHBOARD_PASSWORD existente (API key en headers)

## Dependencias

- Sistema: `x11vnc`, `novnc`, `websockify` (solo Linux, opcional)
- NPM: `react-vnc` (wrapper React de noVNC)
