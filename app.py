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

from services.notification_service import (
    send_skin_notification
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
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# SECRET KEY
# ============================================================

app.secret_key = os.getenv(
    "SECRET_KEY",
    "fortnite-hub-development-key"
)


# ============================================================
# DATABASE
# ============================================================

create_database()


# ============================================================
# FEATURE DATABASE
# ============================================================

def create_feature_tables():

    connection = get_connection()
    cursor = connection.cursor()

    # ========================================================
    # PREFERITI
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            item_name TEXT,
            image_url TEXT,
            data_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(user_id, item_id)
        )
    """)

    # ========================================================
    # STORICO SHOP
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_date TEXT NOT NULL,
            item_id TEXT NOT NULL,
            item_name TEXT,
            image_url TEXT,
            data_json TEXT,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(shop_date, item_id)
        )
    """)

    connection.commit()
    connection.close()


create_feature_tables()


# ============================================================
# HELPERS
# ============================================================

def login_required():

    return "user_id" in session


# ============================================================
# ITEM ID
# ============================================================

def get_item_id(
    item,
    fallback_index=None
):

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


# ============================================================
# ITEM NAME
# ============================================================

def get_item_name(item):

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


# ============================================================
# ITEM IMAGE
# ============================================================

def get_item_image(item):

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


# ============================================================
# SHOP DATE
# ============================================================

def get_shop_date(shop):

    if not shop:

        return None

    data = shop.get(
        "data"
    )

    if not data:

        return None

    return data.get(
        "date"
    )


# ============================================================
# SAVE SHOP HISTORY
# ============================================================

