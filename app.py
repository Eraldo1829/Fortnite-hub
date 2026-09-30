import os
import json
from datetime import datetime, date

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database.database import (
    create_database,
    get_connection
)

from services.email_service import (
    send_welcome_email
)

from services.tracker_service import (
    run_tracker_check
)

from services.fortnite_api import (
    get_shop,
    prepare_shop,
    group_shop_items,
    get_all_cosmetics,
    search_cosmetics,
    get_cosmetic_category,
    get_current_shop_prices
)


# ============================================================
# APP
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "fortnite-hub-development-key"
)

create_database()


# ============================================================
# FEATURE TABLES
# ============================================================

def create_feature_tables():

    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # FAVORITES
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            item_id TEXT NOT NULL,

            item_name TEXT,

            image_url TEXT,

            data_json TEXT,

            created_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(
                user_id,
                item_id
            )
        )
        """
    )

    # --------------------------------------------------------
    # SHOP HISTORY
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS shop_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            shop_date TEXT NOT NULL,

            item_id TEXT NOT NULL,

            item_name TEXT,

            image_url TEXT,

            data_json TEXT,

            saved_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(
                shop_date,
                item_id
            )
        )
        """
    )

    # --------------------------------------------------------
    # NOTIFICATION LOG
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_log (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            item_id TEXT NOT NULL,

            shop_date TEXT NOT NULL,

            item_name TEXT,

            sent_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(
                user_id,
                item_id,
                shop_date
            )
        )
        """
    )

    # --------------------------------------------------------
    # NOTIFICATION SETTINGS
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_settings (

            user_id INTEGER PRIMARY KEY,

            enabled INTEGER NOT NULL DEFAULT 1,

            updated_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


create_feature_tables()


# ============================================================
# HELPERS
# ============================================================

def login_required():
    return "user_id" in session


# ------------------------------------------------------------
# ITEM ID
# ------------------------------------------------------------

def get_item_id(item, fallback_index=None):

    if not isinstance(item, dict):
        return None

    possible_keys = [
        "id",
        "itemId",
        "item_id",
        "offerId",
        "templateId",
        "assetId"
    ]

    for key in possible_keys:

        value = item.get(key)

        if value:
            return str(value)

    if fallback_index is not None:
        return f"item-{fallback_index}"

    return None


# ------------------------------------------------------------
# ITEM NAME
# ------------------------------------------------------------

def get_item_name(item):

    if not isinstance(item, dict):
        return "Skin senza nome"

    possible_keys = [
        "name",
        "displayName",
        "title"
    ]

    for key in possible_keys:

        value = item.get(key)

        if value:
            return str(value)

    return "Skin senza nome"


# ------------------------------------------------------------
# ITEM IMAGE
# ------------------------------------------------------------

def get_item_image(item):

    if not isinstance(item, dict):
        return None

    possible_keys = [
        "image",
        "imageUrl",
        "image_url",
        "icon",
        "iconUrl",
        "featuredImage"
    ]

    for key in possible_keys:

        value = item.get(key)

        if value:
            return str(value)

    return None


# ------------------------------------------------------------
# SHOP DATE
# ------------------------------------------------------------

def get_shop_date(shop):

    if not shop:
        return None

    data = shop.get("data")

    if isinstance(data, dict):

        shop_date = data.get("date")

        if shop_date:
            return str(shop_date)

    shop_date = shop.get("date")

    if shop_date:
        return str(shop_date)

    return None


# ------------------------------------------------------------
# PREPARE SHOP TEMPLATE DATA
# ------------------------------------------------------------

def prepare_shop_template_items(
    shop_items,
    favorite_ids
):

    prepared = []

    for index, item in enumerate(shop_items):

        if not isinstance(item, dict):
            continue

        item_id = get_item_id(
            item,
            index
        )

        item_name = get_item_name(
            item
        )

        image_url = get_item_image(
            item
        )

        # Manteniamo i dati originali
        item["_shop_index"] = index

        item["_item_id"] = (
            item_id
        )

        item["_item_name"] = (
            item_name
        )

        item["_image_url"] = (
            image_url
        )

        item["_is_favorite"] = (
            str(item_id) in favorite_ids
            if item_id
            else False
        )

        # Compatibilità anche con eventuali
        # parti del template che usano il nome semplice
        item["is_favorite"] = (
            item["_is_favorite"]
        )

        prepared.append(item)

    return prepared


# ------------------------------------------------------------
# SAVE SHOP HISTORY
# ------------------------------------------------------------

def save_shop_history(
    shop_date,
    shop_items
):

    if not shop_date:
        return

    connection = get_connection()
    cursor = connection.cursor()

    for index, item in enumerate(shop_items):

        item_id = get_item_id(
            item,
            index
        )

        if not item_id:
            continue

        item_name = get_item_name(item)
        image_url = get_item_image(item)

        try:

            data_json = json.dumps(
                item,
                ensure_ascii=False
            )

        except Exception:

            data_json = "{}"

        cursor.execute(
            """
            INSERT INTO shop_history
            (
                shop_date,
                item_id,
                item_name,
                image_url,
                data_json
            )

            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(
                shop_date,
                item_id
            )

            DO UPDATE SET

                item_name =
                    excluded.item_name,

                image_url =
                    excluded.image_url,

                data_json =
                    excluded.data_json
            """,
            (
                shop_date,
                item_id,
                item_name,
                image_url,
                data_json
            )
        )

    connection.commit()
    connection.close()


# ------------------------------------------------------------
# FAVORITE IDS
# ------------------------------------------------------------

def get_favorite_ids(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT item_id

        FROM favorites

        WHERE user_id = ?
        """,
        (
            user_id,
        )
    )

    rows = cursor.fetchall()

    connection.close()

    return {
        str(row["item_id"])
        for row in rows
    }


