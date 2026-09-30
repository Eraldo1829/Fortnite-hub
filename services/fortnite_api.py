import os
import requests


API_BASE_URL = "https://fortnite-api.com"
API_TIMEOUT = 30


# ============================================================
# API KEY
# ============================================================

def get_api_key():
    return os.getenv("FORTNITE_API_KEY")


def get_headers():

    api_key = get_api_key()

    if not api_key:
        print("❌ FORTNITE_API_KEY non configurata.")
        return None

    return {
        "Authorization": api_key
    }


# ============================================================
# GENERIC API REQUEST
# ============================================================

def api_get(endpoint, params=None, timeout=API_TIMEOUT):

    headers = get_headers()

    if not headers:
        return None

    url = f"{API_BASE_URL}{endpoint}"

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params or {},
            timeout=timeout
        )

        print(
            f"API {endpoint} -> HTTP {response.status_code}"
        )

        if response.status_code != 200:

            print(
                "❌ Risposta API:",
                response.text[:500]
            )

            return None

        return response.json()

    except requests.Timeout:

        print(
            "❌ Timeout API:",
            endpoint
        )

        return None

    except requests.RequestException as error:

        print(
            "❌ Errore richiesta API:",
            error
        )

        return None

    except ValueError as error:

        print(
            "❌ JSON non valido:",
            error
        )

        return None


# ============================================================
# SHOP
# ============================================================

def get_shop():

    result = api_get(
        "/v2/shop"
    )

    if not result:

        print(
            "❌ Shop API non ha restituito dati."
        )

        return None

    print(
        "✅ Shop API ricevuta correttamente."
    )

    return result


# ============================================================
# TEXT VALUE
# ============================================================

def get_text_value(value):

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


# ============================================================
# PREPARE SHOP
# ============================================================

def prepare_shop(shop):

    if not shop:
        return []

    data = shop.get("data")

    if not isinstance(data, dict):
        print("❌ Shop: campo data non valido.")
        return []

    entries = data.get(
        "entries",
        []
    )

    if not isinstance(entries, list):

        print(
            "❌ Shop: entries non è una lista."
        )

        return []

    print(
        "🛒 Entry Shop:",
        len(entries)
    )

    items = []

    for entry in entries:

        if not isinstance(entry, dict):
            continue

        final_price = entry.get(
            "finalPrice"
        )

        br_items = entry.get(
            "brItems",
            []
        )

        if not isinstance(br_items, list):
            continue

        if not br_items:
            continue

        first_item = br_items[0]

        if not isinstance(first_item, dict):
            continue

        raw_type = first_item.get(
            "type"
        )

        type_name = get_text_value(
            raw_type
        )

        if not type_name:
            type_name = "Cosmetico"

        type_value = ""

        if isinstance(raw_type, dict):

            type_value = (
                raw_type.get("value")
                or ""
            )

        raw_series = first_item.get(
            "series"
        )

        series_name = get_text_value(
            raw_series
        )

        raw_set = first_item.get(
            "set"
        )

        set_name = get_text_value(
            raw_set
        )

        images = first_item.get(
            "images",
            {}
        )

        if not isinstance(images, dict):
            images = {}

        image = (
            images.get("icon")
            or
            images.get("featured")
        )

        item = {

            "shop_index":
                len(items),

            "id":
                first_item.get("id"),

            "name":
                first_item.get(
                    "name",
                    "Oggetto senza nome"
                ),

            "description":
                first_item.get(
                    "description",
                    ""
                ),

            "type":
                type_name,

            "type_value":
                type_value,

            "image":
                image,

            "price":
                final_price,

            "bundle":
                len(br_items) > 1,

            "bundle_items":
                br_items,

            "series":
                series_name,

            "set":
                set_name
        }

        items.append(item)

    print(
        "✅ Oggetti Shop preparati:",
        len(items)
    )

    return items


# ============================================================
# SHOP CATEGORY
# ============================================================

