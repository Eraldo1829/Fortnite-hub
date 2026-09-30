import os
import json
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    abort,
)

from werkzeug.security import generate_password_hash, check_password_hash

from services.fortnite_api import (
    get_shop,
    prepare_shop,
    get_all_cosmetics,
    get_current_shop_prices,
    get_cosmetic_category,
)


# ============================================================
# APP
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "fortnite-hub-dev-secret-key")

DATABASE = os.getenv("DATABASE_PATH", "fortnite_hub.db")


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            item_name TEXT,
            image_url TEXT,
            data_json TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, item_id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS shop_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_date TEXT NOT NULL,
            item_id TEXT NOT NULL,
            item_name TEXT,
            image_url TEXT,
            price INTEGER,
            bundle INTEGER DEFAULT 0,
            data_json TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(shop_date, item_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_id TEXT,
            sent_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            telegram_enabled INTEGER DEFAULT 0,
            telegram_chat_id TEXT,
            email_enabled INTEGER DEFAULT 0,
            email_address TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    conn.commit()
    conn.close()


# ============================================================
# HELPERS
# ============================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def login_required():
    return "user_id" in session


def get_item_id(item, fallback=None):
    if not isinstance(item, dict):
        return fallback

    possible_keys = [
        "id",
        "item_id",
        "itemId",
        "_item_id",
    ]

    for key in possible_keys:
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value)

    return fallback


def get_item_name(item):
    if not isinstance(item, dict):
        return "Unknown Item"

    possible_keys = [
        "name",
        "displayName",
        "item_name",
        "_item_name",
    ]

    for key in possible_keys:
        value = item.get(key)
        if value:
            return str(value)

    return "Unknown Item"


def get_item_image(item):
    if not isinstance(item, dict):
        return ""

    possible_keys = [
        "image",
        "image_url",
        "icon",
        "_image_url",
    ]

    for key in possible_keys:
        value = item.get(key)
        if value:
            return str(value)

    images = item.get("images")

    if isinstance(images, dict):
        for key in ["icon", "featured", "smallIcon", "large"]:
            value = images.get(key)
            if value:
                return str(value)

    return ""


