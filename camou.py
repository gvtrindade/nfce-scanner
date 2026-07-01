from camoufox import AsyncCamoufox
from camoufox.virtdisplay import VirtualDisplay
import logging
import os

logger = logging.getLogger(__name__)

# Patch Xvfb screen size: default 1x1x24 is a known bot detection signal
# Real screens are never 1x1 pixel; this causes Cloudflare Turnstile to fail
VirtualDisplay.xvfb_args = (
    "-screen", "0", "1920x1080x24",
    "-ac",
    "-nolisten", "tcp",
    "-extension", "RENDER",
    "+extension", "GLX",
    "-extension", "COMPOSITE",
    "-extension", "XVideo",
    "-extension", "XVideo-MotionCompensation",
    "-extension", "XINERAMA",
    "-shmem",
    "-fp", "built-ins",
    "-nocursor",
    "-br",
)

config = {
    'window.outerHeight': 1056,
    'window.outerWidth': 1920,
    'window.innerHeight': 1008,
    'window.innerWidth': 1920,
    'navigator.language': 'pt-BR',
    'navigator.languages': ['pt-BR', 'en-US'],
    'navigator.hardwareConcurrency': 12,
}

MIN_CONTENT_LENGTH = 6000


def _get_proxy():
    proxy_url = os.environ.get("PROXY_URL")
    if proxy_url:
        logger.info(f"Using proxy: {proxy_url}")
        return {"server": proxy_url}
    return None


async def _content_or_none(page, label=""):
    content = await page.content()
    logger.info(f"[{label}] Content length: {len(content)}, URL: {page.url}")
    if len(content) < MIN_CONTENT_LENGTH:
        text = await page.evaluate('document.body?.innerText') or 'N/A'
        logger.warning(f"[{label}] Content too small ({len(content)}), body text: {text[:500]}")
        return None
    return content


async def _try_captcha(page, url):
    logger.info(f"Captcha page, current URL: {page.url}")

    # Let the page fully settle
    try:
        await page.wait_for_load_state("networkidle", timeout=15 * 1000)
    except Exception:
        pass

    # Some SEFAZ Captcha pages require time-on-page before accepting submission
    await page.wait_for_timeout(10 * 1000)

    locator = page.locator("input[value='Continuar consulta de NFC-e']")
    try:
        await locator.wait_for(timeout=20 * 1000)
        logger.info("Found continue button, clicking...")

        # Use real Playwright click to trigger JS event handlers on the form
        async with page.expect_navigation(timeout=30 * 1000):
            await locator.click(force=True, timeout=10 * 1000)
        logger.info(f"Post-click URL: {page.url}")
        content = await _content_or_none(page, "captcha-click")
        if content:
            return content
        logger.info("Click succeeded but content too small")
    except Exception as e:
        logger.info(f"Click or navigation failed: {e}")
        logger.info(f"Post-attempt URL: {page.url}")

    logger.info("Trying to get any content from current page")
    raw = await _content_or_none(page, "captcha-fallback")
    if raw:
        text = await page.evaluate('document.body?.innerText') or ''
        if "Caso o erro persista" in text:
            logger.info("SEFAZ error page detected")
            return None
        return raw
    return None


async def _try_direct(page, url):
    logger.info(f"Direct NfceCompleta URL, current URL: {page.url}")
    return await _content_or_none(page, "direct")


async def scrape_content(key: str):
    url = f"https://ww1.receita.fazenda.df.gov.br/DecVisualizador/Nfce/Captcha?Chave={key}"

    proxy = _get_proxy()
    launch_kwargs = dict(
        config=config,
        os=["windows", "macos", "linux"],
        i_know_what_im_doing=True,
        headless="virtual",
        disable_coop=True,
    )
    if proxy:
        launch_kwargs["proxy"] = proxy
        launch_kwargs["geoip"] = True

    logger.info(f"Starting scrape for key {key}")
    try:
        async with AsyncCamoufox(**launch_kwargs) as browser:
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30 * 1000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=15 * 1000)
                except Exception:
                    pass
                result = await _try_captcha(page, url)

                if result:
                    logger.info("Got valid content")
                    return result
                logger.info("No valid content from this URL, trying next")
            except Exception as e:
                logger.warning(f"URL {url} failed: {e}")

            return await page.content()
    except Exception as e:
        logger.error(f"Error in scrape_content: {str(e)}", exc_info=True)
        raise