# ------------------------------------------------------------
# ITEM HISTORY STATS
# ------------------------------------------------------------

def get_item_history_stats(item_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT shop_date

        FROM shop_history

        WHERE item_id = ?

        ORDER BY shop_date DESC
        """,
        (
            str(item_id),
        )
    )

    rows = cursor.fetchall()

    connection.close()

    dates = []

    for row in rows:

        raw_date = row["shop_date"]

        if not raw_date:
            continue

        parsed_date = None

        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f"
        ]

        for fmt in formats:

            try:

                parsed_date = datetime.strptime(
                    raw_date[:26],
                    fmt
                ).date()

                break

            except Exception:
                continue

        if parsed_date:
            dates.append(parsed_date)

    if not dates:

        return {
            "last_date": None,
            "first_date": None,
            "days_since": None,
            "appearances": 0
        }

    dates = sorted(
        set(dates),
        reverse=True
    )

    last_date = dates[0]
    first_date = dates[-1]

    today = date.today()

    days_since = (
        today - last_date
    ).days

    return {
        "last_date":
            last_date.strftime(
                "%d/%m/%Y"
            ),

        "first_date":
            first_date.strftime(
                "%d/%m/%Y"
            ),

        "days_since":
            days_since,

        "appearances":
            len(dates)
    }


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not username or not email or not password:

            return render_template(
                "register.html",
                error="Compila tutti i campi."
            )

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id

            FROM users

            WHERE email = ?

            LIMIT 1
            """,
            (
                email,
            )
        )

        existing_user = cursor.fetchone()

        if existing_user:

            connection.close()

            return render_template(
                "register.html",
                error="Email già registrata."
            )

        password_hash = generate_password_hash(
            password
        )

        try:

            cursor.execute(
                """
                INSERT INTO users
                (
                    username,
                    email,
                    password
                )

                VALUES (?, ?, ?)
                """,
                (
                    username,
                    email,
                    password_hash
                )
            )

            connection.commit()

        except Exception as error:

            connection.close()

            print(
                "❌ Errore registrazione:",
                error
            )

            return render_template(
                "register.html",
                error="Errore durante la registrazione."
            )

        connection.close()

        send_welcome_email(
            email,
            username
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *

            FROM users

            WHERE email = ?

            LIMIT 1
            """,
            (
                email,
            )
        )

        user = cursor.fetchone()

        connection.close()

        if not user:

            return render_template(
                "login.html",
                error="Email o password non corretti."
            )

        if not check_password_hash(
            user["password"],
            password
        ):

            return render_template(
                "login.html",
                error="Email o password non corretti."
            )

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["email"] = user["email"]

        return redirect(
            url_for("home")
        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ============================================================
# SHOP
# ============================================================

@app.route("/skins")
def skins():

    try:

        shop = get_shop()

    except Exception as error:

        print(
            "❌ Errore caricamento Shop:",
            error
        )

        shop = None

    if not shop:

        return render_template(
            "skins.html",

            shop_groups=[],

            items=[],

            search_query="",

            favorite_ids=set(),

            shop_date=None
        )

    try:

        shop_items = prepare_shop(
            shop
        )

    except Exception as error:

        print(
            "❌ Errore preparazione Shop:",
            error
        )

        shop_items = []

    shop_date = get_shop_date(
        shop
    )

    save_shop_history(
        shop_date,
        shop_items
    )

    favorite_ids = set()

    if login_required():

        favorite_ids = get_favorite_ids(
            session["user_id"]
        )

    search_query = request.args.get(
        "search",
        ""
    ).strip()

    # --------------------------------------------------------
    # RICERCA SHOP
    # --------------------------------------------------------

    if search_query:

        search_lower = (
            search_query.lower()
        )

        filtered_items = []

        for item in shop_items:

            name = get_item_name(
                item
            ).lower()

            if search_lower in name:

                filtered_items.append(
                    item
                )

        shop_items = filtered_items

    # --------------------------------------------------------
    # PREPARAZIONE TEMPLATE
    # --------------------------------------------------------

    shop_items = prepare_shop_template_items(
        shop_items,
        favorite_ids
    )

    # --------------------------------------------------------
    # GRUPPI
    # --------------------------------------------------------

    shop_groups = group_shop_items(
        shop_items
    )

    return render_template(
        "skins.html",

        shop_groups=shop_groups,

        items=shop_items,

        search_query=search_query,

        favorite_ids=favorite_ids,

        shop_date=shop_date
    )


# ============================================================
# SHOP ITEM DETAIL
# ============================================================

@app.route(
    "/skins/<int:item_index>"
)
def skin_detail_by_index(
    item_index
):

    shop = get_shop()

    if not shop:

        return redirect(
            url_for("skins")
        )

    shop_items = prepare_shop(
        shop
    )

    if (
        item_index < 0
        or item_index >= len(shop_items)
    ):

        return redirect(
            url_for("skins")
        )

    item = shop_items[
        item_index
    ]

    item_id = get_item_id(
        item,
        item_index
    )

    history = get_item_history_stats(
        item_id
    )

    is_favorite = False

    if login_required():

        favorite_ids = get_favorite_ids(
            session["user_id"]
        )

        is_favorite = (
            str(item_id)
            in favorite_ids
        )

    return render_template(
        "skin_detail.html",

        item=item,

        item_id=item_id,

        history=history,

        is_favorite=is_favorite,

        from_shop=True
    )


# ============================================================
# ALL ITEMS
# ============================================================

@app.route("/all-items")
def all_items():

    search_query = request.args.get(
        "search",
        ""
    ).strip()

    selected_category = request.args.get(
        "category",
        ""
    ).strip()

    try:

        page = int(
            request.args.get(
                "page",
                1
            )
        )

    except ValueError:

        page = 1

    if page < 1:
        page = 1

    # --------------------------------------------------------
    # CARICA CATALOGO
    # --------------------------------------------------------

    try:

        cosmetics = get_all_cosmetics()

    except Exception as error:

        print(
            "❌ Errore caricamento catalogo:",
            error
        )

        cosmetics = []

    # --------------------------------------------------------
    # CATEGORIE DISPONIBILI
    # --------------------------------------------------------

    categories = set()

    for cosmetic in cosmetics:

        try:

            item_category = get_cosmetic_category(
                cosmetic
            )

        except Exception:

            item_category = ""

        if item_category:
            categories.add(
                item_category
            )

    categories = sorted(
        categories
    )

    # --------------------------------------------------------
    # RICERCA
    # --------------------------------------------------------

    if search_query:

        search_lower = (
            search_query.lower()
        )

        filtered_cosmetics = []

        for item in cosmetics:

            name = get_item_name(
                item
            ).lower()

            item_id = get_item_id(
                item
            )

            item_id_text = (
                str(item_id).lower()
                if item_id
                else ""
            )

            if (
                search_lower in name
                or search_lower in item_id_text
            ):

                filtered_cosmetics.append(
                    item
                )

        cosmetics = filtered_cosmetics

    # --------------------------------------------------------
    # FILTRO CATEGORIA
    # --------------------------------------------------------

    if selected_category:

        filtered_cosmetics = []

        for item in cosmetics:

            try:

                item_category = (
                    get_cosmetic_category(
                        item
                    )
                )

            except Exception:

                item_category = ""

            if (
                item_category
                == selected_category
            ):

                filtered_cosmetics.append(
                    item
                )

        cosmetics = filtered_cosmetics

    # --------------------------------------------------------
    # PAGINAZIONE
    # --------------------------------------------------------

    per_page = 60

    total_results = len(
        cosmetics
    )

    total_pages = max(
        1,
        (
            total_results
            + per_page
            - 1
        ) // per_page
    )

    if page > total_pages:
        page = total_pages

    start = (
        page - 1
    ) * per_page

    end = (
        start + per_page
    )

    page_cosmetics = cosmetics[
        start:end
    ]

    has_next = (
        page < total_pages
    )

    # --------------------------------------------------------
    # PREZZI SHOP
    # --------------------------------------------------------

    try:

        current_prices = (
            get_current_shop_prices()
        )

    except Exception as error:

        print(
            "⚠️ Errore recupero prezzi Shop:",
            error
        )

        current_prices = {}

    # --------------------------------------------------------
    # PREFERITI
    # --------------------------------------------------------

    favorite_ids = set()

    if login_required():

        favorite_ids = get_favorite_ids(
            session["user_id"]
        )

    # --------------------------------------------------------
    # PREPARAZIONE ITEM
    # --------------------------------------------------------

    prepared_cosmetics = []

    for item in page_cosmetics:

        item_id = get_item_id(
            item
        )

        item_name = get_item_name(
            item
        )

        image_url = get_item_image(
            item
        )

        try:

            item_category = get_cosmetic_category(
                item
            )

        except Exception:

            item_category = "📦 Altri oggetti"

        price_data = None

        if item_id:

            price_data = current_prices.get(
                str(item_id)
            )

        # Campi usati dal template
        item["_item_id"] = item_id
        item["_item_name"] = item_name
        item["_image_url"] = image_url
        item["_category"] = item_category

        item["_shop_price"] = price_data

        item["_shop_bundle"] = (
            bool(
                price_data.get("bundle")
            )
            if isinstance(
                price_data,
                dict
            )
            else False
        )

        item["_is_favorite"] = (
            str(item_id)
            in favorite_ids
            if item_id
            else False
        )

        prepared_cosmetics.append(
            item
        )

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "all_items.html",

        cosmetics=prepared_cosmetics,

        selected_category=selected_category,

        categories=categories,

        search_query=search_query,

        page=page,

        total_pages=total_pages,

        total_results=total_results,

        total_items=total_results,

        has_next=has_next,

        favorite_ids=favorite_ids
    )


# ============================================================
# ALL ITEM DETAIL
# ============================================================

@app.route(
    "/all-items/<path:item_id>"
)
def all_item_detail(
    item_id
):

    try:

        cosmetics = get_all_cosmetics()

    except Exception as error:

        print(
            "❌ Errore caricamento catalogo:",
            error
        )

        cosmetics = []

    item = None

    for cosmetic in cosmetics:

        cosmetic_id = get_item_id(
            cosmetic
        )

        if (
            cosmetic_id
            and str(cosmetic_id)
            == str(item_id)
        ):

            item = cosmetic
            break

    if not item:

        return redirect(
            url_for("all_items")
        )

    history = get_item_history_stats(
        item_id
    )

    try:

        current_prices = (
            get_current_shop_prices()
        )

    except Exception as error:

        print(
            "⚠️ Errore recupero prezzo:",
            error
        )

        current_prices = {}

    current_price = current_prices.get(
        str(item_id)
    )

    is_favorite = False

    if login_required():

        favorite_ids = get_favorite_ids(
            session["user_id"]
        )

        is_favorite = (
            str(item_id)
            in favorite_ids
        )

    return render_template(
        "all_item_detail.html",

        item=item,

        item_id=item_id,

        history=history,

        current_price=current_price,

        is_favorite=is_favorite
    )


# ============================================================
# FAVORITE DETAIL
# ============================================================

@app.route(
    "/favorites/<path:item_id>"
)
def favorite_detail(
    item_id
):

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *

        FROM favorites

        WHERE
            user_id = ?

            AND item_id = ?

        LIMIT 1
        """,
        (
            session["user_id"],
            str(item_id)
        )
    )

    favorite = cursor.fetchone()

    connection.close()

    if not favorite:

        return redirect(
            url_for("favorites")
        )

    # --------------------------------------------------------
    # AGGIORNA STORICO
    # --------------------------------------------------------

    try:

        shop = get_shop()

        if shop:

            shop_items = prepare_shop(
                shop
            )

            shop_date = get_shop_date(
                shop
            )

            save_shop_history(
                shop_date,
                shop_items
            )

    except Exception as error:

        print(
            "⚠️ Errore aggiornamento storico:",
            error
        )

    # --------------------------------------------------------
    # RECUPERA JSON
    # --------------------------------------------------------

    item_data = {}

    try:

        if favorite["data_json"]:

            item_data = json.loads(
                favorite["data_json"]
            )

    except Exception:

        item_data = {}

    if not item_data:

        item_data = {

            "id":
                favorite["item_id"],

            "name":
                favorite["item_name"],

            "image":
                favorite["image_url"]
        }

    history = get_item_history_stats(
        item_id
    )

    return render_template(
        "skin_detail.html",

        item=item_data,

        item_id=item_id,

        history=history,

        is_favorite=True,

        from_shop=False
    )