def get_shop_date():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_favorite_ids(user_id):
    if not user_id:
        return set()

    conn = get_db()

    rows = conn.execute(
        """
        SELECT item_id
        FROM favorites
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchall()

    conn.close()

    return {
        str(row["item_id"])
        for row in rows
        if row["item_id"] is not None
    }


# ============================================================
# TEMPLATE ITEM DECORATION
# ============================================================

def decorate_item_for_template(
    item,
    item_id=None,
    favorite_ids=None,
    shop_index=None,
):
    """
    Aggiunge ai dati dell'item le variabili utilizzate
    dai template:

        _item_id
        _item_name
        _image_url
        _is_favorite
        _shop_index

    Non elimina né modifica i dati originali come:
        bundle
        bundle_items
        price
        type
        series
        set
    """

    if not isinstance(item, dict):
        return item

    if favorite_ids is None:
        favorite_ids = set()

    if item_id is None:
        item_id = get_item_id(item, shop_index)

    item_name = get_item_name(item)
    image_url = get_item_image(item)

    item["_item_id"] = (
        str(item_id)
        if item_id is not None
        else None
    )

    item["_item_name"] = item_name

    item["_image_url"] = image_url

    if shop_index is not None:
        item["_shop_index"] = shop_index

    item["_is_favorite"] = (
        str(item_id) in favorite_ids
        if item_id is not None
        else False
    )

    # Compatibilità con eventuali template che usano
    # is_favorite senza underscore.
    item["is_favorite"] = item["_is_favorite"]

    return item


def prepare_shop_template_items(shop_items, favorite_ids):
    """
    Prepara gli item dello Shop per i template.

    Importante:
    l'indice viene mantenuto quello originale dello Shop.
    """

    prepared = []

    for index, item in enumerate(shop_items):

        if not isinstance(item, dict):
            continue

        item_id = get_item_id(item, index)

        decorate_item_for_template(
            item,
            item_id=item_id,
            favorite_ids=favorite_ids,
            shop_index=index,
        )

        prepared.append(item)

    return prepared


# ============================================================
# SHOP HISTORY
# ============================================================

def save_shop_history(shop_items):
    if not shop_items:
        return

    shop_date = get_shop_date()

    conn = get_db()
    cursor = conn.cursor()

    for index, item in enumerate(shop_items):

        if not isinstance(item, dict):
            continue

        item_id = get_item_id(item, index)

        if item_id is None:
            continue

        item_name = get_item_name(item)
        image_url = get_item_image(item)

        price = item.get("price")

        try:
            price = int(price) if price is not None else None
        except (ValueError, TypeError):
            price = None

        bundle = 1 if item.get("bundle") else 0

        try:
            data_json = json.dumps(
                item,
                ensure_ascii=False,
            )
        except Exception:
            data_json = "{}"

        cursor.execute(
            """
            INSERT INTO shop_history (
                shop_date,
                item_id,
                item_name,
                image_url,
                price,
                bundle,
                data_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(shop_date, item_id)
            DO UPDATE SET
                item_name = excluded.item_name,
                image_url = excluded.image_url,
                price = excluded.price,
                bundle = excluded.bundle,
                data_json = excluded.data_json
            """,
            (
                shop_date,
                str(item_id),
                item_name,
                image_url,
                price,
                bundle,
                data_json,
                now_iso(),
            ),
        )

    conn.commit()
    conn.close()


def get_item_history_stats(item_id):
    if not item_id:
        return {
            "appearances": 0,
            "first_date": None,
            "last_date": None,
            "days_since": None,
        }

    conn = get_db()

    rows = conn.execute(
        """
        SELECT shop_date
        FROM shop_history
        WHERE item_id = ?
        ORDER BY shop_date ASC
        """,
        (str(item_id),),
    ).fetchall()

    conn.close()

    dates = [
        row["shop_date"]
        for row in rows
        if row["shop_date"]
    ]

    if not dates:
        return {
            "appearances": 0,
            "first_date": None,
            "last_date": None,
            "days_since": None,
        }

    first_date = dates[0]
    last_date = dates[-1]

    days_since = None

    try:
        last_dt = datetime.strptime(
            last_date,
            "%Y-%m-%d",
        ).date()

        today = datetime.now(timezone.utc).date()

        days_since = (
            today - last_dt
        ).days

    except Exception:
        days_since = None

    return {
        "appearances": len(dates),
        "first_date": first_date,
        "last_date": last_date,
        "days_since": days_since,
    }


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    shop = get_shop()

    shop_items = []

    if shop:
        shop_items = prepare_shop(shop)

    return render_template(
        "index.html",
        shop=shop,
        shop_items=shop_items,
    )


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = (
            request.form.get("username", "")
            .strip()
        )

        password = request.form.get(
            "password",
            "",
        )

        if not username or not password:
            return render_template(
                "register.html",
                error="Username e password sono obbligatori.",
            )

        password_hash = generate_password_hash(
            password
        )

        conn = get_db()

        try:

            conn.execute(
                """
                INSERT INTO users (
                    username,
                    password_hash,
                    created_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    username,
                    password_hash,
                    now_iso(),
                ),
            )

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            return render_template(
                "register.html",
                error="Username già esistente.",
            )

        conn.close()

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = (
            request.form.get("username", "")
            .strip()
        )

        password = request.form.get(
            "password",
            "",
        )

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

        conn.close()

        if (
            user
            and check_password_hash(
                user["password_hash"],
                password,
            )
        ):

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(
                url_for("index")
            )

        return render_template(
            "login.html",
            error="Username o password non corretti.",
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
        url_for("index")
    )


# ============================================================
# SHOP / SKINS
# ============================================================

@app.route("/skins")
def skins():

    shop = get_shop()

    if not shop:

        return render_template(
            "skins.html",
            shop_groups=[],
            items=[],
            groups=[],
            search_query="",
            favorite_ids=set(),
            shop_date=None,
        )

    shop_items = prepare_shop(shop)

    # Salviamo lo storico prima di aggiungere
    # i campi interni dei template.
    save_shop_history(shop_items)

    user_id = session.get("user_id")

    favorite_ids = get_favorite_ids(
        user_id
    )

    # IMPORTANTE:
    # Decoriamo gli item PRIMA del filtro di ricerca.
    # Così _shop_index rimane l'indice reale dello Shop.
    shop_items = prepare_shop_template_items(
        shop_items,
        favorite_ids,
    )

    search_query = (
        request.args.get(
            "q",
            "",
        )
        .strip()
    )

    if search_query:

        search_lower = search_query.lower()

        shop_items = [
            item
            for item in shop_items
            if search_lower
            in get_item_name(item).lower()
        ]

    shop_groups = []

    try:
        from services.fortnite_api import group_shop_items

        shop_groups = group_shop_items(
            shop_items
        )

    except Exception:

        shop_groups = [
            {
                "name": "Shop",
                "category": "shop",
                "shop_items": shop_items,
            }
        ]

    return render_template(
        "skins.html",
        shop_groups=shop_groups,
        items=shop_items,
        groups=shop_groups,
        search_query=search_query,
        favorite_ids=favorite_ids,
        shop_date=get_shop_date(),
    )


# ============================================================
# SKIN DETAIL
# ============================================================

@app.route("/skins/<int:item_index>")
def skin_detail(item_index):

    shop = get_shop()

    if not shop:
        return redirect(
            url_for("skins")
        )

    shop_items = prepare_shop(shop)

    if (
        item_index < 0
        or item_index >= len(shop_items)
    ):
        return redirect(
            url_for("skins")
        )

    item = shop_items[item_index]

    if not isinstance(item, dict):
        return redirect(
            url_for("skins")
        )

    item_id = get_item_id(
        item,
        item_index,
    )

    user_id = session.get("user_id")

    favorite_ids = get_favorite_ids(
        user_id
    )

    # ========================================================
    # FIX PRINCIPALE
    # ========================================================
    #
    # skin_detail.html utilizza:
    #
    # item._item_id
    # item._item_name
    # item._image_url
    # item._is_favorite
    #
    # Prima questi campi mancavano e Jinja produceva
    # Undefined -> errore tojson.
    #
    decorate_item_for_template(
        item,
        item_id=item_id,
        favorite_ids=favorite_ids,
        shop_index=item_index,
    )

    is_favorite = bool(
        item.get("_is_favorite")
    )

    history = get_item_history_stats(
        item_id
    )

    return render_template(
        "skin_detail.html",

        # Item completo, compresi:
        # bundle
        # bundle_items
        # price
        # image
        # type
        # ecc.
        item=item,

        item_id=item_id,

        # Compatibilità con entrambi i nomi.
        history=history,
        history_stats=history,

        is_favorite=is_favorite,

        from_shop=True,
    )


# ============================================================
# ALL ITEMS
# ============================================================

@app.route("/all-items")
def all_items():

    cosmetics = get_all_cosmetics()

    if not cosmetics:
        return render_template(
            "all_items.html",
            cosmetics=[],
            items=[],
            categories=[],
            selected_category="",
            search_query="",
            page=1,
            total_pages=1,
            total_results=0,
            total_items=0,
            has_next=False,
            favorite_ids=set(),
        )

    search_query = (
        request.args.get(
            "q",
            "",
        )
        .strip()
    )

    selected_category = (
        request.args.get(
            "category",
            "",
        )
        .strip()
    )

    try:
        page = int(
            request.args.get(
                "page",
                1,
            )
        )
    except (TypeError, ValueError):
        page = 1

    if page < 1:
        page = 1

    # ========================================================
    # CATEGORIES
    # ========================================================

    categories = set()

    for item in cosmetics:

        if not isinstance(item, dict):
            continue

        category = get_cosmetic_category(
            item
        )

        if category:
            categories.add(
                category
            )

    categories = sorted(
        categories,
        key=lambda x: str(x).lower(),
    )

    # ========================================================
    # FILTER
    # ========================================================

    filtered = []

    search_lower = search_query.lower()

    for item in cosmetics:

        if not isinstance(item, dict):
            continue

        item_name = get_item_name(
            item
        )

        category = get_cosmetic_category(
            item
        )

        if search_lower:

            if search_lower not in item_name.lower():
                continue

        if selected_category:

            if category != selected_category:
                continue

        filtered.append(item)

    total_results = len(filtered)

    # ========================================================
    # PAGINATION
    # ========================================================

    per_page = 48

    total_pages = max(
        1,
        (
            total_results
            + per_page
            - 1
        )
        // per_page,
    )

    if page > total_pages:
        page = total_pages

    start = (
        page - 1
    ) * per_page

    end = start + per_page

    page_items = filtered[
        start:end
    ]

    # ========================================================
    # PRICES
    # ========================================================

    try:
        shop_prices = get_current_shop_prices()
    except Exception:
        shop_prices = {}

    user_id = session.get(
        "user_id"
    )

    favorite_ids = get_favorite_ids(
        user_id
    )

    prepared_cosmetics = []

    for index, item in enumerate(
        page_items
    ):

        if not isinstance(item, dict):
            continue

        item_id = get_item_id(
            item,
            start + index,
        )

        decorate_item_for_template(
            item,
            item_id=item_id,
            favorite_ids=favorite_ids,
            shop_index=start + index,
        )

        category = get_cosmetic_category(
            item
        )

        item["_category"] = category

        price_data = shop_prices.get(
            str(item_id)
        )

        if isinstance(
            price_data,
            dict,
        ):

            item["_shop_price"] = (
                price_data.get("price")
            )

            item["_shop_bundle"] = bool(
                price_data.get("bundle")
            )

        else:

            item["_shop_price"] = None
            item["_shop_bundle"] = False

        prepared_cosmetics.append(
            item
        )

    has_next = page < total_pages

    return render_template(
        "all_items.html",
        cosmetics=prepared_cosmetics,
        items=prepared_cosmetics,
        selected_category=selected_category,
        categories=categories,
        search_query=search_query,
        page=page,
        total_pages=total_pages,
        total_results=total_results,
        total_items=len(cosmetics),
        has_next=has_next,
        favorite_ids=favorite_ids,
    )


# ============================================================
# ALL ITEM DETAIL
# ============================================================

@app.route("/all-items/<path:item_id>")
def all_item_detail(item_id):

    cosmetics = get_all_cosmetics()

    item = None

    for cosmetic in cosmetics:

        if not isinstance(cosmetic, dict):
            continue

        current_id = get_item_id(
            cosmetic
        )

        if (
            current_id is not None
            and str(current_id)
            == str(item_id)
        ):
            item = cosmetic
            break

    if item is None:
        abort(404)

    user_id = session.get(
        "user_id"
    )

    favorite_ids = get_favorite_ids(
        user_id
    )

    decorate_item_for_template(
        item,
        item_id=item_id,
        favorite_ids=favorite_ids,
    )

    is_favorite = bool(
        item.get("_is_favorite")
    )

    # ========================================================
    # CURRENT SHOP PRICE
    # ========================================================

    try:
        prices = get_current_shop_prices()
        current_price = prices.get(
            str(item_id)
        )
    except Exception:
        current_price = None

    if isinstance(
        current_price,
        dict,
    ):

        item["_shop_price"] = (
            current_price.get("price")
        )

        item["_shop_bundle"] = bool(
            current_price.get("bundle")
        )

    else:

        item["_shop_price"] = None
        item["_shop_bundle"] = False

    history = get_item_history_stats(
        item_id
    )

    return render_template(
        "all_item_detail.html",
        item=item,
        item_id=item_id,
        history=history,
        history_stats=history,
        current_price=current_price,
        is_favorite=is_favorite,
    )


# ============================================================
# FAVORITE DETAIL
# ============================================================

@app.route("/favorites/<path:item_id>")
def favorite_detail(item_id):

    if not login_required():

        return redirect(
            url_for(
                "login",
                next=request.path,
            )
        )

    user_id = session["user_id"]

    conn = get_db()

    favorite = conn.execute(
        """
        SELECT *
        FROM favorites
        WHERE user_id = ?
        AND item_id = ?
        """,
        (
            user_id,
            str(item_id),
        ),
    ).fetchone()

    conn.close()

    if favorite is None:
        return redirect(
            url_for("favorites")
        )

    item_data = None

    if favorite["data_json"]:

        try:
            item_data = json.loads(
                favorite["data_json"]
            )
        except Exception:
            item_data = None

    if not isinstance(
        item_data,
        dict,
    ):

        item_data = {
            "id": str(item_id),
            "name": favorite["item_name"]
            or "Unknown Item",
            "image": favorite["image_url"]
            or "",
        }

    # Assicuriamoci che i dati principali esistano.
    if not item_data.get("id"):
        item_data["id"] = str(item_id)

    if not item_data.get("name"):
        item_data["name"] = (
            favorite["item_name"]
            or "Unknown Item"
        )

    if not item_data.get("image"):
        item_data["image"] = (
            favorite["image_url"]
            or ""
        )

    decorate_item_for_template(
        item_data,
        item_id=item_id,
        favorite_ids={str(item_id)},
    )

    history = get_item_history_stats(
        item_id
    )

    return render_template(
        "skin_detail.html",
        item=item_data,
        item_id=item_id,
        history=history,
        history_stats=history,
        is_favorite=True,
        from_shop=False,
    )


# ============================================================
# ADD FAVORITE
# ============================================================

@app.route(
    "/favorites/add",
    methods=["POST"],
)
def add_favorite():

    if not login_required():

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    item_id = str(
        request.form.get(
            "item_id",
            "",
        )
    ).strip()

    item_name = (
        request.form.get(
            "item_name",
            "",
        )
        .strip()
    )

    image_url = (
        request.form.get(
            "image_url",
            "",
        )
        .strip()
    )

    if not item_id:

        return redirect(
            request.referrer
            or url_for("skins")
        )

    conn = get_db()

    conn.execute(
        """
        INSERT OR IGNORE INTO favorites (
            user_id,
            item_id,
            item_name,
            image_url,
            data_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            item_id,
            item_name,
            image_url,
            "{}",
            now_iso(),
        ),
    )

    conn.commit()
    conn.close()

    return redirect(
        request.referrer
        or url_for("skins")
    )


# ============================================================
# REMOVE FAVORITE
# ============================================================

@app.route(
    "/favorites/remove",
    methods=["POST"],
)
def remove_favorite():

    if not login_required():

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    item_id = str(
        request.form.get(
            "item_id",
            "",
        )
    ).strip()

    conn = get_db()

    conn.execute(
        """
        DELETE FROM favorites
        WHERE user_id = ?
        AND item_id = ?
        """,
        (
            user_id,
            item_id,
        ),
    )

    conn.commit()
    conn.close()

    return redirect(
        request.referrer
        or url_for("favorites")
    )


# ============================================================
# FAVORITES
# ============================================================

@app.route("/favorites")
def favorites():

    if not login_required():

        return redirect(
            url_for(
                "login",
                next=request.path,
            )
        )

    user_id = session["user_id"]

    conn = get_db()

    rows = conn.execute(
        """
        SELECT *
        FROM favorites
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    ).fetchall()

    conn.close()

    favorite_items = []

    for row in rows:

        item = None

        if row["data_json"]:

            try:
                item = json.loads(
                    row["data_json"]
                )
            except Exception:
                item = None

        if not isinstance(
            item,
            dict,
        ):

            item = {
                "id": str(row["item_id"]),
                "name": row["item_name"]
                or "Unknown Item",
                "image": row["image_url"]
                or "",
            }

        decorate_item_for_template(
            item,
            item_id=row["item_id"],
            favorite_ids={
                str(row["item_id"])
            },
        )

        favorite_items.append(
            item
        )

    return render_template(
        "favorites.html",
        favorites=favorite_items,
        items=favorite_items,
    )


# ============================================================
# FAVORITE TOGGLE API
# ============================================================

@app.route(
    "/api/favorite/toggle",
    methods=["POST"],
)
def favorite_toggle():

    if not login_required():

        return jsonify(
            {
                "success": False,
                "error": "Login richiesto.",
            }
        ), 401

    data = request.get_json(
        silent=True
    )

    if not isinstance(
        data,
        dict,
    ):
        data = {}

    item_id = str(
        data.get(
            "item_id",
            "",
        )
        or ""
    ).strip()

    item_name = str(
        data.get(
            "item_name",
            "",
        )
        or ""
    ).strip()

    image_url = str(
        data.get(
            "image_url",
            "",
        )
        or ""
    ).strip()

    item_data = data.get(
        "item"
    )

    if not item_id:

        return jsonify(
            {
                "success": False,
                "error": "item_id mancante.",
            }
        ), 400

    if not isinstance(
        item_data,
        dict,
    ):
        item_data = {}

    # Manteniamo sempre questi dati nel JSON.
    item_data.setdefault(
        "id",
        item_id,
    )

    if item_name:
        item_data.setdefault(
            "name",
            item_name,
        )

    if image_url:
        item_data.setdefault(
            "image",
            image_url,
        )

    user_id = session["user_id"]

    conn = get_db()

    existing = conn.execute(
        """
        SELECT id
        FROM favorites
        WHERE user_id = ?
        AND item_id = ?
        """,
        (
            user_id,
            item_id,
        ),
    ).fetchone()

    # ========================================================
    # REMOVE
    # ========================================================

    if existing:

        conn.execute(
            """
            DELETE FROM favorites
            WHERE user_id = ?
            AND item_id = ?
            """,
            (
                user_id,
                item_id,
            ),
        )

        conn.commit()
        conn.close()

        return jsonify(
            {
                "success": True,
                "is_favorite": False,
                "item_id": item_id,
            }
        )

    # ========================================================
    # ADD
    # ========================================================

    try:

        data_json = json.dumps(
            item_data,
            ensure_ascii=False,
        )

    except Exception:

        data_json = "{}"

    conn.execute(
        """
        INSERT INTO favorites (
            user_id,
            item_id,
            item_name,
            image_url,
            data_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            item_id,
            item_name,
            image_url,
            data_json,
            now_iso(),
        ),
    )

    conn.commit()
    conn.close()

    return jsonify(
        {
            "success": True,
            "is_favorite": True,
            "item_id": item_id,
        }
    )


# ============================================================
# SHOP HISTORY
# ============================================================

@app.route("/shop-history")
def shop_history():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            shop_date,
            COUNT(*) AS item_count
        FROM shop_history
        GROUP BY shop_date
        ORDER BY shop_date DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "shop_history.html",
        history=rows,
        shop_history=rows,
    )


# ============================================================
# SHOP HISTORY DETAIL
# ============================================================

@app.route(
    "/shop-history/<path:shop_date>"
)
def shop_history_detail(shop_date):

    conn = get_db()

    rows = conn.execute(
        """
        SELECT *
        FROM shop_history
        WHERE shop_date = ?
        ORDER BY item_name ASC
        """,
        (shop_date,),
    ).fetchall()

    conn.close()

    items = []

    for row in rows:

        item = None

        if row["data_json"]:

            try:
                item = json.loads(
                    row["data_json"]
                )
            except Exception:
                item = None

        if not isinstance(
            item,
            dict,
        ):

            item = {
                "id": row["item_id"],
                "name": row["item_name"],
                "image": row["image_url"],
                "price": row["price"],
                "bundle": bool(
                    row["bundle"]
                ),
            }

        items.append(item)

    return render_template(
        "shop_history_detail.html",
        shop_date=shop_date,
        items=items,
        history_items=items,
    )


# ============================================================
# TRACKER
# ============================================================

@app.route("/tracker")
def tracker():

    return render_template(
        "tracker.html"
    )


# ============================================================
# TRACKER NOTIFICATIONS
# ============================================================

@app.route(
    "/tracker/notifications"
)
def tracker_notifications():

    if not login_required():

        return redirect(
            url_for(
                "login",
                next=request.path,
            )
        )

    user_id = session["user_id"]

    conn = get_db()

    settings = conn.execute(
        """
        SELECT *
        FROM notification_settings
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    conn.close()

    return render_template(
        "tracker_notifications.html",
        settings=settings,
    )


# ============================================================
# TRACKER CHECK API
# ============================================================

@app.route(
    "/api/tracker/check"
)
def tracker_check():

    shop = get_shop()

    if not shop:

        return jsonify(
            {
                "success": False,
                "error": "Shop non disponibile.",
            }
        ), 503

    shop_items = prepare_shop(
        shop
    )

    return jsonify(
        {
            "success": True,
            "count": len(shop_items),
            "shop_date": get_shop_date(),
        }
    )


# ============================================================
# 404
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "404.html"
    ), 404


# ============================================================
# STARTUP
# ============================================================

init_db()


# ============================================================
# LOCAL RUN
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "10000",
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
