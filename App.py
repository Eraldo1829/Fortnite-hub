from flask import Flask
from database.database import create_database

app = Flask(__name__)

create_database()


@app.route("/")
def home():
    return "🎮 Fortnite Hub è online!"


if __name__ == "__main__":
    app.run()
