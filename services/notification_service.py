import os
import resend


# ============================================================
# CONFIGURAZIONE RESEND
# ============================================================

RESEND_API_KEY = os.getenv(
    "RESEND_API_KEY"
)

FROM_EMAIL = "Fortnite Hub <onboarding@resend.dev>"


# ============================================================
# INVIO EMAIL
# ============================================================

def send_skin_notification(
    recipient,
    username,
    item_name,
    image_url=None
):

    if not recipient:

        print(
            "❌ Nessun destinatario."
        )

        return False

    if not RESEND_API_KEY:

        print(
            "❌ RESEND_API_KEY non configurata."
        )

        return False

    subject = (
        f"🔥 {item_name} è tornata nello Shop!"
    )

    # ========================================================
    # IMMAGINE
    # ========================================================

    image_html = ""

    if image_url:

        image_html = f"""
        <div style="
            text-align:center;
            margin:25px 0;
        ">
            <img
                src="{image_url}"
                alt="{item_name}"
                style="
                    max-width:320px;
                    width:100%;
                    border-radius:18px;
                "
            >
        </div>
        """

    # ========================================================
    # HTML EMAIL
    # ========================================================

    html = f"""
    <!DOCTYPE html>

    <html lang="it">

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width,
            initial-scale=1.0"
        >

        <title>
            Fortnite Hub
        </title>

    </head>

    <body style="
        margin:0;
        padding:0;
        background:#111827;
        font-family:Arial,sans-serif;
        color:#ffffff;
    ">

        <div style="
            max-width:600px;
            margin:0 auto;
            padding:30px 20px;
        ">

            <div style="
                background:#1f2937;
                border-radius:20px;
                padding:30px;
                text-align:center;
            ">

                <h1 style="
                    margin-top:0;
                    font-size:28px;
                ">
                    🔥 Fortnite Hub
                </h1>

                <p style="
                    color:#cbd5e1;
                    font-size:16px;
                ">
                    Ciao {username}!
                </p>

                <h2 style="
                    font-size:24px;
                    margin-top:25px;
                ">
                    {item_name}
                </h2>

                <p style="
                    color:#cbd5e1;
                    font-size:16px;
                ">
                    Una skin che hai nei tuoi
                    preferiti è tornata
                    nello Shop di Fortnite!
                </p>

                {image_html}

                <a
                    href="https://fortnite-hub-g6u2.onrender.com"
                    style="
                        display:inline-block;
                        padding:14px 24px;
                        border-radius:12px;
                        background:#6366f1;
                        color:white;
                        text-decoration:none;
                        font-weight:bold;
                    "
                >
                    Apri Fortnite Hub
                </a>

            </div>

        </div>

    </body>

    </html>
    """

    # ========================================================
    # RESEND
    # ========================================================

    try:

        resend.api_key = RESEND_API_KEY

        response = resend.Emails.send(
            {
                "from": FROM_EMAIL,
                "to": [recipient],
                "subject": subject,
                "html": html
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
            error
        )

        return False