def get_category_name(item):

    item_type = str(
        item.get("type_value")
        or ""
    ).lower()

    display_type = str(
        item.get("type")
        or ""
    ).lower()

    if (
        item_type == "outfit"
        or "outfit" in display_type
        or "skin" in display_type
    ):

        return "👕 Outfit"

    if (
        item_type == "emote"
        or "emote" in display_type
    ):

        return "💃 Emote"

    if (
        item_type == "pickaxe"
        or "pickaxe" in display_type
        or "piccone" in display_type
    ):

        return "⛏️ Picconi"

    if (
        item_type == "backpack"
        or "back bling" in display_type
        or "zaino" in display_type
    ):

        return "🎒 Back Bling"

    if (
        item_type == "glider"
        or "glider" in display_type
        or "deltaplano" in display_type
    ):

        return "🪂 Deltaplani"

    if (
        item_type == "wrap"
        or "wrap" in display_type
    ):

        return "🎨 Wrap"

    if (
        item_type == "music"
        or "music" in display_type
        or "musica" in display_type
    ):

        return "🎵 Musica"

    if (
        item_type == "loadingscreen"
        or "loading" in display_type
    ):

        return "🖼️ Schermate di caricamento"

    if (
        item_type == "contrail"
        or "contrail" in display_type
    ):

        return "✨ Scie"

    return "📦 Altri oggetti"


# ============================================================
# GROUP SHOP
# ============================================================

def group_shop_items(items):

    groups = {}

    for item in items:

        series = item.get(
            "series"
        )

        item_set = item.get(
            "set"
        )

        category = get_category_name(
            item
        )

        if series:

            group_name = series

        elif item_set:

            group_name = item_set

        else:

            group_name = category

        if group_name not in groups:

            groups[group_name] = {

                "name":
                    group_name,

                "category":
                    category,

                "shop_items":
                    []
            }

        groups[group_name][
            "shop_items"
        ].append(item)

    return list(
        groups.values()
    )


# ============================================================
# NORMALIZE COSMETIC
# ============================================================

def normalize_cosmetic(cosmetic):

    if not isinstance(
        cosmetic,
        dict
    ):

        return None

    images = cosmetic.get(
        "images",
        {}
    )

    if not isinstance(
        images,
        dict
    ):

        images = {}

    image = (
        images.get("icon")
        or
        images.get("featured")
        or
        images.get("smallIcon")
    )

    raw_type = cosmetic.get(
        "type",
        {}
    )

    if isinstance(
        raw_type,
        dict
    ):

        type_value = (
            raw_type.get("value")
            or ""
        )

        type_display = (
            raw_type.get("displayValue")
            or ""
        )

    else:

        type_value = str(
            raw_type or ""
        )

        type_display = str(
            raw_type or ""
        )

    rarity = cosmetic.get(
        "rarity",
        {}
    )

    if isinstance(
        rarity,
        dict
    ):

        rarity_value = (
            rarity.get("value")
            or ""
        )

        rarity_display = (
            rarity.get("displayValue")
            or rarity_value
            or "Sconosciuta"
        )

    else:

        rarity_value = str(
            rarity or ""
        )

        rarity_display = (
            rarity_value
            or "Sconosciuta"
        )

    series = cosmetic.get(
        "series"
    )

    if isinstance(
        series,
        dict
    ):

        series_name = (
            series.get("name")
            or
            series.get("displayValue")
            or
            series.get("value")
            or
            ""
        )

    else:

        series_name = (
            series or ""
        )

    item_set = cosmetic.get(
        "set"
    )

    if isinstance(
        item_set,
        dict
    ):

        set_name = (
            item_set.get("text")
            or
            item_set.get("name")
            or
            item_set.get("displayValue")
            or
            item_set.get("value")
            or
            ""
        )

    else:

        set_name = (
            item_set or ""
        )

    item = {

        "id":
            cosmetic.get("id"),

        "name":
            cosmetic.get(
                "name",
                "Oggetto senza nome"
            ),

        "description":
            cosmetic.get(
                "description",
                ""
            ),

        "type": {

            "value":
                type_value,

            "displayValue":
                type_display
        },

        "displayType":
            type_display,

        "rarity": {

            "value":
                rarity_value,

            "displayValue":
                rarity_display
        },

        "_rarity":
            rarity_display,

        "series":
            series_name,

        "set":
            set_name,

        "images": {

            "icon":
                image
        },

        "image":
            image,

        "introduction":
            cosmetic.get(
                "introduction"
            ),

        "added":
            cosmetic.get(
                "added"
            ),

        "lastAppearance":
            cosmetic.get(
                "lastAppearance"
            ),

        "shopHistory":
            cosmetic.get(
                "shopHistory",
                []
            ),

        "variants":
            cosmetic.get(
                "variants",
                []
            )
    }

    item["_category"] = get_cosmetic_category(
        item
    )

    return item


