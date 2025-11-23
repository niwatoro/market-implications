from flask import Flask, render_template, jsonify
import json
import os
from metrics.calculations import process_market_data

app = Flask(__name__, template_folder="../templates", static_folder="../static")

DATA_FILE = "data/market_data.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE, "r") as f:
        return json.load(f)


@app.route("/")
def index():
    raw_data = load_data()
    processed = process_market_data(raw_data) if raw_data else None
    return render_template("index.html", data=processed)


@app.route("/api/data")
def get_data():
    raw_data = load_data()
    result = (
        process_market_data(raw_data) if raw_data else {"error": "No data available"}
    )
    return jsonify(result)


if __name__ == "__main__":
    app.run(port=8000, debug=True)
