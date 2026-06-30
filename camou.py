from camoufox import AsyncCamoufox
import logging
import os

logger = logging.getLogger(__name__)

config = {
    'window.outerHeight': 1056,
    'window.outerWidth': 1920,
    'window.innerHeight': 1008,
    'window.innerWidth': 1920,
    'navigator.language': 'pt-BR',
    'navigator.languages': ['pt-BR', 'en-US'],
    'navigator.platform': 'Win32',
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
    await page.wait_for_timeout(5 * 1000)

    locator = page.locator("input[value='Continuar consulta de NFC-e']")
    try:
        await locator.wait_for(timeout=20 * 1000)
        logger.info("Found continue button, clicking...")
        await locator.click()
        await page.wait_for_load_state("networkidle", timeout=20 * 1000)
        await page.wait_for_timeout(3 * 1000)
        logger.info(f"Post-click URL: {page.url}")
        content = await _content_or_none(page, "captcha-click")
        if content:
            return content
        logger.info("Captcha click succeeded but content too small")
    except Exception as e:
        logger.info(f"Continue button not found or click failed: {e}")
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
        headless=True,
        disable_coop=True,
    )
    if proxy:
        launch_kwargs["proxy"] = proxy
        launch_kwargs["geoip"] = True

    logger.info(f"Starting scrape for key {key}")
    try:
        async with AsyncCamoufox(**launch_kwargs) as browser:
            page = await browser.new_page()

            logger.info(f"Trying URL: {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30 * 1000)
                await page.wait_for_timeout(5 * 1000)
                logger.info(f"Title: {await page.title()}, URL: {page.url}")

                if "Captcha" in page.url or "Captcha" in url:
                    result = await _try_captcha(page, url)
                else:
                    result = await _try_direct(page, url)

                if result:
                    logger.info("Got valid content")
                    return result
                logger.info("No valid content from this URL, trying next")
            except Exception as e:
                logger.warning(f"URL {url} failed: {e}")

            logger.warning("All URLs exhausted, returning last page content")
            return await page.content()
    except Exception as e:
        logger.error(f"Error in scrape_content: {str(e)}", exc_info=True)
        raise
