import json

from database.database import (
    create_database,
    get_connection
)

from services.fortnite_api import (
    get_shop,
    prepare_shop
)

from services.notification_service import (
    send_skin_notification
)


# ============================================================
# DATABASE
# ============================================================

create_database()


# ============================================================
# HELPERS
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
# NOTIFICATION CHECK
# ============================================================

def check_skin_tracker():

    print(
        "========================================"
    )

    print(
        "🔥 FORTNITE HUB - SKIN TRACKER"
    )

    print(
        "========================================"
    )

    # ========================================================
    # SHOP
    # ========================================================

    print(
        "🛒 Recupero Shop..."
    )

    shop = get_shop()

    if not shop:

        print(
            "❌ Impossibile recuperare lo Shop."
        )

        return False

    shop_date = get_shop_date(
        shop
    )

    if not shop_date:

        print(
            "❌ Data Shop non trovata."
        )

        return False

    print(
        f"📅 Shop: {shop_date}"
    )

    shop_items = prepare_shop(
        shop
    )

    if not shop_items:

        print(
            "❌ Nessun item trovato."
        )

        return False

    print(
        f"📦 Item nello Shop: "
        f"{len(shop_items)}"
    )

    # ========================================================
    # SHOP IDS
    # ========================================================

    shop_items_by_id = {}

    for index, item in enumerate(
        shop_items
    ):

        item_id = get_item_id(
            item,
            index
        )

        if not item_id:

            continue

        shop_items_by_id[
            str(item_id)
        ] = item

    print(
        f"🔎 ID Shop analizzati: "
        f"{len(shop_items_by_id)}"
    )

    # ========================================================
    # DATABASE
    # ========================================================

    connection = get_connection()

    cursor = connection.cursor()

    # ========================================================
    # UTENTI CON NOTIFICHE ATTIVE
    # ========================================================

    cursor.execute("""
        SELECT
            u.id,
            u.username,
            u.email
        FROM users u

        LEFT JOIN notification_settings ns
            ON ns.user_id = u.id

        WHERE
            COALESCE(ns.enabled, 1) = 1
    """)

    users = cursor.fetchall()

    print(
        f"👤 Utenti con notifiche attive: "
        f"{len(users)}"
    )

    # ========================================================
    # CICLO UTENTI
    # ========================================================

    notifications_sent = 0

    for user in users:

        user_id = user["id"]

        username = user["username"]

        email = user["email"]

        # ====================================================
        # PREFERITI
        # ====================================================

        cursor.execute(
            """
            SELECT
                item_id,
                item_name,
                image_url,
                data_json
            FROM favorites
            WHERE user_id = ?
            """,
            (
                user_id,
            )
        )

        favorites = cursor.fetchall()

        if not favorites:

            continue

        print(
            f"👤 {username}: "
            f"{len(favorites)} preferiti"
        )

        # ====================================================
        # CONTROLLA PREFERITI
        # ====================================================

        for favorite in favorites:

            favorite_id = str(
                favorite["item_id"]
            )

            if favorite_id not in shop_items_by_id:

                continue

            shop_item = (
                shop_items_by_id[
                    favorite_id
                ]
            )

            item_name = (
                favorite["item_name"]
                or
                get_item_name(
                    shop_item
                )
            )

            image_url = (
                favorite["image_url"]
                or
                get_item_image(
                    shop_item
                )
            )

            # =================================================
            # GIÀ NOTIFICATO?
            # =================================================

            cursor.execute(
                """
                SELECT id
                FROM notification_log
                WHERE user_id = ?
                AND item_id = ?
                AND shop_date = ?
                LIMIT 1
                """,
                (
                    user_id,
                    favorite_id,
                    shop_date
                )
            )

            already_notified = (
                cursor.fetchone()
            )

            if already_notified:

                print(
                    f"   ↳ ⏭️ Già notificato: "
                    f"{item_name}"
                )

                continue

            # =================================================
            # INVIA EMAIL
            # =================================================

            print(
                f"   ↳ 🔔 Invio notifica: "
                f"{item_name}"
            )

            sent = send_skin_notification(
                recipient=email,
                username=username,
                item_name=item_name,
                image_url=image_url
            )

            if not sent:

                print(
                    f"   ↳ ❌ Invio fallito: "
                    f"{item_name}"
                )

                continue

            # =================================================
            # SALVA LOG
            # =================================================

            cursor.execute(
                """
                INSERT OR IGNORE INTO
                notification_log
                (
                    user_id,
                    item_id,
                    shop_date,
                    item_name
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    favorite_id,
                    shop_date,
                    item_name
                )
            )

            notifications_sent += 1

    # ========================================================
    # COMMIT
    # ========================================================

    connection.commit()

    connection.close()

    # ========================================================
    # RISULTATO
    # ========================================================

    print(
        "========================================"
    )

    print(
        f"📨 Notifiche inviate: "
        f"{notifications_sent}"
    )

    print(
        "✅ Tracker completato."
    )

    print(
        "========================================"
    )

    return True


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    check_skin_tracker()