def save_shop_history(
    shop_date,
    shop_items
):

    if not shop_date or not shop_items:

        return

    connection = get_connection()
    cursor = connection.cursor()

    for index, item in enumerate(
        shop_items
    ):

        item_id = get_item_id(
            item,
            index
        )

        if not item_id:

            continue

        item_name = get_item_name(
            item
        )

        image_url = get_item_image(
            item
        )

        data_json = json.dumps(
            item,
            ensure_ascii=False
        )

        cursor.execute(
            """
            INSERT OR IGNORE INTO shop_history
            (
                shop_date,
                item_id,
                item_name,
                image_url,
                data_json
            )
            VALUES (?, ?, ?, ?, ?)
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


# ============================================================
# GET FAVORITE IDS
# ============================================================

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


# ============================================================
# SHOP HISTORY STATISTICS
# ============================================================

def get_item_history_stats(item_id):

    if not item_id:

        return {
            "last_date": None,
            "first_date": None,
            "days_since": None,
            "appearances": 0
        }

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT shop_date
        FROM shop_history
        WHERE item_id = ?
        ORDER BY shop_date ASC
        """,
        (
            str(item_id),
        )
    )

    rows = cursor.fetchall()

    connection.close()

    if not rows:

        return {
            "last_date": None,
            "first_date": None,
            "days_since": None,
            "appearances": 0
        }

    dates = []

    for row in rows:

        shop_date = row[
            "shop_date"
        ]

        if not shop_date:

            continue

        try:

            parsed_date = datetime.fromisoformat(
                shop_date.replace(
                    "Z",
                    "+00:00"
                )
            ).date()

            dates.append(
                parsed_date
            )

            continue

        except Exception:

            pass

        try:

            parsed_date = date.fromisoformat(
                shop_date[:10]
            )

            dates.append(
                parsed_date
            )

        except Exception:

            continue

    if not dates:

        return {
            "last_date": None,
            "first_date": None,
            "days_since": None,
            "appearances": 0
        }

    first_date = min(
        dates
    )

    last_date = max(
        dates
    )

    today = date.today()

    days_since = (
        today - last_date
    ).days

    if days_since < 0:

        days_since = 0

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

        if (
            not username
            or not email
            or not password
        ):

            return render_template(
                "register.html",
                error="Compila tutti i campi."
            )

        if len(username) < 3:

            return render_template(
                "register.html",
                error=(
                    "Lo username deve avere "
                    "almeno 3 caratteri."
                )
            )

        if len(password) < 6:

            return render_template(
                "register.html",
                error=(
                    "La password deve avere "
                    "almeno 6 caratteri."
                )
            )

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            OR email = ?
            """,
            (
                username,
                email
            )
        )

        existing_user = (
            cursor.fetchone()
        )

        if existing_user:

            connection.close()

            return render_template(
                "register.html",
                error=(
                    "Username o email "
                    "già utilizzati."
                )
            )

        password_hash = (
            generate_password_hash(
                password
            )
        )

        cursor.execute(
            """
            INSERT INTO users
            (
                username,
                email,
                password_hash
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
        connection.close()

        try:

            send_welcome_email(
                email,
                username
            )

        except Exception as error:

            print(
                "Errore email:",
                error
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
            """,
            (
                email,
            )
        )

        user = cursor.fetchone()

        connection.close()

        if user:

            if check_password_hash(
                user["password_hash"],
                password
            ):

                session["user_id"] = (
                    user["id"]
                )

                session["username"] = (
                    user["username"]
                )

                return redirect(
                    url_for("home")
                )

        return render_template(
            "login.html",
            error=(
                "Email o password "
                "non corretti."
            )
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
# SKINS / SHOP
# ============================================================

@app.route("/skins")
def skins():

    shop = get_shop()

    shop_items = prepare_shop(
        shop
    )

    shop_date = get_shop_date(
        shop
    )

    # ========================================================
    # SALVA STORICO
    # ========================================================

    save_shop_history(
        shop_date,
        shop_items
    )

    # ========================================================
    # PREFERITI
    # ========================================================

    favorite_ids = set()

    if login_required():

        favorite_ids = (
            get_favorite_ids(
                session["user_id"]
            )
        )

    # ========================================================
    # PREPARAZIONE ITEM
    # ========================================================

    for index, item in enumerate(
        shop_items
    ):

        item["_shop_index"] = (
            index
        )

        item["_item_id"] = (
            get_item_id(
                item,
                index
            )
        )

        item["_item_name"] = (
            get_item_name(
                item
            )
        )

        item["_image_url"] = (
            get_item_image(
                item
            )
        )

        item["_is_favorite"] = (
            item["_item_id"]
            in favorite_ids
        )

    # ========================================================
    # RICERCA
    # ========================================================

    search_query = request.args.get(
        "q",
        ""
    ).strip()

    if search_query:

        search_lower = (
            search_query.lower()
        )

        shop_items = [
            item
            for item in shop_items
            if search_lower
            in item[
                "_item_name"
            ].lower()
        ]

    # ========================================================
    # GRUPPI
    # ========================================================

    shop_groups = (
        group_shop_items(
            shop_items
        )
    )

    return render_template(
        "skins.html",

        shop_items=shop_items,

        shop_groups=shop_groups,

        shop_date=shop_date,

        favorite_ids=favorite_ids,

        search_query=search_query
    )


# ============================================================
# SHOP ITEM DETAIL
# ============================================================

@app.route(
    "/skins/<int:item_index>"
)
def skin_detail(item_index):

    shop = get_shop()

    shop_items = prepare_shop(
        shop
    )

    if not shop_items:

        return render_template(
            "skin_detail.html",
            item=None
        ), 404

    if (
        item_index < 0
        or
        item_index >= len(
            shop_items
        )
    ):

        return render_template(
            "skin_detail.html",
            item=None
        ), 404

    item = shop_items[
        item_index
    ]

    item["_item_id"] = (
        get_item_id(
            item,
            item_index
        )
    )

    item["_item_name"] = (
        get_item_name(
            item
        )
    )

    item["_image_url"] = (
        get_item_image(
            item
        )
    )

    item["_is_favorite"] = False

    if login_required():

        favorite_ids = (
            get_favorite_ids(
                session["user_id"]
            )
        )

        item["_is_favorite"] = (
            item["_item_id"]
            in favorite_ids
        )

    shop_date = get_shop_date(
        shop
    )

    save_shop_history(
        shop_date,
        shop_items
    )

    history_stats = (
        get_item_history_stats(
            item["_item_id"]
        )
    )

    return render_template(
        "skin_detail.html",

        item=item,

        history_stats=history_stats
    )


# ============================================================
# TUTTI GLI ITEM
# ============================================================

@app.route("/all-items")
def all_items():

    search_query = request.args.get(
        "q",
        ""
    ).strip()

    selected_category = (
        request.args.get(
            "category",
            ""
        ).strip()
    )

    # ========================================================
    # CATEGORIE
    # ========================================================

    categories = [

        "👕 Outfit",

        "🎒 Back Bling",

        "⛏️ Picconi",

        "🪂 Deltaplani",

        "💃 Emote",

        "🎨 Wrap",

        "🖼️ Schermate di caricamento",

        "✨ Scie",

        "🎵 Musica",

        "🎨 Spray",

        "🏳️ Banner",

        "📦 Altri oggetti"
    ]

    # ========================================================
    # COSMETICI
    #
    # Viene utilizzata la ricerca API invece di scaricare
    # l'intero catalogo e mostrarlo tutto contemporaneamente.
    # ========================================================

    cosmetics = search_cosmetics(
        search_query=search_query,
        category=selected_category
    )

    # ========================================================
    # PAGINAZIONE
    # ========================================================

    total_results = len(
        cosmetics
    )

    page = request.args.get(
        "page",
        "1"
    )

    try:

        page = int(
            page
        )

    except ValueError:

        page = 1

    if page < 1:

        page = 1

    per_page = 60

    start = (
        page - 1
    ) * per_page

    end = (
        start + per_page
    )

    visible_cosmetics = cosmetics[
        start:end
    ]

    has_next = (
        end < total_results
    )

    # ========================================================
    # PREZZI SHOP
    # ========================================================

    shop_prices = (
        get_current_shop_prices()
    )

    # ========================================================
    # PREFERITI
    # ========================================================

    favorite_ids = set()

    if login_required():

        favorite_ids = (
            get_favorite_ids(
                session["user_id"]
            )
        )

    # ========================================================
    # PREPARAZIONE
    # ========================================================

    for item in visible_cosmetics:

        item["_item_id"] = (
            get_item_id(
                item
            )
        )

        item["_item_name"] = (
            get_item_name(
                item
            )
        )

        item["_image_url"] = (
            get_item_image(
                item
            )
        )

        item["_is_favorite"] = (
            item["_item_id"]
            in favorite_ids
        )

        if not item.get(
            "_category"
        ):

            item["_category"] = (
                get_cosmetic_category(
                    item
                )
            )

        # ====================================================
        # PREZZO SHOP ATTUALE
        # ====================================================

        item["_shop_price"] = None

        item["_shop_bundle"] = False

        cosmetic_id = str(
            item.get("id")
            or ""
        )

        if cosmetic_id in shop_prices:

            price_data = (
                shop_prices[
                    cosmetic_id
                ]
            )

            item["_shop_price"] = (
                price_data.get(
                    "price"
                )
            )

            item["_shop_bundle"] = (
                price_data.get(
                    "bundle",
                    False
                )
            )

    return render_template(
        "all_items.html",

        cosmetics=visible_cosmetics,

        categories=categories,

        selected_category=selected_category,

        search_query=search_query,

        favorite_ids=favorite_ids,

        page=page,

        total_results=total_results,

        has_next=has_next
    )


# ============================================================
# TUTTI GLI ITEM - DETTAGLIO
# ============================================================

@app.route(
    "/all-items/<path:item_id>"
)
def all_item_detail(item_id):

    # ========================================================
    # CERCA DIRETTAMENTE L'ITEM
    # ========================================================

    cosmetics = search_cosmetics(
        search_query=item_id
    )

    selected_item = None

    for item in cosmetics:

        current_id = str(
            item.get("id", "")
        )

        if current_id == str(
            item_id
        ):

            selected_item = item

            break

    # ========================================================
    # FALLBACK
    # ========================================================

    if selected_item is None:

        return render_template(
            "all_item_detail.html",
            item=None
        ), 404

    # ========================================================
    # DATI ITEM
    # ========================================================

    selected_item["_item_id"] = (
        get_item_id(
            selected_item
        )
    )

    selected_item["_item_name"] = (
        get_item_name(
            selected_item
        )
    )

    selected_item["_image_url"] = (
        get_item_image(
            selected_item
        )
    )

    if not selected_item.get(
        "_category"
    ):

        selected_item["_category"] = (
            get_cosmetic_category(
                selected_item
            )
        )

    # ========================================================
    # PREZZO SHOP
    # ========================================================

    selected_item["_shop_price"] = None

    selected_item["_shop_bundle"] = False

    shop_prices = (
        get_current_shop_prices()
    )

    cosmetic_id = str(
        selected_item.get("id")
        or ""
    )

    if cosmetic_id in shop_prices:

        price_data = (
            shop_prices[
                cosmetic_id
            ]
        )

        selected_item["_shop_price"] = (
            price_data.get(
                "price"
            )
        )

        selected_item["_shop_bundle"] = (
            price_data.get(
                "bundle",
                False
            )
        )

    # ========================================================
    # PREFERITO
    # ========================================================

    selected_item["_is_favorite"] = False

    if login_required():

        favorite_ids = (
            get_favorite_ids(
                session["user_id"]
            )
        )

        selected_item["_is_favorite"] = (
            selected_item["_item_id"]
            in favorite_ids
        )

    return render_template(
        "all_item_detail.html",

        item=selected_item
    )


# ============================================================
# FAVORITE DETAIL
# ============================================================

@app.route(
    "/favorites/<path:item_id>"
)
def favorite_detail(item_id):

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
        AND item_id = ?
        LIMIT 1
        """,
        (
            session["user_id"],
            str(item_id)
        )
    )

    row = cursor.fetchone()

    connection.close()

    if not row:

        return render_template(
            "skin_detail.html",
            item=None,
            history_stats=None
        ), 404

    try:

        item = json.loads(
            row["data_json"]
            or "{}"
        )

    except Exception:

        item = {}

    item["_item_id"] = (
        row["item_id"]
    )

    item["_item_name"] = (
        row["item_name"]
        or
        get_item_name(item)
    )

    item["_image_url"] = (
        row["image_url"]
        or
        get_item_image(item)
    )

    item["_is_favorite"] = True

    if not item.get("name"):

        item["name"] = (
            item["_item_name"]
        )

    if not item.get("image"):

        item["image"] = (
            item["_image_url"]
        )

    try:

        shop = get_shop()

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
            "Errore aggiornamento "
            "storico preferito:",
            error
        )

    history_stats = (
        get_item_history_stats(
            item["_item_id"]
        )
    )

    return render_template(
        "skin_detail.html",

        item=item,

        history_stats=history_stats
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
        "Skin"
    ).strip()

    image_url = request.form.get(
        "image_url",
        ""
    ).strip()

    data_json = request.form.get(
        "data_json",
        "{}"
    )

    if not item_id:

        return redirect(
            request.referrer
            or
            url_for("skins")
        )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO favorites
        (
            user_id,
            item_id,
            item_name,
            image_url,
            data_json
        )
        VALUES (?, ?, ?, ?, ?)
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
        request.referrer
        or
        url_for("skins")
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

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM favorites
        WHERE user_id = ?
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
        request.referrer
        or
        url_for("skins")
    )


