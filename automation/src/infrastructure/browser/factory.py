from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from automation.src.config import settings


def create_browser(headless: bool | None = None, slow_mo: int | None = None) -> Browser:
    if headless is None:
        headless = settings.HEADLESS
    if slow_mo is None:
        slow_mo = settings.SLOW_MO

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=headless,
        slow_mo=slow_mo,
        args=[
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
        ],
    )
    return browser


def create_context(browser: Browser) -> BrowserContext:
    context = browser.new_context(
        viewport={"width": settings.VIEWPORT_WIDTH, "height": settings.VIEWPORT_HEIGHT},
        ignore_https_errors=True,
        user_agent=settings.USER_AGENT,
        locale=settings.BROWSER_LOCALE,
    )

    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return context


def create_page(browser: Browser | None = None) -> Page:
    if browser is None:
        browser = create_browser()
    context = create_context(browser)
    return context.new_page()
