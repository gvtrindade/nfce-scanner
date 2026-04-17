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



def scrape_content(url):
    with Camoufox(
        config=config,
        os=["windows", "macos", "linux"],
        i_know_what_im_doing=True,
        headless=True
    ) as browser:
        page = browser.new_page()
        page.goto(url)

        print("Page accessed, waiting to load")
        page.wait_for_timeout(10 * 1000)
        locator = page.locator("input[value='Continuar consulta de NFC-e']")
        locator.wait_for()
        locator.click()

        print("Page accessed, returning content")
        page.wait_for_timeout(5 * 1000)

        # with open("file.html", "w") as f:
        #     f.writelines(page.content())

        return page.content()

        #in ubuntu server: install libasound2t64 and libgtk-3-0