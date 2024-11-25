import os
from time import sleep

import pandas as pd
import requests
from dotenv import load_dotenv


def fetch_standings(week, subscription_key):
    url = "https://apim.laliga.com/webview/api/web/subscriptions/laliga-easports-2024/standing"
    params = {
        "week": week,
        "contentLanguage": "en",
        "subscription-key": subscription_key,
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(
            f"Failed to fetch data for week {week}. Status code: {response.status_code}"
        )


def process_standings_data(raw_data):
    processed_data = []

    for team in raw_data["standings"]:
        processed_team = {
            "position": team["position"],
            "team": team["team"]["nickname"],
            "points": team["points"],
            "played": team["played"],
            "won": team["won"],
            "drawn": team["drawn"],
            "lost": team["lost"],
            "goals_for": team["goals_for"],
            "goals_against": team["goals_against"],
            "goal_difference": team["goal_difference"],
        }
        processed_data.append(processed_team)

    return pd.DataFrame(processed_data)


def main():
    # Load environment variables
    load_dotenv()

    # Get API key from environment variable
    subscription_key = os.getenv("LALIGA_API_KEY")
    if not subscription_key:
        raise ValueError("LALIGA_API_KEY not found in environment variables")

    os.makedirs("data/standings", exist_ok=True)

    for week in range(1, 15):
        try:
            print(f"Fetching data for week {week}...")

            raw_data = fetch_standings(week, subscription_key)
            df = process_standings_data(raw_data)

            filename = f"data/standings/week{week}.csv"
            df.to_csv(filename, index=False)
            print(f"Saved data to {filename}")

            sleep(1)

        except Exception as e:
            print(f"Error processing week {week}: {e}")
            continue


if __name__ == "__main__":
    main()
