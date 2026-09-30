import os
import resend


# ============================================================
# CONFIGURAZIONE RESEND
# ============================================================

def get_resend_api_key():

    return os.getenv(
        "RESEND_API_KEY"
    )


# ============================================================
# EMAIL DI BENVENUTO
# ============================================================

def send_welcome_email(
    email,
    username
):

    api_key = get_resend_api_key()

    if not api_key:

        print(
            "⚠️ RESEND_API_KEY non configurata."
        )

        return False

    resend.api_key = api_key

    html = f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <style>

            body {{
                margin: 0;
                padding: 0;
                background: #080b16;
                font-family: Arial, sans-serif;
                color: #ffffff;
            }}

            .container {{
                max-width: 600px;
                margin: 40px auto;
                background: #11162a;
                border-radius: 16px;
                overflow: hidden;
                border: 1px solid #26345c;
            }}

            .header {{
                padding: 35px 30px;
                text-align: center;
                background: linear-gradient(
                    135deg,
                    #101b3d,
                    #24134d
                );
            }}

            .logo {{
                font-size: 32px;
                font-weight: bold;
                color: #ffffff;
            }}

            .logo span {{
                color: #6ee7ff;
            }}

            .content {{
                padding: 35px 30px;
            }}

            h1 {{
                margin-top: 0;
                color: #ffffff;
            }}

            p {{
                color: #b9c3df;
                font-size: 16px;
                line-height: 1.7;
            }}

            .button {{
                display: inline-block;
                margin-top: 20px;
                padding: 14px 24px;
                background: #6ee7ff;
                color: #07101d;
                text-decoration: none;
                border-radius: 10px;
                font-weight: bold;
            }}

            .footer {{
                padding: 20px 30px;
                text-align: center;
                color: #697493;
                font-size: 12px;
            }}

        </style>

    </head>


    <body>

        <div class="container">

            <div class="header">

                <div class="logo">
                    FORTNITE <span>HUB</span>
                </div>

            </div>


            <div class="content">

                <h1>
                    Benvenuto, {username}! 🎮
                </h1>

                <p>
                    Il tuo account Fortnite Hub è stato
                    creato con successo.
                </p>

                <p>
                    Ora puoi iniziare a esplorare il sito,
                    seguire lo Shop e prepararti alle
                    prossime funzionalità.
                </p>

                <a
                    href="https://fortnite-hub-g6u2.onrender.com/"
                    class="button"
                >
                    Vai a Fortnite Hub
                </a>

            </div>


            <div class="footer">

                Fortnite Hub

            </div>

        </div>

    </body>

    </html>
    """

    try:

        response = resend.Emails.send(
            {
                "from": "Fortnite Hub <onboarding@resend.dev>",

                "to": [email],

                "subject": "Benvenuto su Fortnite Hub 🎮",

                "html": html
            }
        )

        print(
            "✅ Email di benvenuto inviata:",
            response
        )

        return True

    except Exception as error:

        print(
            "❌ Errore invio email:",
            error
        )

        return False


# ============================================================
# EMAIL SKIN TORNATA NELLO SHOP
# ============================================================

def send_skin_shop_notification(
    email,
    username,
    skin_name,
    skin_image=None,
    shop_date=None
):

    api_key = get_resend_api_key()

    if not api_key:

        print(
            "⚠️ RESEND_API_KEY non configurata."
        )

        return False

    resend.api_key = api_key

    image_html = ""

    if skin_image:

        image_html = f"""
        <div style="
            text-align:center;
            margin:25px 0;
        ">

            <img
                src="{skin_image}"
                alt="{skin_name}"
                style="
                    width:220px;
                    max-width:100%;
                    border-radius:16px;
                    display:inline-block;
                "
            >

        </div>
        """

    date_html = ""

    if shop_date:

        date_html = f"""
        <p>
            📅 <strong>Data Shop:</strong>
            {shop_date}
        </p>
        """

    html = f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <style>

            body {{
                margin: 0;
                padding: 0;
                background: #080b16;
                font-family: Arial, sans-serif;
                color: #ffffff;
            }}

            .container {{
                max-width: 600px;
                margin: 40px auto;
                background: #11162a;
                border-radius: 18px;
                overflow: hidden;
                border: 1px solid #26345c;
            }}

            .header {{
                padding: 35px 30px;
                text-align: center;
                background: linear-gradient(
                    135deg,
                    #101b3d,
                    #24134d
                );
            }}

            .logo {{
                font-size: 30px;
                font-weight: bold;
                color: #ffffff;
            }}

            .logo span {{
                color: #6ee7ff;
            }}

            .content {{
                padding: 35px 30px;
            }}

            h1 {{
                margin-top: 0;
                color: #ffffff;
                font-size: 28px;
            }}

            h2 {{
                color: #6ee7ff;
                font-size: 22px;
            }}

            p {{
                color: #b9c3df;
                font-size: 16px;
                line-height: 1.7;
            }}

            .skin-box {{
                padding: 20px;
                background: #0b1124;
                border: 1px solid #26345c;
                border-radius: 16px;
                text-align: center;
            }}

            .button {{
                display: inline-block;
                margin-top: 20px;
                padding: 14px 24px;
                background: #6ee7ff;
                color: #07101d;
                text-decoration: none;
                border-radius: 10px;
                font-weight: bold;
            }}

            .footer {{
                padding: 20px 30px;
                text-align: center;
                color: #697493;
                font-size: 12px;
            }}

        </style>

    </head>


    <body>

        <div class="container">

            <div class="header">

                <div class="logo">
                    FORTNITE <span>HUB</span>
                </div>

            </div>


            <div class="content">

                <h1>
                    🔔 Skin nello Shop!
                </h1>

                <p>
                    Ciao {username}!
                </p>

                <p>
                    Una delle skin che stai monitorando
                    è tornata nello Shop di Fortnite.
                </p>


                <div class="skin-box">

                    <h2>
                        {skin_name}
                    </h2>

                    {image_html}

                    {date_html}

                </div>


                <p>
                    Controlla subito Fortnite Hub
                    per vedere tutti i dettagli.
                </p>


                <div style="text-align:center;">

                    <a
                        href="https://fortnite-hub-g6u2.onrender.com/skins"
                        class="button"
                    >
                        🛒 Vai allo Shop
                    </a>

                </div>

            </div>


            <div class="footer">

                Fortnite Hub · Skin Tracker

            </div>

        </div>

    </body>

    </html>
    """

    try:

        response = resend.Emails.send(
            {
                "from": "Fortnite Hub <onboarding@resend.dev>",

                "to": [email],

                "subject":
                    f"🔔 {skin_name} è tornata nello Shop!",

                "html": html
            }
        )

        print(
            "✅ Notifica skin inviata:",
            response
        )

        return True

    except Exception as error:

        print(
            "❌ Errore invio notifica skin:",
            error
        )

        return False
