import json
import os
from time import sleep

import pandas as pd
import requests
from dotenv import load_dotenv


def fetch_matches(week, subscription_key):
    url = f"https://apim.laliga.com/webview/api/web/subscriptions/laliga-easports-2024/week/{week}/matches"
    params = {"contentLanguage": "en", "subscription-key": subscription_key}

    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(
            f"Failed to fetch data for week {week}. Status code: {response.status_code}"
        )


def process_match_data(raw_data, week, for_json=True):
    processed_matches = []

    for match in raw_data["matches"]:
        if for_json:
            processed_match = {
                "week": week,
                "home_team": match["home_team"]["shortname"],
                "away_team": match["away_team"]["shortname"],
                "home_score": match["home_score"],
                "away_score": match["away_score"],
            }
        else:
            processed_match = {
                "home_team": match["home_team"]["shortname"],
                "away_team": match["away_team"]["shortname"],
                "home_score": match["home_score"],
                "away_score": match["away_score"],
            }
        processed_matches.append(processed_match)

    return processed_matches


def main():
    load_dotenv()

    subscription_key = os.getenv("LALIGA_API_KEY")
    if not subscription_key:
        raise ValueError("LALIGA_API_KEY not found in environment variables")

    os.makedirs("data/matches", exist_ok=True)

    all_matches = []

    for week in range(1, 15):
        try:
            print(f"Fetching matches for week {week}...")

            raw_data = fetch_matches(week, subscription_key)

            # Process for JSON (includes week)
            json_matches = process_match_data(raw_data, week, for_json=True)
            all_matches.extend(json_matches)

            # Process for CSV (excludes week)
            csv_matches = process_match_data(raw_data, week, for_json=False)
            df = pd.DataFrame(csv_matches)
            csv_filename = f"data/matches/week{week}.csv"
            df.to_csv(csv_filename, index=False)

            print(f"Processed week {week} - {len(csv_matches)} matches")
            sleep(1)

        except Exception as e:
            print(f"Error processing week {week}: {e}")
            continue

    with open("data/matches/all_matches.json", "w", encoding="utf-8") as f:
        json.dump(all_matches, f, ensure_ascii=False, indent=2)

    print("Data collection complete!")


if __name__ == "__main__":
    main()