# ============================================================
# SEARCH COSMETICS
# ============================================================

def search_cosmetics(
    search_query="",
    category=""
):

    search_query = (
        search_query or ""
    ).strip()

    if not search_query:

        cosmetics = get_all_cosmetics()

        if category:

            cosmetics = [
                item
                for item in cosmetics
                if item.get("_category") == category
            ]

        return cosmetics

    result = api_get(
        "/v2/cosmetics/br/search/all",
        params={
            "language": "it",
            "searchLanguage": "it",
            "matchMethod": "contains",
            "name": search_query
        }
    )

    if not result:
        return []

    data = result.get(
        "data",
        []
    )

    if not isinstance(data, list):
        return []

    cosmetics = []

    for cosmetic in data:

        item = normalize_cosmetic(
            cosmetic
        )

        if item is None:
            continue

        if category:

            if item.get("_category") != category:
                continue

        cosmetics.append(item)

    return cosmetics


# ============================================================
# ALL COSMETICS
# ============================================================

def get_all_cosmetics():

    result = api_get(
        "/v2/cosmetics/br",
        params={
            "language": "it"
        },
        timeout=60
    )

    if not result:

        print(
            "❌ Catalogo cosmetici non disponibile."
        )

        return []

    data = result.get(
        "data",
        []
    )

    if not isinstance(data, list):

        print(
            "❌ Formato catalogo non valido."
        )

        return []

    cosmetics = []

    for cosmetic in data:

        item = normalize_cosmetic(
            cosmetic
        )

        if item is not None:
            cosmetics.append(item)

    print(
        "✅ Tutti gli Item caricati:",
        len(cosmetics)
    )

    return cosmetics


# ============================================================
# COSMETIC CATEGORY
# ============================================================

def get_cosmetic_category(item):

    raw_type = item.get(
        "type"
    )

    if isinstance(
        raw_type,
        dict
    ):

        type_value = str(
            raw_type.get("value")
            or ""
        ).lower()

        type_display = str(
            raw_type.get("displayValue")
            or ""
        ).lower()

    else:

        type_value = str(
            raw_type or ""
        ).lower()

        type_display = ""

    display_type = str(
        item.get("displayType")
        or ""
    ).lower()

    combined = (
        type_value
        + " "
        + type_display
        + " "
        + display_type
    )

    if (
        "outfit" in combined
        or "skin" in combined
    ):

        return "👕 Outfit"

    if (
        "backpack" in combined
        or "back bling" in combined
    ):

        return "🎒 Back Bling"

    if (
        "pickaxe" in combined
        or "harvesting" in combined
    ):

        return "⛏️ Picconi"

    if "glider" in combined:

        return "🪂 Deltaplani"

    if "emote" in combined:

        return "💃 Emote"

    if "wrap" in combined:

        return "🎨 Wrap"

    if "loading" in combined:

        return "🖼️ Schermate di caricamento"

    if "contrail" in combined:

        return "✨ Scie"

    if (
        "music" in combined
        or "music pack" in combined
    ):

        return "🎵 Musica"

    if "spray" in combined:

        return "🎨 Spray"

    if "banner" in combined:

        return "🏳️ Banner"

    return "📦 Altri oggetti"


# ============================================================
# CURRENT SHOP PRICES
# ============================================================

def get_current_shop_prices():

    shop = get_shop()

    if not shop:
        return {}

    data = shop.get(
        "data"
    )

    if not isinstance(
        data,
        dict
    ):

        return {}

    entries = data.get(
        "entries",
        []
    )

    if not isinstance(
        entries,
        list
    ):

        return {}

    prices = {}

    for entry in entries:

        if not isinstance(
            entry,
            dict
        ):

            continue

        final_price = entry.get(
            "finalPrice"
        )

        if final_price is None:
            continue

        br_items = entry.get(
            "brItems",
            []
        )

        if not isinstance(
            br_items,
            list
        ):

            continue

        for br_item in br_items:

            if not isinstance(
                br_item,
                dict
            ):

                continue

            item_id = br_item.get(
                "id"
            )

            if not item_id:
                continue

            prices[str(item_id)] = {

                "price":
                    final_price,

                "bundle":
                    len(br_items) > 1
            }

    return prices
