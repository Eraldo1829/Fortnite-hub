```python
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


def get_text_value(value):

    """
    Estrae in modo sicuro un valore testuale.
    Il campo può essere una stringa oppure un dizionario.
    """

    if isinstance(value, str):
        return value

    if isinstance(value, dict):

        return (
            value.get("displayValue")
            or value.get("text")
            or value.get("name")
            or value.get("value")
        )

    return None


def prepare_shop(shop):

    if not shop:
        return []

    if "data" not in shop:
        return []

    data = shop.get("data")

    if not isinstance(data, dict):
        return []

    entries = data.get("entries", [])

    if not isinstance(entries, list):
        return []

    items = []

    for entry in entries:

        if not isinstance(entry, dict):
            continue

        final_price = entry.get("finalPrice")

        br_items = entry.get("brItems", [])

        if not isinstance(br_items, list):
            continue

        if len(br_items) == 0:
            continue

        first_item = br_items[0]

        if not isinstance(first_item, dict):
            continue


        # =========================
        # TYPE
        # =========================

        raw_type = first_item.get("type")

        type_name = get_text_value(
            raw_type
        )

        if not type_name:
            type_name = "Cosmetico"


        # =========================
        # SERIES
        # =========================

        raw_series = first_item.get(
            "series"
        )

        series_name = get_text_value(
            raw_series
        )


        # =========================
        # SET
        # =========================

        raw_set = first_item.get(
            "set"
        )

        set_name = get_text_value(
            raw_set
        )


        # =========================
        # IMAGE
        # =========================

        images = first_item.get(
            "images",
            {}
        )

        if not isinstance(images, dict):
            images = {}

        image = images.get("icon")


        # =========================
        # ITEM
        # =========================

        item = {

            "shop_index": len(items),

            "name": first_item.get(
                "name",
                "Oggetto senza nome"
            ),

            "description": first_item.get(
                "description",
                ""
            ),

            "type": type_name,

            "type_value": (
                raw_type.get("value", "")
                if isinstance(raw_type, dict)
                else ""
            ),

            "image": image,

            "price": final_price,

            "bundle": len(br_items) > 1,

            "bundle_items": br_items,

            "series": series_name,

            "set": set_name
        }

        items.append(item)

    return items


def get_category_name(item):

    item_type = str(
        item.get("type_value") or ""
    ).lower()

    display_type = str(
        item.get("type") or ""
    ).lower()


    # OUTFIT

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


    # CONTRAIL

    if (
        item_type == "contrail"
        or "contrail" in display_type
    ):

        return "✨ Scie"


    return "📦 Altri oggetti"


def group_shop_items(items):

    groups = {}

    for item in items:

        series = item.get("series")

        item_set = item.get("set")

        category = get_category_name(
            item
        )


        # =========================
        # DETERMINA GRUPPO
        # =========================

        if series:

            group_name = series

        elif item_set:

            group_name = item_set

        else:

            group_name = category


        # =========================
        # CREA GRUPPO
        # =========================

        if group_name not in groups:

            groups[group_name] = {

                "name": group_name,

                "category": category,

                "shop_items": []

            }


        # =========================
        # AGGIUNGI OGGETTO
        # =========================

        groups[group_name][
            "shop_items"
        ].append(item)


    return list(
        groups.values()
    )
```
