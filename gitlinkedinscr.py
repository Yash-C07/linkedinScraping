import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from parsel import Selector
import time

load_dotenv("creds.env")
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# Setup Chrome driver with automatic version management
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

def linkedin_login(email, password):
    driver.get('https://www.linkedin.com/uas/login')

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, 'username'))
    )
    driver.find_element(By.ID, 'username').send_keys(email)
    driver.find_element(By.ID, 'password').send_keys(password)
    driver.find_element(By.ID, 'password').submit()

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'nav[role="navigation"]'))
    )
    print("Logged in successfully.")

def expand_section(button_selector, timeout=5):
    try:
        btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(button_selector)
        )
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(2)
    except (TimeoutException, NoSuchElementException):
        pass
    except ElementClickInterceptedException:
        print("Could not click expand button.")

def scroll_page():
    scroll_pause_time = 1.0
    last_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(0, last_height, 250):
        driver.execute_script(f"window.scrollTo(0, {i});")
        time.sleep(scroll_pause_time)

def extract_profile_sections():
    sel = Selector(text=driver.page_source)

    about = sel.xpath('//section[contains(@class, "artdeco-card") and .//h2[contains(text(), "About")]]//span[contains(@class, "break-words")]/text()').get()
    about = about.strip() if about else None

    projects = []
    project_sections = sel.xpath('//section[contains(@class,"pv-profile-section") and .//h2[contains(text(),"Projects")]]//li')
    for proj in project_sections:
        title = proj.xpath('.//h3/text()').get()
        description = proj.xpath('.//p/text()').get()
        if title:
            projects.append({
                "title": title.strip(),
                "description": description.strip() if description else ""
            })

    licenses = []
    license_sections = sel.xpath('//section[contains(@class,"pv-profile-section") and .//h2[contains(text(),"Licenses")]]//li')
    for lic in license_sections:
        name = lic.xpath('.//h3/text()').get()
        issuer = lic.xpath('.//p[contains(@class,"issuer-name")]/text()').get()
        if name:
            licenses.append({
                "name": name.strip(),
                "issuer": issuer.strip() if issuer else ""
            })

    education = []
    education_sections = sel.xpath('//section[contains(@class,"education-section")]//li')
    for edu in education_sections:
        school = edu.xpath('.//h3/text()').get()
        degree = edu.xpath('.//p[contains(@class,"degree")]/text()').get()
        field_of_study = edu.xpath('.//p[contains(@class,"field-of-study")]/text()').get()
        dates = edu.xpath('.//p[contains(@class, "date-range")]/time/text()').getall()
        education.append({
            "school": school.strip() if school else "",
            "degree": degree.strip() if degree else "",
            "field_of_study": field_of_study.strip() if field_of_study else "",
            "dates": " - ".join(dates) if dates else ""
        })

    return {
        "about": about,
        "projects": projects,
        "licenses": licenses,
        "education": education
    }

def scrape_linkedin_profile(url):
    driver.get(url)
    time.sleep(5)
    scroll_page()
    expand_section((By.CSS_SELECTOR, 'button[aria-label*="Show more"]'))
    expand_section((By.CSS_SELECTOR, 'button[aria-label*="See more projects"]'))

    return extract_profile_sections()

if __name__ == "__main__":
    email = LINKEDIN_EMAIL
    password = LINKEDIN_PASSWORD
    linkedin_login(email, password)

    profile_url = "https://www.linkedin.com/in/thilak-p-l-3050b1202/"
    data = scrape_linkedin_profile(profile_url)

    driver.quit()

    print("Extracted Profile Data:")
    print(data)
