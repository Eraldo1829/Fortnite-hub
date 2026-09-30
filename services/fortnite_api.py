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


def prepare_shop(shop):
    if not shop or "data" not in shop:
        return []

    entries = shop["data"].get("entries", [])

    items = []

    for entry in entries:

        final_price = entry.get("finalPrice")

        br_items = entry.get("brItems", [])

        if not br_items:
            continue

        # Prendiamo le informazioni dell'offerta
        first_item = br_items[0]

        item = {
            "name": first_item.get("name", "Oggetto senza nome"),
            "description": first_item.get("description", ""),
            "type": first_item.get("type", {}).get(
                "displayValue",
                "Cosmetico"
            ),
            "image": first_item.get("images", {}).get("icon"),
            "price": final_price,
            "items": br_items,
            "bundle": len(br_items) > 1
        }

        items.append(item)

    return items
