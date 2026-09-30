import os
import requests


API_BASE_URL = "https://fortnite-api.com"

API_TIMEOUT = 20


# ============================================================
# API KEY
# ============================================================

def get_api_key():

    return os.getenv(
        "FORTNITE_API_KEY"
    )


# ============================================================
# SHOP
# ============================================================

def get_shop():

    api_key = get_api_key()

    if not api_key:

        print(
            "FORTNITE_API_KEY non configurata."
        )

        return None

    url = f"{API_BASE_URL}/v2/shop"

    headers = {
        "Authorization": api_key
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=API_TIMEOUT
        )

        if response.status_code != 200:

            print(
                "Errore Shop API:",
                response.status_code
            )

            return None

        return response.json()

    except requests.RequestException as error:

        print(
            "Errore richiesta Shop:",
            error
        )

        return None


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

        return []

    entries = data.get(
        "entries",
        []
    )

    if not isinstance(
        entries,
        list
    ):

        return []

    items = []

    for entry in entries:

        if not isinstance(
            entry,
            dict
        ):

            continue

        final_price = entry.get(
            "finalPrice"
        )

        br_items = entry.get(
            "brItems",
            []
        )

        if not isinstance(
            br_items,
            list
        ):

            continue

        if not br_items:

            continue

        first_item = br_items[0]

        if not isinstance(
            first_item,
            dict
        ):

            continue

        raw_type = first_item.get(
            "type"
        )

        type_name = get_text_value(
            raw_type
        )

        if not type_name:

            type_name = "Cosmetico"

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

        if not isinstance(
            images,
            dict
        ):

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
                (
                    raw_type.get(
                        "value",
                        ""
                    )
                    if isinstance(
                        raw_type,
                        dict
                    )
                    else ""
                ),

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

        items.append(
            item
        )

    return items


# ============================================================
# SHOP CATEGORY
# ============================================================