# ============================================================
# ADD FAVORITE
# ============================================================

@app.route(
    "/favorites/add",
    methods=["POST"]
)
def add_favorite():

    if not login_required():

        return redirect(
            url_for("login")
        )

    item_id = request.form.get(
        "item_id",
        ""
    ).strip()

    item_name = request.form.get(
        "item_name",
        ""
    ).strip()

    image_url = request.form.get(
        "image_url",
        ""
    ).strip()

    data_json = request.form.get(
        "data_json",
        ""
    )

    redirect_to = request.form.get(
        "redirect_to",
        ""
    )

    if not item_id:

        return redirect(
            redirect_to
            or url_for("skins")
        )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO favorites
        (
            user_id,
            item_id,
            item_name,
            image_url,
            data_json
        )

        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(
            user_id,
            item_id
        )

        DO UPDATE SET

            item_name =
                excluded.item_name,

            image_url =
                excluded.image_url,

            data_json =
                excluded.data_json
        """,
        (
            session["user_id"],
            item_id,
            item_name,
            image_url,
            data_json
        )
    )

    connection.commit()
    connection.close()

    return redirect(
        redirect_to
        or url_for("favorites")
    )


# ============================================================
# REMOVE FAVORITE
# ============================================================

@app.route(
    "/favorites/remove",
    methods=["POST"]
)
def remove_favorite():

    if not login_required():

        return redirect(
            url_for("login")
        )

    item_id = request.form.get(
        "item_id",
        ""
    ).strip()

    redirect_to = request.form.get(
        "redirect_to",
        ""
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM favorites

        WHERE
            user_id = ?

            AND item_id = ?
        """,
        (
            session["user_id"],
            item_id
        )
    )

    connection.commit()
    connection.close()

    return redirect(
        redirect_to
        or url_for("favorites")
    )


