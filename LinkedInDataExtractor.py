import os
import asyncio
import random
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv

load_dotenv("creds.env")
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
             "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


async def linkedin_profile_scraper(username: str):
    user_data_dir = os.path.join(Path.home(), ".crawl4ai", "linkedin_session")
    browser_config = BrowserConfig(
        headless=False,
        user_data_dir=user_data_dir,
        use_persistent_context=True,
        user_agent=USER_AGENT
    )
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="networkidle",
        page_timeout=180000,
        session_id="linkedin_session"  # Important: Use the same session_id for all related requests
    )

    login_url = "https://www.linkedin.com/login"
    profile_url = f"https://www.linkedin.com/in/{username}/"

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Login step with session reuse
        async def login_action(page):
            await page.fill('input[name="session_key"]', LINKEDIN_EMAIL)
            await page.fill('input[name="session_password"]', LINKEDIN_PASSWORD)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle")
            await page.wait_for_selector('nav[aria-label="Primary"]', timeout=15000)

        print("Logging in to LinkedIn...")
        await asyncio.sleep(random.uniform(5, 10))
        await crawler.arun(login_url, config=run_config, page_action=login_action)
        print("Login successful. Navigating to profile...")

        await asyncio.sleep(random.uniform(6, 18))

        # Profile fetch within same session
        result = await crawler.arun(profile_url, config=run_config)

        content = result.markdown.lower()

        if "captcha" in content or "verify" in content or "join linkedin" in content:
            print("Captcha or login challenge detected! Automation may be blocked.")
        else:
            print("Profile data extracted:\n")
            print(result.markdown[:2000])  # Print first 2000 characters

        # When done, kill the session (optional to free memory)
        await crawler.crawler_strategy.kill_session("linkedin_session")


if __name__ == "__main__":
    username = "thilak-p-l-3050b1202"  # Pass LinkedIn username, not full profile URL
    asyncio.run(linkedin_profile_scraper(username))
