"""Run against the web application's database, never an Actions-local copy."""
from datetime import datetime, timezone


def check_shop(app_module, send_email=False):
    shop = app_module.get_shop()
    if not shop:
        return {"success": False, "error": "Shop non disponibile."}
    items = app_module.prepare_shop(shop)
    date = ((shop.get("data") or {}).get("date") or datetime.now(timezone.utc).isoformat())[:10]
    app_module.save_shop_history(items, shop_date=date)
    available = {}
    for item in items:
        available[str(item.get("id"))] = item
        for child in item.get("bundle_items") or []:
            if isinstance(child, dict) and child.get("id"):
                available[str(child["id"])] = child
    sent = 0
    if send_email:
        from services.notification_service import send_skin_notification
        conn = app_module.get_db()
        try:
            # One write transaction prevents concurrent checks sending the same alert.
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute("""SELECT f.*, u.username, s.email_address
                FROM favorites f JOIN users u ON u.id=f.user_id
                JOIN notification_settings s ON s.user_id=u.id
                WHERE s.enabled=1 AND s.email_enabled=1""").fetchall()
            for row in rows:
                if row["item_id"] not in available or not row["email_address"]:
                    continue
                exists = conn.execute("SELECT 1 FROM notification_log WHERE user_id=? AND item_id=? AND shop_date=?",
                                      (row["user_id"], row["item_id"], date)).fetchone()
                if exists:
                    continue
                item = available[row["item_id"]]
                if send_skin_notification(row["email_address"], row["username"], item.get("name"), app_module.get_item_image(item)):
                    conn.execute("INSERT INTO notification_log(user_id,item_id,shop_date,sent_at) VALUES(?,?,?,?)",
                                 (row["user_id"], row["item_id"], date, app_module.now_iso()))
                    sent += 1
            conn.commit()
        finally:
            conn.close()
    return {"success": True, "count": len(items), "shop_date": date, "sent": sent}