# ============================================================
# FAVORITES
# ============================================================

@app.route("/favorites")
def favorites():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *

        FROM favorites

        WHERE user_id = ?

        ORDER BY created_at DESC
        """,
        (
            session["user_id"],
        )
    )

    favorite_items = cursor.fetchall()

    connection.close()

    return render_template(
        "favorites.html",

        favorite_items=favorite_items
    )


# ============================================================
# FAVORITE TOGGLE API
# ============================================================

@app.route(
    "/api/favorite/toggle",
    methods=["POST"]
)
def favorite_toggle():

    if not login_required():

        return {
            "success": False,
            "error": "Non autenticato"
        }, 401

    data = request.get_json(
        silent=True
    ) or {}

    item_id = str(
        data.get(
            "item_id",
            ""
        )
    ).strip()

    item_name = str(
        data.get(
            "item_name",
            ""
        )
    ).strip()

    image_url = str(
        data.get(
            "image_url",
            ""
        )
    ).strip()

    item_data = data.get(
        "item",
        {}
    )

    if not item_id:

        return {
            "success": False,
            "error": "item_id mancante"
        }, 400

    try:

        data_json = json.dumps(
            item_data,
            ensure_ascii=False
        )

    except Exception:

        data_json = "{}"

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id

        FROM favorites

        WHERE
            user_id = ?

            AND item_id = ?

        LIMIT 1
        """,
        (
            session["user_id"],
            item_id
        )
    )

    existing = cursor.fetchone()

    if existing:

        cursor.execute(
            """
            DELETE FROM favorites

            WHERE
                user_id = ?

                AND item_id = ?
            """,
            (
                session["user_id"],
                item_id
            )
        )

        is_favorite = False

    else:

        cursor.execute(
            """
            INSERT INTO favorites
            (
                user_id,
                item_id,
                item_name,
                image_url,
                data_json
            )

            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(
                user_id,
                item_id
            )

            DO UPDATE SET

                item_name =
                    excluded.item_name,

                image_url =
                    excluded.image_url,

                data_json =
                    excluded.data_json
            """,
            (
                session["user_id"],
                item_id,
                item_name,
                image_url,
                data_json
            )
        )

        is_favorite = True

    connection.commit()
    connection.close()

    return {
        "success": True,
        "is_favorite": is_favorite
    }


