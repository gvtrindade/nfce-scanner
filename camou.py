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
            locator = page.locator("input[value='Continuar consulta de NFC-e']")
            await locator.wait_for()
            await locator.click()

            logger.info("Clicked, waiting for content")
            await page.wait_for_timeout(5 * 1000)

            logger.info("Getting page content")
            content = await page.content()
            logger.info(f"Content length: {len(content)}")

            return content
    except Exception as e:
        logger.error(f"Error in scrape_content: {str(e)}", exc_info=True)
        raise
