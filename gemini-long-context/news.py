import json
import os
from time import sleep

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    return driver


def extract_article_content(driver, url):
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 10)

        # Find the date using the more stable part of the class name
        date_container = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[class^='styled__NewsInfoSlyled']")
            )
        )
        # Get the second paragraph which contains the date
        date_element = date_container.find_elements(By.TAG_NAME, "p")[1]
        date = date_element.text.split(" ")[1]  # Remove day name

        # Find the content container using the stable part of the class name
        content_container = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[class^='styled__TextRichContainer']")
            )
        )
        paragraphs = content_container.find_elements(By.TAG_NAME, "p")

        # Combine all paragraphs into one text, removing empty ones
        content = " ".join(p.text.strip() for p in paragraphs if p.text.strip())

        return {"date": date, "content": content}

    except Exception as e:
        print(f"Error extracting content from {url}: {e}")
        return None


def save_article(article_data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(article_data, f, ensure_ascii=False, indent=2)


def main():
    # Create directory for news if it doesn't exist
    os.makedirs("data/news", exist_ok=True)

    driver = setup_driver()

    try:
        # Example URL - you'll need to provide the list of URLs
        urls = [
            f"https://www.laliga.com/en-CA/news/laliga-ea-sports-matchday-{x}-preview"
            for x in range(2, 15)
        ]

        for i, url in enumerate(urls):
            print(f"Processing article {i+1}/{len(urls)}")

            article_data = extract_article_content(driver, url)
            matchday = url.split("-")[-2]
            if article_data:
                # Create filename from date
                # date = article_data["date"].replace(".", "-")
                filename = f"data/news/matchday_preview_{matchday}.json"
                save_article(article_data, filename)

            sleep(1)  # Be nice to the server

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