# ============================================================
# SHOP HISTORY
# ============================================================

@app.route("/shop-history")
def shop_history():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            shop_date,
            COUNT(*) AS item_count

        FROM shop_history

        GROUP BY shop_date

        ORDER BY shop_date DESC
        """
    )

    history = cursor.fetchall()

    connection.close()

    return render_template(
        "shop_history.html",

        history=history
    )


# ============================================================
# SHOP HISTORY DATE
# ============================================================

@app.route(
    "/shop-history/<path:shop_date>"
)
def shop_history_date(
    shop_date
):

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *

        FROM shop_history

        WHERE shop_date = ?

        ORDER BY item_name COLLATE NOCASE
        """,
        (
            shop_date,
        )
    )

    items = cursor.fetchall()

    connection.close()

    return render_template(
        "shop_history_date.html",

        items=items,

        shop_date=shop_date
    )


# ============================================================
# TRACKER
# ============================================================

@app.route("/tracker")
def tracker():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            item_id,
            item_name,
            image_url,
            created_at

        FROM favorites

        WHERE user_id = ?

        ORDER BY created_at DESC
        """,
        (
            session["user_id"],
        )
    )

    tracked_items = cursor.fetchall()

    cursor.execute(
        """
        SELECT enabled

        FROM notification_settings

        WHERE user_id = ?

        LIMIT 1
        """,
        (
            session["user_id"],
        )
    )

    settings = cursor.fetchone()

    connection.close()

    notifications_enabled = True

    if settings:

        notifications_enabled = bool(
            settings["enabled"]
        )

    return render_template(
        "tracker.html",

        tracked_items=tracked_items,

        notifications_enabled=(
            notifications_enabled
        )
    )


# ============================================================
# TRACKER NOTIFICATION SETTINGS
# ============================================================

@app.route(
    "/tracker/notifications",
    methods=["POST"]
)
def tracker_notifications():

    if not login_required():

        return redirect(
            url_for("login")
        )

    enabled = request.form.get(
        "enabled"
    )

    enabled_value = (
        1
        if enabled == "1"
        else 0
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO notification_settings
        (
            user_id,
            enabled,
            updated_at
        )

        VALUES (?, ?, CURRENT_TIMESTAMP)

        ON CONFLICT(user_id)

        DO UPDATE SET

            enabled =
                excluded.enabled,

            updated_at =
                CURRENT_TIMESTAMP
        """,
        (
            session["user_id"],
            enabled_value
        )
    )

    connection.commit()
    connection.close()

    return redirect(
        url_for("tracker")
    )


# ============================================================
# AUTOMATIC TRACKER CHECK
# ============================================================

@app.route(
    "/api/tracker/check",
    methods=["GET"]
)
def api_tracker_check():

    cron_secret = os.getenv(
        "CRON_SECRET"
    )

    request_secret = request.args.get(
        "secret"
    )

    if not cron_secret:

        return {
            "success": False,
            "error":
                "CRON_SECRET non configurata"
        }, 500

    if request_secret != cron_secret:

        return {
            "success": False,
            "error": "Unauthorized"
        }, 401

    try:

        result = run_tracker_check()

        return result, 200

    except Exception as error:

        print(
            "❌ Errore Tracker:",
            error
        )

        return {
            "success": False,
            "error": str(error)
        }, 500


# ============================================================
# ERROR HANDLER
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return (
        render_template(
            "index.html"
        ),
        404
    )


# ============================================================
# START APP
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
