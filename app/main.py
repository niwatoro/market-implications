import json
import os
from typing import Any

from flask import Flask, Response, jsonify, render_template

from metrics import process_market_data

app = Flask(__name__, template_folder="../templates", static_folder="../static")

DATA_FILE = "data/market_data.json"


def load_data() -> dict[str, Any] | None:
    """
    Load market data from the JSON file.

    Returns the parsed JSON as a dictionary, or ``None`` if the file does not exist.
    """
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE) as f:
        return json.load(f)


@app.route("/")
def index() -> str:
    """
    Render the main page with processed market data.

    Loads raw market data, processes it, and renders ``index.html`` with the
    processed data or ``None`` if no data is available.
    """
    raw_data = load_data()
    processed = process_market_data(raw_data) if raw_data else None
    return render_template("index.html", data=processed)


@app.route("/api/data")
def get_data() -> Response:
    """
    Return market data as JSON.

    Loads raw market data and returns the processed data via ``jsonify``.
    If no data is available, returns an error message.
    """
    raw_data = load_data()
    result = (
        process_market_data(raw_data) if raw_data else {"error": "No data available"}
    )
    return jsonify(result)


if __name__ == "__main__":
    app.run(port=8000, debug=True)
