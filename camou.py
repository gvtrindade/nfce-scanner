from camoufox import Camoufox

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
    async with Camoufox(
        config=config,
        os=["windows", "macos", "linux"],
        i_know_what_im_doing=True,
        headless=True
    ) as browser:
        page = await browser.new_page()
        await page.goto(url)

        print("Page accessed, waiting to load")
        await page.wait_for_timeout(10 * 1000)
        locator = page.locator("input[value='Continuar consulta de NFC-e']")
        await locator.wait_for()
        await locator.click()

        print("Page accessed, returning content")
        await page.wait_for_timeout(5 * 1000)

        # with open("file.html", "w") as f:
        #     f.writelines(page.content())

        return await page.content()

        #in ubuntu server: install libasound2t64 and libgtk-3-0