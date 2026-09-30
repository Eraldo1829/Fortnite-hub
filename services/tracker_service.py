import os
from datetime import datetime

from database.database import get_connection
from services.email_service import (
    send_skin_shop_notification
)
from services.fortnite_api import (
    get_shop,
    prepare_shop
)


# ============================================================
# HELPERS
# ============================================================

def get_item_id(item, fallback_index=None):

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

    data = shop.get("data")

    if isinstance(data, dict):

        shop_date = data.get("date")

        if shop_date:
            return str(shop_date)

    shop_date = shop.get("date")

    if shop_date:
        return str(shop_date)

    return datetime.utcnow().strftime(
        "%Y-%m-%d"
    )


# ============================================================
# CONTROLLO TRACKER
# ============================================================

def run_tracker_check():

    print("")
    print("=" * 60)
    print("🔔 FORTNITE HUB - TRACKER CHECK")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. Recupera lo Shop
    # --------------------------------------------------------

    try:

        shop = get_shop()

    except Exception as error:

        print(
            "❌ Errore recupero Shop:",
            error
        )

        return {
            "success": False,
            "message": "Errore recupero Shop",
            "sent": 0,
            "skipped": 0
        }

    if not shop:

        print(
            "❌ Shop vuoto o non disponibile."
        )

        return {
            "success": False,
            "message": "Shop non disponibile",
            "sent": 0,
            "skipped": 0
        }

    # --------------------------------------------------------
    # 2. Prepara gli item
    # --------------------------------------------------------

    try:

        shop_items = prepare_shop(shop)

    except Exception as error:

        print(
            "❌ Errore preparazione Shop:",
            error
        )

        return {
            "success": False,
            "message": "Errore preparazione Shop",
            "sent": 0,
            "skipped": 0
        }

    if not shop_items:

        print(
            "⚠️ Nessun item trovato nello Shop."
        )

        return {
            "success": False,
            "message": "Nessun item nello Shop",
            "sent": 0,
            "skipped": 0
        }

    # --------------------------------------------------------
    # 3. Data Shop
    # --------------------------------------------------------

    shop_date = get_shop_date(shop)

    print(
        f"📅 Data Shop: {shop_date}"
    )

    print(
        f"🛒 Item nello Shop: {len(shop_items)}"
    )

    # --------------------------------------------------------
    # 4. Crea mappa item dello Shop
    # --------------------------------------------------------

    shop_map = {}

    for index, item in enumerate(shop_items):

        item_id = get_item_id(
            item,
            index
        )

        if not item_id:
            continue

        shop_map[item_id] = item

    print(
        f"🔎 Item identificabili: {len(shop_map)}"
    )

    # --------------------------------------------------------
    # 5. Recupera utenti + preferiti
    # --------------------------------------------------------

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            u.id AS user_id,
            u.username AS username,
            u.email AS email,

            f.item_id AS item_id,
            f.item_name AS favorite_name,
            f.image_url AS favorite_image

        FROM favorites f

        INNER JOIN users u
            ON u.id = f.user_id

        LEFT JOIN notification_settings ns
            ON ns.user_id = u.id

        WHERE
            COALESCE(ns.enabled, 1) = 1

        ORDER BY
            u.id ASC
        """
    )

    tracked_items = cursor.fetchall()

    print(
        f"👤 Skin monitorate attive: {len(tracked_items)}"
    )

    sent_count = 0
    skipped_count = 0

    # --------------------------------------------------------
    # 6. Controlla ogni preferito
    # --------------------------------------------------------

    for tracked in tracked_items:

        user_id = tracked["user_id"]

        username = tracked["username"]

        email = tracked["email"]

        item_id = str(
            tracked["item_id"]
        )

        favorite_name = (
            tracked["favorite_name"]
        )

        favorite_image = (
            tracked["favorite_image"]
        )

        # ----------------------------------------------------
        # La skin è nello Shop?
        # ----------------------------------------------------

        shop_item = shop_map.get(
            item_id
        )

        if not shop_item:

            continue

        skin_name = get_item_name(
            shop_item
        )

        skin_image = get_item_image(
            shop_item
        )

        if not skin_name:

            skin_name = favorite_name

        if not skin_image:

            skin_image = favorite_image

        print("")
        print(
            f"🎯 Trovata skin monitorata: "
            f"{skin_name}"
        )

        print(
            f"   👤 Utente: {username}"
        )

        print(
            f"   ✉️ Email: {email}"
        )

        print(
            f"   🆔 Item ID: {item_id}"
        )

        # ----------------------------------------------------
        # Controlla se abbiamo già notificato oggi
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id

            FROM notification_log

            WHERE
                user_id = ?

                AND item_id = ?

                AND shop_date = ?

            LIMIT 1
            """,
            (
                user_id,
                item_id,
                shop_date
            )
        )

        already_notified = (
            cursor.fetchone()
        )

        if already_notified:

            print(
                "   ⏭️ Notifica già inviata oggi."
            )

            skipped_count += 1

            continue

        # ----------------------------------------------------
        # Invia email
        # ----------------------------------------------------

        email_sent = send_skin_shop_notification(
            email=email,
            username=username,
            skin_name=skin_name,
            skin_image=skin_image,
            shop_date=shop_date
        )

        if not email_sent:

            print(
                "   ❌ Invio email fallito."
            )

            continue

        # ----------------------------------------------------
        # Salva nel notification_log
        # ----------------------------------------------------

        try:

            cursor.execute(
                """
                INSERT INTO notification_log
                (
                    user_id,
                    item_id,
                    shop_date,
                    item_name
                )

                VALUES (?, ?, ?, ?)

                ON CONFLICT(
                    user_id,
                    item_id,
                    shop_date
                )

                DO NOTHING
                """,
                (
                    user_id,
                    item_id,
                    shop_date,
                    skin_name
                )
            )

            connection.commit()

            print(
                "   ✅ Notifica registrata."
            )

            sent_count += 1

        except Exception as error:

            connection.rollback()

            print(
                "   ❌ Errore salvataggio log:",
                error
            )

    # --------------------------------------------------------
    # 7. Chiudi database
    # --------------------------------------------------------

    connection.close()

    # --------------------------------------------------------
    # 8. Risultato
    # --------------------------------------------------------

    print("")
    print("=" * 60)

    print(
        f"✅ Controllo completato."
    )

    print(
        f"📧 Email inviate: {sent_count}"
    )

    print(
        f"⏭️ Già notificate: {skipped_count}"
    )

    print("=" * 60)
    print("")

    return {
        "success": True,
        "message": "Controllo completato",
        "sent": sent_count,
        "skipped": skipped_count,
        "shop_date": shop_date,
        "shop_items": len(shop_items)
    }
