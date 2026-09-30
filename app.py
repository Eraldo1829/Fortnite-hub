from flask import Flask, render_template
from database.database import create_database
from services.fortnite_api import get_shop


app = Flask(__name__)

create_database()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/skins")
def skins():
    shop = get_shop()

    return render_template(
        "skins.html",
        shop=shop
    )


if __name__ == "__main__":
    app.run()
