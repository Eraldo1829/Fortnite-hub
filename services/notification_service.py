import os
import html

import resend


# ============================================================
# CONFIGURAZIONE RESEND
# ============================================================

RESEND_API_KEY = os.getenv("RESEND_API_KEY")

FROM_EMAIL = "Fortnite Hub <onboarding@resend.dev>"


# ============================================================
# INVIO NOTIFICA SKIN
# ============================================================

def send_skin_notification(
    recipient,
    username,
    item_name,
    image_url=None
):

    # --------------------------------------------------------
    # CONTROLLI
    # --------------------------------------------------------

    if not recipient:
        print("❌ Nessun destinatario.")
        return False

    if not RESEND_API_KEY:
        print("❌ RESEND_API_KEY non configurata.")
        return False

    # --------------------------------------------------------
    # SICUREZZA HTML
    # --------------------------------------------------------

    safe_username = html.escape(
        str(username or "Utente")
    )

    safe_item_name = html.escape(
        str(item_name or "Skin")
    )

    safe_image_url = ""

    if image_url:
        safe_image_url = html.escape(
            str(image_url),
            quote=True
        )

    # --------------------------------------------------------
    # OGGETTO EMAIL
    # --------------------------------------------------------

    subject = (
        f"🔥 {safe_item_name} è tornata nello Shop!"
    )

    # --------------------------------------------------------
    # IMMAGINE
    # --------------------------------------------------------

    image_html = ""

    if safe_image_url:

        image_html = f"""
        <div style="
            text-align:center;
            margin:25px 0;
        ">

            <img
                src="{safe_image_url}"
                alt="{safe_item_name}"
                style="
                    display:block;
                    margin:0 auto;
                    max-width:320px;
                    width:100%;
                    height:auto;
                    border-radius:18px;
                "
            >

        </div>
        """

    # --------------------------------------------------------
    # EMAIL HTML
    # --------------------------------------------------------

    html_content = f"""
<!DOCTYPE html>

<html lang="it">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>Fortnite Hub</title>

</head>

<body style="
    margin:0;
    padding:0;
    background:#111827;
    font-family:Arial,Helvetica,sans-serif;
    color:#ffffff;
">

    <div style="
        width:100%;
        padding:30px 15px;
        box-sizing:border-box;
    ">

        <div style="
            max-width:600px;
            margin:0 auto;
            background:#1f2937;
            border-radius:20px;
            padding:30px;
            box-sizing:border-box;
            text-align:center;
        ">

            <h1 style="
                margin:0 0 20px 0;
                font-size:30px;
            ">
                🔥 Fortnite Hub
            </h1>

            <p style="
                margin:0 0 10px 0;
                color:#cbd5e1;
                font-size:16px;
            ">
                Ciao {safe_username}!
            </p>

            <h2 style="
                margin:25px 0 15px 0;
                font-size:25px;
                color:#ffffff;
            ">
                {safe_item_name}
            </h2>

            <p style="
                margin:0;
                color:#cbd5e1;
                font-size:16px;
                line-height:1.6;
            ">
                Una skin che hai aggiunto ai tuoi preferiti
                è tornata nello Shop di Fortnite!
            </p>

            {image_html}

            <a
                href="https://fortnite-hub-g6u2.onrender.com"
                style="
                    display:inline-block;
                    margin-top:10px;
                    padding:14px 24px;
                    border-radius:12px;
                    background:#6366f1;
                    color:#ffffff;
                    text-decoration:none;
                    font-size:16px;
                    font-weight:bold;
                "
            >
                Apri Fortnite Hub
            </a>

            <p style="
                margin:30px 0 0 0;
                color:#94a3b8;
                font-size:13px;
                line-height:1.5;
            ">
                Questa email è stata inviata automaticamente
                da Fortnite Hub perché hai attivato le notifiche
                per i tuoi preferiti.
            </p>

        </div>

    </div>

</body>

</html>
"""

    # --------------------------------------------------------
    # INVIO CON RESEND
    # --------------------------------------------------------

    try:

        resend.api_key = RESEND_API_KEY

        response = resend.Emails.send(
            {
                "from": FROM_EMAIL,
                "to": [recipient],
                "subject": subject,
                "html": html_content
            }
        )

        print(
            f"✅ Notifica inviata a {recipient}: "
            f"{item_name}"
        )

        print(
            "📨 Resend response:",
            response
        )

        return True

    except Exception as error:

        print(
            "❌ Errore invio email:",
            repr(error)
        )

        return False
