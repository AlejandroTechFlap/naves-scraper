"""
Utilidades compartidas para navegación con zendriver.

Usadas por integrations/milanuncios.py (warmup) y save_session.py (login).
"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Timeout para el polling inicial de about:blank
_NAV_POLL_TIMEOUT = 10.0
_NAV_POLL_INTERVAL = 0.3
_NAV_MAX_RETRIES = 2


async def wait_for_navigation(
    page,
    url: str,
    browser=None,
    marker_prefix: str = "NAV",
    retries: int = _NAV_MAX_RETRIES,
    poll_timeout: float = _NAV_POLL_TIMEOUT,
) -> str:
    """
    Espera a que Chrome cargue una URL real (no about:blank).

    Hace bring_to_front + wait_for_ready_state, luego polling rápido cada 0.3s.
    Si sigue en about:blank tras `poll_timeout` segundos, reintenta hasta `retries` veces.

    Args:
        page: zendriver page object
        url: URL que se intentó cargar
        browser: zendriver browser (para inspeccionar tabs en logs)
        marker_prefix: prefijo para los marcadores stdout (e.g. "WARMUP", "SESSION_NAV")
        retries: intentos adicionales de navegación tras el primero
        poll_timeout: segundos de polling antes de reintentar

    Returns:
        La URL real cargada.

    Raises:
        NavigationError: si no se pudo cargar tras todos los reintentos.
    """
    try:
        await page.bring_to_front()
    except Exception:
        pass
    try:
        await page.wait_for_ready_state(until="complete")
    except Exception:
        await asyncio.sleep(5)

    await asyncio.sleep(2)

    # Polling rápido: verificar cada 0.3s hasta poll_timeout
    actual_url = await _poll_until_loaded(page, poll_timeout)
    if actual_url:
        print(f"[{marker_prefix}:nav_ok] URL cargada: {actual_url}", flush=True)
        return actual_url

    # Reintentar navegación
    for attempt in range(retries):
        tab_urls = _get_tab_urls(browser)
        logger.warning("[%s] about:blank tras %.0fs (intento %d/%d). Tabs: %s",
                       marker_prefix, poll_timeout, attempt + 1, retries + 1, tab_urls)
        print(f"[{marker_prefix}:blank attempt={attempt+1}/{retries+1}] about:blank — tabs: {tab_urls}", flush=True)

        await page.get(url)
        try:
            await page.bring_to_front()
        except Exception:
            pass
        try:
            await page.wait_for_ready_state(until="complete")
        except Exception:
            await asyncio.sleep(5)

        actual_url = await _poll_until_loaded(page, poll_timeout)
        if actual_url:
            print(f"[{marker_prefix}:nav_ok] URL cargada: {actual_url}", flush=True)
            return actual_url

    # Todos los reintentos fallaron
    tab_urls = _get_tab_urls(browser)
    print(f"[{marker_prefix}:nav_failed] about:blank tras {retries + 1} reintentos — tabs: {tab_urls}", flush=True)
    logger.error("[%s] Fallo: about:blank tras %d reintentos. Tabs: %s",
                 marker_prefix, retries + 1, tab_urls)
    raise NavigationError(
        f"about:blank tras {retries + 1} reintentos — Chrome no pudo cargar {url}"
    )


async def _poll_until_loaded(page, timeout: float) -> Optional[str]:
    """Polling de window.location.href hasta que no sea about:blank. Retorna URL o None."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        await asyncio.sleep(_NAV_POLL_INTERVAL)
        try:
            actual_url = await page.evaluate("window.location.href") or ""
        except Exception:
            actual_url = ""
        if actual_url and "about:blank" not in actual_url:
            return actual_url
    return None


def _get_tab_urls(browser) -> list[str]:
    """Extrae URLs de todas las pestañas abiertas (para diagnóstico)."""
    if browser is None:
        return ["?"]
    return [getattr(t, "url", "?") for t in browser.targets]


class NavigationError(Exception):
    """Chrome no pudo cargar la URL tras múltiples reintentos."""
