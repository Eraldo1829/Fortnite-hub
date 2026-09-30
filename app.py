from flask import Flask, render_template

from database.database import create_database

from services.fortnite_api import (
    get_shop,
    prepare_shop,
    group_shop_items
)


app = Flask(__name__)


create_database()


@app.route("/")
def home():

    return render_template(
        "index.html"
    )


@app.route("/skins")
def skins():

    shop = get_shop()

    shop_items = prepare_shop(
        shop
    )

    shop_groups = group_shop_items(
        shop_items
    )

    shop_date = None

    if shop and shop.get("data"):

        shop_date = shop["data"].get(
            "date"
        )


    return render_template(
        "skins.html",
        shop_items=shop_items,
        shop_groups=shop_groups,
        shop_date=shop_date
    )


@app.route("/skins/<int:item_index>")
def skin_detail(item_index):

    shop = get_shop()

    shop_items = prepare_shop(
        shop
    )


    if not shop_items:

        return render_template(
            "skin_detail.html",
            item=None
        ), 404


    if (
        item_index < 0
        or item_index >= len(shop_items)
    ):

        return render_template(
            "skin_detail.html",
            item=None
        ), 404


    item = shop_items[
        item_index
    ]


    return render_template(
        "skin_detail.html",
        item=item
    )


if __name__ == "__main__":

    app.run()
