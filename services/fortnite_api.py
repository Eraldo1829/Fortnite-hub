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

        first_item = br_items[0]

        item_type = first_item.get("type", {})

        series = first_item.get("series")
        item_set = first_item.get("set")

        series_name = None
        set_name = None

        if isinstance(series, dict):
            series_name = series.get("name")

        if isinstance(item_set, dict):
            set_name = item_set.get("text")

            if not set_name:
                set_name = item_set.get("name")

        item = {
            "name": first_item.get(
                "name",
                "Oggetto senza nome"
            ),

            "description": first_item.get(
                "description",
                ""
            ),

            "type": item_type.get(
                "displayValue",
                "Cosmetico"
            ),

            "type_value": first_item.get(
                "type",
                {}
            ).get(
                "value",
                ""
            ),

            "image": first_item.get(
                "images",
                {}
            ).get("icon"),

            "price": final_price,

            "bundle": len(br_items) > 1,

            "bundle_items": br_items,

            "series": series_name,

            "set": set_name
        }

        items.append(item)

    return items


def get_category_name(item):

    """
    Determina la categoria principale
    dell'oggetto.
    """

    item_type = (
        item.get("type_value")
        or ""
    ).lower()

    display_type = (
        item.get("type")
        or ""
    ).lower()


    # OUTFIT / SKIN

    if (
        item_type == "outfit"
        or "outfit" in display_type
        or "skin" in display_type
    ):
        return "👕 Outfit"


    # EMOTE

    if (
        item_type == "emote"
        or "emote" in display_type
    ):
        return "💃 Emote"


    # PICKAXE

    if (
        item_type == "pickaxe"
        or "pickaxe" in display_type
        or "piccone" in display_type
    ):
        return "⛏️ Picconi"


    # BACK BLING

    if (
        item_type == "backpack"
        or "back bling" in display_type
        or "zaino" in display_type
    ):
        return "🎒 Back Bling"


    # GLIDER

    if (
        item_type == "glider"
        or "glider" in display_type
        or "deltaplano" in display_type
    ):
        return "🪂 Deltaplani"


    # WRAP

    if (
        item_type == "wrap"
        or "wrap" in display_type
    ):
        return "🎨 Wrap"


    # MUSIC

    if (
        item_type == "music"
        or "music" in display_type
        or "musica" in display_type
    ):
        return "🎵 Musica"


    # LOADING SCREEN

    if (
        item_type == "loadingscreen"
        or "loading" in display_type
    ):
        return "🖼️ Schermate di caricamento"


    # TRAIL / CONTRAIL

    if (
        item_type == "contrail"
        or "contrail" in display_type
    ):
        return "✨ Scie"


    # DEFAULT

    return "📦 Altri oggetti"


def group_shop_items(items):

    """
    Organizza gli oggetti in sezioni.

    Prima vengono considerate le collaborazioni/set.
    Successivamente il tipo di oggetto.
    """

    groups = {}

    for item in items:

        series = item.get("series")
        item_set = item.get("set")

        category = get_category_name(item)


        # =========================
        # COLLAB / SET
        # =========================

        if series:

            group_name = series

        elif item_set:

            group_name = item_set

        else:

            group_name = category


        if group_name not in groups:

            groups[group_name] = {
                "name": group_name,
                "category": category,
                "items": []
            }


        groups[group_name]["items"].append(item)


    # =========================
    # ORDINE
    # =========================

    ordered_groups = list(
        groups.values()
    )


    return ordered_groups
