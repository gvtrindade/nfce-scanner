from camoufox import AsyncCamoufox
import logging

logger = logging.getLogger(__name__)

config = {
    'window.outerHeight': 1056,
    'window.outerWidth': 1920,
    'window.innerHeight': 1008,
    'window.innerWidth': 1920,
    'navigator.language': 'en-US',
    'navigator.languages': ['en-US'],
    'navigator.platform': 'Win32',
    'navigator.hardwareConcurrency': 12,
}


async def scrape_content(url):
    logger.info(f"Starting to scrape content from {url}")
    try:
        async with AsyncCamoufox(
            config=config,
            os=["windows", "macos", "linux"],
            i_know_what_im_doing=True,
            headless=True
        ) as browser:
            page = await browser.new_page()
            logger.info(f"Going to URL: {url}")
            await page.goto(url)

            logger.info("Page accessed, waiting to load")
            await page.wait_for_timeout(10 * 1000)

            logger.info(f"Current page title: {await page.title()}")
            logger.info(f"Current page URL: {page.url}")

            locator = page.locator("input[value='Continuar consulta de NFC-e']")
            try:
                await locator.wait_for(timeout=10 * 1000)
                await locator.click()
                logger.info("Clicked continue button, waiting for content")
                await page.wait_for_timeout(5 * 1000)
            except Exception:
                logger.info("Continue button not found, trying to get content directly")

            logger.info("Getting page content")
            content = await page.content()
            logger.info(f"Content length: {len(content)}")
            if len(content) < 2000:
                logger.warning(f"Content too small, body text: {await page.evaluate('document.body?.innerText') or 'N/A'}")

            return content
    except Exception as e:
        logger.error(f"Error in scrape_content: {str(e)}", exc_info=True)
        raise
