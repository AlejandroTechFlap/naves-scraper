"""
Ciclo de vida del browser de scraping: warmup y espera de captchas.

Extraído de integrations/milanuncios.py para mantener cada archivo < 300 líneas.
"""
import asyncio
import logging
import random

import zendriver as uc

from utils.browser import NavigationError, wait_for_navigation

logger = logging.getLogger(__name__)

BASE_URL = "https://www.milanuncios.com"
CATEGORY_URL = "https://www.milanuncios.com/naves-industriales/"

_WARMUP_CAPTCHA_TIMEOUT = 45  # segundos de espera automática para F5 proof-of-work
_CAPTCHA_SOLVE_TIMEOUT = 600  # 10 min para resolución manual del usuario
_CAPTCHA_MARKERS = ("geetest", "pardon our interruption", "just a moment", "checking your browser")


# ---------------------------------------------------------------------------
# Warmup
# ---------------------------------------------------------------------------

async def warmup(browser: uc.Browser) -> None:
    """
    Secuencia de warm-up en 3 pasos para que p.js/reese84 genere el token
    de confianza antes de navegar a la URL de búsqueda real.
    Sin este warm-up, el challenge se activa en la primera petición.
    """
    from integrations.milanuncios import ScrapeBanException

    # Paso 1: homepage — deja que los scripts anti-bot corran
    print("[WARMUP:step1] Cargando homepage...", flush=True)
    logger.info("Warm-up paso 1/3: homepage...")
    page = await browser.get(BASE_URL)

    try:
        await wait_for_navigation(page, BASE_URL, browser=browser, marker_prefix="WARMUP")
    except NavigationError:
        raise ScrapeBanException("about:blank tras 3 reintentos — Chrome no pudo cargar la URL. Reiniciando browser.")

    await asyncio.sleep(random.uniform(2.0, 4.0))
    title = await page.evaluate("document.title") or ""

    if "pardon" in title.lower():
        logger.warning("[WARMUP] Captcha en homepage — esperando resolución automática (%ds)...", _WARMUP_CAPTCHA_TIMEOUT)
        print("[WARMUP:captcha] F5/Incapsula en homepage — esperando resolución automática...", flush=True)
        if not await _wait_for_warmup_captcha(page, BASE_URL):
            print("[WARMUP:captcha_skip] Sin resolver — saltando paso 1.", flush=True)
            logger.warning("[WARMUP] Captcha en homepage no resuelto — continuando igualmente")
        return

    logger.info(f"Warm-up paso 1 OK: {title}")

    # Paso 2: scroll suave para simular lectura humana
    try:
        await page.scroll_down(random.randint(200, 500))
    except Exception:
        pass
    await asyncio.sleep(random.uniform(1.5, 3.0))

    # Paso 3: navegar a la categoría objetivo para activar el token de esa sección
    print("[WARMUP:step2] Cargando categoria naves-industriales...", flush=True)
    logger.info("Warm-up paso 2/3: categoría naves-industriales...")
    await page.get(CATEGORY_URL)
    await asyncio.sleep(random.uniform(3.0, 5.0))
    html = await page.get_content()

    if "pardon" in html.lower() or "geetest" in html.lower():
        logger.warning("[WARMUP] Captcha en categoría — esperando resolución automática (%ds)...", _WARMUP_CAPTCHA_TIMEOUT)
        print("[WARMUP:captcha] F5/Incapsula en naves-industriales — esperando resolución automática...", flush=True)
        if not await _wait_for_warmup_captcha(page, CATEGORY_URL):
            print("[WARMUP:captcha_skip] Sin resolver — saltando paso 2.", flush=True)
            logger.warning("[WARMUP] Captcha en categoría no resuelto — continuando igualmente")
    else:
        logger.info("Warm-up paso 2/3 OK.")

    try:
        await page.scroll_down(random.randint(100, 300))
    except Exception:
        pass
    await asyncio.sleep(random.uniform(1.0, 2.0))
    print("[WARMUP:complete] Warm-up completado.", flush=True)
    logger.info("Warm-up completo.")


# ---------------------------------------------------------------------------
# Espera de captcha durante warmup (automática, F5 proof-of-work)
# ---------------------------------------------------------------------------

