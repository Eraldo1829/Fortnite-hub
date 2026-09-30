import os
import requests


def get_shop():
    api_key = os.getenv("FORTNITE_API_KEY")

    if not api_key:
        return None

    url = "https://fortnite-api.com/v2/shop"

    headers = {
        "Authorization": api_key
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        if response.status_code != 200:
            return None

        return response.json()

    except requests.RequestException:
        return None
