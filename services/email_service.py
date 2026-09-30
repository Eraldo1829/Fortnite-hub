import os
import resend


def send_welcome_email(
    email,
    username
):

    api_key = os.getenv(
        "RESEND_API_KEY"
    )

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