def get_category_name(item):

    item_type = str(
        item.get(
            "type_value"
        )
        or ""
    ).lower()

    display_type = str(
        item.get(
            "type"
        )
        or ""
    ).lower()

    if (
        item_type == "outfit"
        or
        "outfit" in display_type
        or
        "skin" in display_type
    ):

        return "👕 Outfit"

    if (
        item_type == "emote"
        or
        "emote" in display_type
    ):

        return "💃 Emote"

    if (
        item_type == "pickaxe"
        or
        "pickaxe" in display_type
        or
        "piccone" in display_type
    ):

        return "⛏️ Picconi"

    if (
        item_type == "backpack"
        or
        "back bling" in display_type
        or
        "zaino" in display_type
    ):

        return "🎒 Back Bling"

    if (
        item_type == "glider"
        or
        "glider" in display_type
        or
        "deltaplano" in display_type
    ):

        return "🪂 Deltaplani"

    if (
        item_type == "wrap"
        or
        "wrap" in display_type
    ):

        return "🎨 Wrap"

    if (
        item_type == "music"
        or
        "music" in display_type
        or
        "musica" in display_type
    ):

        return "🎵 Musica"

    if (
        item_type == "loadingscreen"
        or
        "loading" in display_type
    ):

        return "🖼️ Schermate di caricamento"

    if (
        item_type == "contrail"
        or
        "contrail" in display_type
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

        groups[
            group_name
        ][
            "shop_items"
        ].append(
            item
        )

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
            raw_type.get(
                "value"
            )
            or ""
        )

        type_display = (
            raw_type.get(
                "displayValue"
            )
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
            rarity.get(
                "value"
            )
            or ""
        )

        rarity_display = (
            rarity.get(
                "displayValue"
            )
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
            series.get(
                "displayValue"
            )
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
            item_set.get(
                "displayValue"
            )
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

    item["_category"] = (
        get_cosmetic_category(
            item
        )
    )

    return item


# ============================================================
# SEARCH COSMETICS
#
# Usa direttamente l'API di ricerca.
# Questo evita di scaricare tutto il catalogo quando l'utente
# sta cercando una skin.
# ============================================================

def search_cosmetics(
    search_query="",
    category=""
):

    api_key = get_api_key()

    if not api_key:

        return []

    url = (
        f"{API_BASE_URL}"
        "/v2/cosmetics/br/search/all"
    )

    headers = {

        "Authorization":
            api_key
    }

    params = {

        "language":
            "it",

        "searchLanguage":
            "it",

        "matchMethod":
            "contains"
    }

    search_query = (
        search_query or ""
    ).strip()

    if search_query:

        params["name"] = (
            search_query
        )

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

        if response.status_code != 200:

            print(
                "Errore ricerca cosmetici:",
                response.status_code
            )

            return []

        result = response.json()

        data = result.get(
            "data",
            []
        )

        if not isinstance(
            data,
            list
        ):

            return []

        cosmetics = []

        for cosmetic in data:

            item = normalize_cosmetic(
                cosmetic
            )

            if item is None:

                continue

            if category:

                if (
                    item.get(
                        "_category"
                    )
                    != category
                ):

                    continue

            cosmetics.append(
                item
            )

        return cosmetics

    except requests.RequestException as error:

        print(
            "Errore ricerca cosmetici:",
            error
        )

        return []

    except Exception as error:

        print(
            "Errore elaborazione ricerca:",
            error
        )

        return []


# ============================================================
# TUTTI GLI ITEM
#
# NOTA:
# Per compatibilità con il vecchio app.py questa funzione
# continua ad esistere.
#
# NON viene utilizzata dalla nuova pagina /all-items per
# effettuare una gigantesca cache permanente.
# ============================================================

def get_all_cosmetics():

    api_key = get_api_key()

    if not api_key:

        return []

    url = (
        f"{API_BASE_URL}"
        "/v2/cosmetics/br"
    )

    headers = {

        "Authorization":
            api_key
    }

    params = {

        "language":
            "it"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

        if response.status_code != 200:

            print(
                "Errore API Tutti gli Item:",
                response.status_code
            )

            return []

        result = response.json()

        data = result.get(
            "data",
            []
        )

        if not isinstance(
            data,
            list
        ):

            return []

        cosmetics = []

        for cosmetic in data:

            item = normalize_cosmetic(
                cosmetic
            )

            if item is not None:

                cosmetics.append(
                    item
                )

        print(
            "Tutti gli Item caricati:",
            len(cosmetics)
        )

        return cosmetics

    except requests.RequestException as error:

        print(
            "Errore richiesta Tutti gli Item:",
            error
        )

        return []

    except Exception as error:

        print(
            "Errore elaborazione Tutti gli Item:",
            error
        )

        return []


# ============================================================
# CATEGORIA COSMETICO
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
            raw_type.get(
                "value"
            )
            or ""
        ).lower()

        type_display = str(
            raw_type.get(
                "displayValue"
            )
            or ""
        ).lower()

    else:

        type_value = str(
            raw_type or ""
        ).lower()

        type_display = ""

    display_type = str(
        item.get(
            "displayType"
        )
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
        or
        "skin" in combined
    ):

        return "👕 Outfit"

    if (
        "backpack" in combined
        or
        "back bling" in combined
    ):

        return "🎒 Back Bling"

    if (
        "pickaxe" in combined
        or
        "harvesting" in combined
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
        or
        "music pack" in combined
    ):

        return "🎵 Musica"

    if "spray" in combined:

        return "🎨 Spray"

    if "banner" in combined:

        return "🏳️ Banner"

    return "📦 Altri oggetti"


# ============================================================
# PREZZI SHOP ATTUALE
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

            prices[
                str(item_id)
            ] = {

                "price":
                    final_price,

                "bundle":
                    len(br_items) > 1
            }

    return prices
