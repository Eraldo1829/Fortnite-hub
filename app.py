import os

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

from services.fortnite_api import (
    get_shop,
    prepare_shop,
    group_shop_items
)


# =========================
# FLASK
# =========================

app = Flask(__name__)


# =========================
# SECRET KEY
# =========================

app.secret_key = os.getenv(
    "SECRET_KEY",
    "fortnite-hub-development-key"
)


# =========================
# DATABASE
# =========================

create_database()


# =========================
# HOME
# =========================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================
# REGISTER
# =========================

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


        # =========================
        # CONTROLLO CAMPI
        # =========================

        if not username or not email or not password:

            return render_template(
                "register.html",
                error="Compila tutti i campi."
            )


        # =========================
        # CONTROLLO USERNAME
        # =========================

        if len(username) < 3:

            return render_template(
                "register.html",
                error="Lo username deve avere almeno 3 caratteri."
            )


        # =========================
        # CONTROLLO PASSWORD
        # =========================

        if len(password) < 6:

            return render_template(
                "register.html",
                error="La password deve avere almeno 6 caratteri."
            )


        # =========================
        # DATABASE
        # =========================

        connection = get_connection()

        cursor = connection.cursor()


        # =========================
        # CONTROLLO UTENTE ESISTENTE
        # =========================

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

        existing_user = cursor.fetchone()


        if existing_user:

            connection.close()

            return render_template(
                "register.html",
                error="Username o email già utilizzati."
            )


        # =========================
        # PASSWORD HASH
        # =========================

        password_hash = generate_password_hash(
            password
        )


        # =========================
        # CREAZIONE UTENTE
        # =========================

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


        # =========================
        # EMAIL DI BENVENUTO
        # =========================

        send_welcome_email(
            email,
            username
        )


        # =========================
        # DOPO REGISTRAZIONE
        # =========================

        return redirect(
            url_for("login")
        )


    return render_template(
        "register.html"
    )


# =========================
# LOGIN
# =========================

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


        # =========================
        # DATABASE
        # =========================

        connection = get_connection()

        cursor = connection.cursor()


        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        )


        user = cursor.fetchone()

        connection.close()


        # =========================
        # CONTROLLO LOGIN
        # =========================

        if user:

            if check_password_hash(
                user["password_hash"],
                password
            ):

                session["user_id"] = user["id"]

                session["username"] = user["username"]

                return redirect(
                    url_for("home")
                )


        # =========================
        # LOGIN FALLITO
        # =========================

        return render_template(
            "login.html",
            error="Email o password non corretti."
        )


    return render_template(
        "login.html"
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================
# SKINS
# =========================

@app.route("/skins")
def skins():

    shop = get_shop()

    shop_items = prepare_shop(
        shop
    )

    shop_groups = group_shop_items(
        shop_items
    )

    shop_date = None


    if shop and shop.get("data"):

        shop_date = shop[
            "data"
        ].get("date")


    return render_template(
        "skins.html",

        shop_items=shop_items,

        shop_groups=shop_groups,

        shop_date=shop_date
    )


# =========================
# SKIN DETAIL
# =========================

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
        or item_index >= len(shop_items)
    ):

        return render_template(
            "skin_detail.html",
            item=None
        ), 404


    item = shop_items[
        item_index
    ]


    return render_template(
        "skin_detail.html",
        item=item
    )


# =========================
# START SERVER
# =========================

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
