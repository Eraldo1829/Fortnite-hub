import os
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# ============================================================
# CONFIGURAZIONE
# ============================================================

SMTP_HOST = os.getenv(
    "SMTP_HOST",
    "smtp.gmail.com"
)

SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "587"
    )
)

SMTP_USERNAME = os.getenv(
    "SMTP_USERNAME",
    ""
)

SMTP_PASSWORD = os.getenv(
    "SMTP_PASSWORD",
    ""
)

FROM_EMAIL = os.getenv(
    "FROM_EMAIL",
    SMTP_USERNAME
)


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

    if not SMTP_USERNAME:

        print(
            "❌ SMTP_USERNAME non configurato."
        )

        return False

    if not SMTP_PASSWORD:

        print(
            "❌ SMTP_PASSWORD non configurato."
        )

        return False

    subject = (
        f"🔥 {item_name} è tornata nello Shop!"
    )

    # ========================================================
    # HTML
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
                    href="#"
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
    # EMAIL
    # ========================================================

    message = MIMEMultipart(
        "alternative"
    )

    message["Subject"] = subject

    message["From"] = FROM_EMAIL

    message["To"] = recipient

    message.attach(
        MIMEText(
            html,
            "html",
            "utf-8"
        )
    )

    # ========================================================
    # SMTP
    # ========================================================

    try:

        server = smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=30
        )

        server.starttls()

        server.login(
            SMTP_USERNAME,
            SMTP_PASSWORD
        )

        server.sendmail(
            FROM_EMAIL,
            recipient,
            message.as_string()
        )

        server.quit()

        print(
            f"✅ Notifica inviata a {recipient}: "
            f"{item_name}"
        )

        return True

    except Exception as error:

        print(
            "❌ Errore invio email:",
            error
        )

        return False
