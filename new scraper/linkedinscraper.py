import os
import asyncio
import re
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.browser_profiler import BrowserProfiler
from crawl4ai.async_logger import AsyncLogger
from colorama import Fore, Style, init

def extract_linkedin_profile_fields(markdown: str) -> dict:
    profile_data = {}

    # Extract Name - Usually appears at the top in markdown as a big heading
    name_match = re.search(r"^#\s*(.+)$", markdown, re.MULTILINE)
    profile_data['name'] = name_match.group(1).strip() if name_match else None

    # Extract About section
    about_match = re.search(r"(?i)^##\s*About\s*\n(.*?)(\n##|\Z)", markdown, re.DOTALL | re.MULTILINE)
    if about_match:
        about_text = about_match.group(1).strip()
        profile_data['about'] = ' '.join(about_text.splitlines())
    else:
        profile_data['about'] = None

    # Extract Education
    edu_match = re.search(r"(?i)^##\s*Education\s*\n(.*?)(\n##|\Z)", markdown, re.DOTALL | re.MULTILINE)
    if edu_match:
        edu_block = edu_match.group(1).strip()
        educations = re.findall(r"^- (.+)$", edu_block, re.MULTILINE)
        profile_data['education'] = educations
    else:
        profile_data['education'] = []

    # Extract Work Experience
    work_match = re.search(r"(?i)^##\s*Experience\s*\n(.*?)(\n##|\Z)", markdown, re.DOTALL | re.MULTILINE)
    if work_match:
        work_block = work_match.group(1).strip()
        experiences = [line.strip() for line in work_block.splitlines() if line.strip()]
        profile_data['experience'] = experiences
    else:
        profile_data['experience'] = []

    # Extract Projects
    proj_match = re.search(r"(?i)^##\s*Projects\s*\n(.*?)(\n##|\Z)", markdown, re.DOTALL | re.MULTILINE)
    if proj_match:
        proj_block = proj_match.group(1).strip()
        projects = re.findall(r"^- (.+)$", proj_block, re.MULTILINE)
        profile_data['projects'] = projects
    else:
        profile_data['projects'] = []

    return profile_data

# Initialize colorama
init()

logger = AsyncLogger(verbose=True)
profiler = BrowserProfiler(logger=logger)

user_data_dir = os.path.abspath("./crawl4ai_profiles")
os.makedirs(user_data_dir, exist_ok=True)

SESSION_ID = "linkedin_session"

async def crawl_with_profile(profile_path, url):
    logger.info(f"\nCrawling {Fore.CYAN}{url}{Style.RESET_ALL} using profile at {Fore.YELLOW}{profile_path}{Style.RESET_ALL}", tag="CRAWL")

    browser_config = BrowserConfig(
        headless=False,
        use_managed_browser=True,
        user_data_dir=profile_path,
    )

    # More precise CSS selector targeting actual profile section for better extraction
    css_selector = "section.pv-profile-section"  # Adjust if needed by inspecting LinkedIn DOM

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Add extra sleep before scraping profile to let JS finish loading
        await asyncio.sleep(5)

        result = await crawler.arun(
            url=url,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                wait_until="networkidle",
                page_timeout=180000,
                css_selector=css_selector,
                session_id=SESSION_ID,
            )
        )

        print("Page title:", result.metadata.get("title"))
        print("Page URL:", result.url)

        # Check for authwall/login page fallback
        if "/authwall" in result.url or "sign in" in result.markdown.lower() or "join linkedin" in result.markdown.lower():
            print("[!] Detected authwall or login page instead of profile. Please login first or check session.")
            return

        # Print markdown preview
        print("Markdown preview:\n", result.markdown[:2000])

        # Extract structured profile data
        profile_fields = extract_linkedin_profile_fields(result.markdown)
        print("\nExtracted Profile Data:")
        for key, value in profile_fields.items():
            print(f"{key.capitalize()}: {value}")

async def main():
    mode = input("Run in [i]nteractive or [a]utomatic mode? (i/a): ").lower()

    if mode == 'i':
        await profiler.interactive_manager(crawl_callback=crawl_with_profile)
    else:
        profiles = profiler.list_profiles()
        if not profiles:
            logger.info("No profiles found. Creating a new one...", tag="DEMO")
            profile_path = await profiler.create_profile()
            if not profile_path:
                logger.error("Cannot proceed without a valid profile", tag="DEMO")
                return
        else:
            profile_path = profiles[0]["path"]
            logger.info(f"Using existing profile at path: {Fore.CYAN}{profile_path}{Style.RESET_ALL}", tag="DEMO")

        linkedin_url = "https://www.linkedin.com/in/thilak-p-l-3050b1202/"
        await crawl_with_profile(profile_path, linkedin_url)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Interrupted by user", tag="DEMO")