# ============================================================
# FAVORITES PAGE
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

    rows = cursor.fetchall()

    connection.close()

    favorite_items = []

    for row in rows:

        try:

            item = json.loads(
                row["data_json"]
                or "{}"
            )

        except Exception:

            item = {}

        item["_item_id"] = (
            row["item_id"]
        )

        item["_item_name"] = (
            row["item_name"]
        )

        item["_image_url"] = (
            row["image_url"]
        )

        item["_is_favorite"] = True

        if not item.get("name"):

            item["name"] = (
                row["item_name"]
            )

        if not item.get("image"):

            item["image"] = (
                row["image_url"]
            )

        favorite_items.append(
            item
        )

    return render_template(
        "favorites.html",

        favorites=favorite_items
    )


# ============================================================
# SHOP HISTORY
# ============================================================

@app.route("/shop-history")
def shop_history():

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

    dates = cursor.fetchall()

    connection.close()

    return render_template(
        "shop_history.html",

        dates=dates
    )


# ============================================================
# SHOP HISTORY DATE
# ============================================================

@app.route(
    "/shop-history/<path:shop_date>"
)
def shop_history_date(shop_date):

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

    rows = cursor.fetchall()

    connection.close()

    history_items = []

    for row in rows:

        try:

            item = json.loads(
                row["data_json"]
                or "{}"
            )

        except Exception:

            item = {}

        item["_item_id"] = (
            row["item_id"]
        )

        item["_item_name"] = (
            row["item_name"]
        )

        item["_image_url"] = (
            row["image_url"]
        )

        history_items.append(
            item
        )

    return render_template(
        "shop_history_date.html",

        shop_date=shop_date,

        history_items=history_items
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
            "message": "Login richiesto."
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
            "Skin"
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
            "message": "ID skin mancante."
        }, 400

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM favorites
        WHERE user_id = ?
        AND item_id = ?
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
            WHERE user_id = ?
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
            """,
            (
                session["user_id"],
                item_id,
                item_name,
                image_url,
                json.dumps(
                    item_data,
                    ensure_ascii=False
                )
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
# START SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                5000
            )
        )
    )
