import os
import asyncio
import random
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv

# Load credentials from creds.env
load_dotenv("creds.env")
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
             "(KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"

SESSION_ID = "linkedin_session"

def build_browser_config(headless=True) -> BrowserConfig:
    return BrowserConfig(
        headless=headless,
        user_data_dir=os.path.join(Path.home(), ".crawl4ai", SESSION_ID),
        use_persistent_context=True,
        user_agent=USER_AGENT,
    )

BASE_RUN_CONFIG = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    wait_until="networkidle",
    page_timeout=180000,
    session_id=SESSION_ID,
)

RUN_CONFIG_WITH_SELECTOR = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    wait_until="networkidle",
    page_timeout=180000,
    css_selector="main",
    session_id=SESSION_ID,
)

async def linkedin_login(page):
    await page.wait_for_load_state("load")

    # Handle Welcome Back screen by clicking your account name
    if await page.is_visible('text="Welcome Back"'):
        print("Handling Welcome Back screen by clicking account...")
        # Change the selector text to your actual account label if needed
        await page.click('text="Alexander Heymn"')
        await asyncio.sleep(1)

    # Fill email if needed
    if await page.is_visible('input[name="session_key"]'):
        await page.fill('input[name="session_key"]', LINKEDIN_EMAIL)

    # Fill password and submit
    if await page.is_visible('input[name="session_password"]'):
        await page.fill('input[name="session_password"]', LINKEDIN_PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

    try:
        await page.wait_for_selector('nav[aria-label="Primary"]', timeout=15000)
        print("Login confirmed successful.")
    except Exception as e:
        print(f"Warning: Login confirmation failed: {e}")

async def scrape_linkedin_profile(profile_url: str, headless: bool = True):
    browser_config = build_browser_config(headless=headless)

    async with AsyncWebCrawler(config=browser_config) as crawler:

        # Step 1: Login page with action
        print("[*] Logging in LinkedIn...")
        await crawler.arun(
            url="https://www.linkedin.com/login",
            config=BASE_RUN_CONFIG,
            page_action=linkedin_login
        )

        await asyncio.sleep(random.uniform(3, 7))  # Human-like delay after login

        # Step 2: Fetch profile page in same session
        print(f"[*] Fetching LinkedIn profile: {profile_url}")
        result = await crawler.arun(
            url=profile_url,
            config=RUN_CONFIG_WITH_SELECTOR
        )

        markdown_lower = result.markdown.lower()

        # Step 3: Detect if redirected to authwall or login
        if "/authwall" in result.url or "sign in" in markdown_lower:
            print("[!] Authwall or login issue detected, retrying login and scrape...")

            # Retry login once more
            await crawler.arun(
                url="https://www.linkedin.com/login",
                config=BASE_RUN_CONFIG,
                page_action=linkedin_login
            )
            await asyncio.sleep(random.uniform(3, 7))

            # Retry profile scrape
            result = await crawler.arun(
                url=profile_url,
                config=RUN_CONFIG_WITH_SELECTOR
            )
            markdown_lower = result.markdown.lower()
            if "/authwall" in result.url or "sign in" in markdown_lower:
                print("[!!!] Still blocked by authwall after retry. You may need proxy or manual intervention.")
                return

        print("[+] Profile scraped successfully. Preview:")
        print(result.markdown[:2000])

        # Optional: clean up session
        await crawler.crawler_strategy.kill_session(SESSION_ID)

if __name__ == "__main__":
    PROFILE_URL = "https://www.linkedin.com/in/thilak-p-l-3050b1202/"
    asyncio.run(scrape_linkedin_profile(PROFILE_URL, headless=False))
