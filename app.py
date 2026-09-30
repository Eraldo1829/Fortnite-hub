from flask import Flask, render_template

from database.database import create_database
from services.fortnite_api import get_shop, prepare_shop


app = Flask(__name__)

create_database()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/skins")
def skins():

    shop = get_shop()

    shop_items = prepare_shop(shop)

    shop_date = None

    if shop and shop.get("data"):
        shop_date = shop["data"].get("date")

    return render_template(
        "skins.html",
        shop_items=shop_items,
        shop_date=shop_date
    )


if __name__ == "__main__":
    app.run()
