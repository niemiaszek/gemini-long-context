import json
import os
from time import sleep
from typing import Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    return driver


def fetch_matches(
    week: int, subscription_key: str, max_retries: int = 3
) -> Optional[Dict]:
    url = f"https://apim.laliga.com/webview/api/web/subscriptions/laliga-easports-2024/week/{week}/matches"
    params = {"contentLanguage": "en", "subscription-key": subscription_key}

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            if attempt == max_retries - 1:
                print(
                    f"Failed to fetch data for week {week} after {max_retries} attempts: {str(e)}"
                )
                raise
            print(f"Attempt {attempt + 1} failed, retrying...")
            sleep(2**attempt)  # Exponential backoff


def get_match_stats(
    driver: webdriver.Chrome, match_url: str, max_retries: int = 3
) -> Optional[Dict]:
    for attempt in range(max_retries):
        try:
            driver.get(f"https://www.laliga.com/en-ES/match/{match_url}")
            wait = WebDriverWait(driver, 10)

            stats_tab = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//div[contains(@class, 'BtnTab')]//p[text()='Stats']/..",
                    )
                )
            )

            driver.execute_script("arguments[0].scrollIntoView(true);", stats_tab)
            driver.execute_script("window.scrollBy(0, -100);")
            sleep(1)

            wait.until(EC.element_to_be_clickable(stats_tab))

            try:
                stats_tab.click()
            except:
                driver.execute_script("arguments[0].click();", stats_tab)

            sleep(2)
            stats_container = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[class^='styled__ContainerStats']")
                )
            )

            stat_elements = stats_container.find_elements(
                By.CSS_SELECTOR, "[class^='styled__Stat']"
            )

            stats = {}
            for stat in stat_elements:
                label = stat.find_element(
                    By.CSS_SELECTOR, "[class^='styled__ContainerTexts'] > p"
                ).text.lower()
                values = stat.find_elements(
                    By.CSS_SELECTOR, "[class^='styled__ContainerText'] p"
                )
                home_value = values[0].text.rstrip("%")
                away_value = values[1].text.rstrip("%")

                try:
                    if "." in home_value or "." in away_value:
                        home_value = float(home_value)
                        away_value = float(away_value)
                    else:
                        home_value = int(home_value.split()[0])
                        away_value = int(away_value.split()[0])
                except (ValueError, IndexError):
                    pass

                key = label.lower().replace(" ", "_")
                stats[key] = {"home": home_value, "away": away_value}

            return stats

        except WebDriverException as e:
            if attempt == max_retries - 1:
                print(
                    f"Error getting stats for {match_url} after {max_retries} attempts: {str(e)}"
                )
                return None
            print(f"Attempt {attempt + 1} failed for {match_url}, retrying...")
            sleep(2**attempt)


def process_match_data(
    raw_data: Dict,
    week: int,
    driver: Optional[webdriver.Chrome] = None,
    detailed: bool = False,
) -> List[Dict]:
    if detailed:
        matches = []
        for match in raw_data["matches"]:
            try:
                match_data = {
                    "home_team": {
                        "shortname": match["home_team"]["shortname"],
                        "score": match["home_score"],
                    },
                    "away_team": {
                        "shortname": match["away_team"]["shortname"],
                        "score": match["away_score"],
                    },
                }

                if match["status"] == "FullTime" and driver:
                    print(f"Getting stats for {match['slug']}...")
                    stats = get_match_stats(driver, match["slug"])
                    if stats:
                        for stat_name, stat_values in stats.items():
                            match_data["home_team"][stat_name] = stat_values["home"]
                            match_data["away_team"][stat_name] = stat_values["away"]

                matches.append(match_data)
            except KeyError as e:
                print(f"Error processing match in week {week}, adding empty data")
                # Add empty data structure to preserve the match position
                matches.append(
                    {
                        "home_team": {"shortname": "ERROR", "score": None},
                        "away_team": {"shortname": "ERROR", "score": None},
                        "error": f"Missing key: {str(e)}",
                    }
                )
        return matches
    else:
        # Simple CSV format - skip problematic matches
        csv_matches = []
        for match in raw_data["matches"]:
            try:
                csv_matches.append(
                    {
                        "home_team": match["home_team"]["shortname"],
                        "home_score": match["home_score"],
                        "away_team": match["away_team"]["shortname"],
                        "away_score": match["away_score"],
                    }
                )
            except KeyError as e:
                print(f"Error processing match for CSV in week {week}: {str(e)}")
        return csv_matches


def main():
    load_dotenv()

    subscription_key = os.getenv("LALIGA_API_KEY")
    if not subscription_key:
        raise ValueError("LALIGA_API_KEY not found in environment variables")

    os.makedirs("data/matches", exist_ok=True)

    driver = setup_driver()
    matches_by_week = {}

    try:
        for week in range(1, 15):
            try:
                print(f"Fetching matches for week {week}...")

                raw_data = fetch_matches(week, subscription_key)
                if not raw_data:
                    print(f"No data received for week {week}, skipping...")
                    continue

                # Process detailed data for JSON
                detailed_matches = process_match_data(
                    raw_data, week, driver=driver, detailed=True
                )
                if detailed_matches:
                    matches_by_week[f"week{week}"] = detailed_matches

                # Process simple data for CSV
                csv_matches = process_match_data(raw_data, week, detailed=False)
                if csv_matches:
                    df = pd.DataFrame(csv_matches)
                    csv_filename = f"data/matches/week{week}.csv"
                    df.to_csv(csv_filename, index=False)
                    print(f"Processed week {week} - {len(csv_matches)} matches")

                sleep(1)

            except Exception as e:
                print(f"Error processing week {week}: {str(e)}")
                print("Continuing to next week...")
                continue

        if matches_by_week:
            with open("data/matches/matches_detailed.json", "w", encoding="utf-8") as f:
                json.dump(matches_by_week, f, ensure_ascii=False, indent=2)
        else:
            print("No data was collected, skipping JSON file creation")

    finally:
        driver.quit()

    print("Data collection complete!")


if __name__ == "__main__":
    main()
