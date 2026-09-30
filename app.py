from flask import Flask, render_template
from database.database import create_database

app = Flask(__name__)

create_database()


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/skins")
def skins():
    return render_template("skins.html")


if __name__ == "__main__":
    app.run()