async def _wait_for_warmup_captcha(page, url: str, timeout: int = _WARMUP_CAPTCHA_TIMEOUT) -> bool:
    """
    Espera resolución automática del captcha F5/Incapsula durante el warmup.
    F5 proof-of-work se resuelve solo en <30s — no requiere interacción del usuario.
    Si no resuelve en `timeout` segundos, hace un reload y espera 10s más.
    Retorna True si se resolvió, False si hay que saltarse el paso.
    """
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        await asyncio.sleep(2)
        try:
            html = await page.get_content()
            if not any(kw in html.lower() for kw in ("pardon", "geetest")):
                elapsed = timeout - int(deadline - loop.time())
                print(f"[WARMUP:captcha_ok] Captcha resuelto automáticamente ({elapsed}s).", flush=True)
                logger.info("[WARMUP] Captcha resuelto automáticamente en ~%ds", elapsed)
                return True
        except Exception:
            pass

    # Reload: un refresh puede completar el challenge JS pendiente
    print("[WARMUP:captcha_reload] Recargando para completar challenge...", flush=True)
    logger.info("[WARMUP] Recargando %s tras captcha no resuelto en %ds", url, timeout)
    try:
        await page.get(url)
        await asyncio.sleep(10)
        html = await page.get_content()
        if not any(kw in html.lower() for kw in ("pardon", "geetest")):
            print("[WARMUP:captcha_ok] Captcha resuelto tras reload.", flush=True)
            logger.info("[WARMUP] Captcha resuelto tras reload")
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Espera interactiva de captcha (usuario resuelve manualmente)
# ---------------------------------------------------------------------------

async def wait_for_captcha_solve(page, url: str, timeout: int = _CAPTCHA_SOLVE_TIMEOUT) -> None:
    """Mantiene Chrome abierto y espera hasta que el usuario resuelva el captcha.

    Imprime marcadores que `scraper_job.py` detecta para actualizar el dashboard.
    Timeout: 10 minutos → raise ScrapeBanException.
    """
    from integrations.milanuncios import ScrapeBanException

    # Si Chrome está en about:blank, navegar de vuelta a la URL del captcha
    try:
        current_url = await page.evaluate("window.location.href") or ""
        if "about:blank" in current_url or not current_url:
            logger.info("[CAPTCHA] Pestaña en about:blank — navegando de vuelta a %s", url)
            await page.get(url)
            await asyncio.sleep(2)
    except Exception:
        pass
    # Traer la pestaña al frente para que el usuario vea el captcha
    try:
        await page.bring_to_front()
    except Exception:
        pass

    print("[CAPTCHA_REQUIRED] Captcha detectado — resuelve el captcha en la ventana de Chrome para continuar", flush=True)
    logger.warning(f"[CAPTCHA] Captcha interactivo en {url} — esperando resolución manual (max {timeout}s)")

    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    consecutive_errors = 0

    while loop.time() < deadline:
        await asyncio.sleep(5)
        remaining = int(deadline - loop.time())
        try:
            title = await page.evaluate("document.title") or ""
            html = await page.get_content()
            consecutive_errors = 0  # Chrome sigue vivo
            if not any(kw in html.lower() for kw in _CAPTCHA_MARKERS):
                print("[CAPTCHA_SOLVED] Captcha resuelto — continuando scraping", flush=True)
                logger.info("[CAPTCHA] Captcha resuelto por el usuario — continuando.")
                return
        except Exception:
            consecutive_errors += 1
            if consecutive_errors >= 3:
                print("[CAPTCHA_TIMEOUT] Chrome cerrado — se requiere renovar sesión", flush=True)
                logger.error("[CAPTCHA] Chrome cerrado (%d errores consecutivos) en %s", consecutive_errors, url)
                raise ScrapeBanException(f"Chrome cerrado durante espera de captcha — re-ejecuta save_session.py")
        print(f"[CAPTCHA_WAITING] Esperando resolución del captcha ({remaining}s restantes)...", flush=True)

    print("[CAPTCHA_TIMEOUT] Tiempo agotado esperando el captcha — se requiere renovar sesión", flush=True)
    logger.error("[CAPTCHA] Tiempo agotado (%ds) sin resolver captcha en %s", timeout, url)
    raise ScrapeBanException(f"Captcha no resuelto en {timeout}s en {url} — re-ejecuta save_session.py")
