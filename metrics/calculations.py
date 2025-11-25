from datetime import datetime
from typing import Any

import pandas as pd


def calculate_rate_probabilities(data_json: dict[str, Any]) -> dict[str, Any] | None:
    """Calculate BoJ rate hike/cut probabilities based on market-implied rates."""
    if not data_json or "rates" not in data_json or "boj_meetings" not in data_json:
        return None

    if not data_json["boj_meetings"]:
        return None

    rates = data_json["rates"]
    df = pd.DataFrame(rates)

    # Get source date and current rate
    source_date_str = data_json.get("source_date", datetime.now().strftime("%Y/%m/%d"))
    try:
        source_date = datetime.strptime(source_date_str, "%Y/%m/%d")
    except ValueError:
        source_date = datetime.now()

    # Convert tenors to days for interpolation
    def tenor_to_days(tenor: str, source_date: datetime) -> float:
        t = tenor.upper()
        if "D" in t:
            return float(t.replace("D", ""))
        if "W" in t:
            return float(t.replace("W", "")) * 7
        if "M" in t:
            return (
                (source_date + pd.DateOffset(months=int(t.replace("M", ""))))
                - source_date
            ).days
        if "Y" in t:
            return (
                (source_date + pd.DateOffset(years=int(t.replace("Y", ""))))
                - source_date
            ).days
        return 0

    df["days"] = df["tenor"].apply(tenor_to_days, source_date=source_date)
    df = df.sort_values("days")

    # Get current overnight rate (1D)
    current_rate = (
        df[df["tenor"] == "1D"]["rate"].iloc[0]
        if len(df[df["tenor"] == "1D"]) > 0
        else df["rate"].iloc[0]
    )

    # Get next meeting date
    next_meeting_str = data_json["boj_meetings"][0]
    next_meeting = datetime.strptime(next_meeting_str, "%Y-%m-%d")

    # Calculate days until meeting
    days_to_meeting = (next_meeting - source_date).days

    # Calculate implied rate
    def calculate_implied_rate(df: pd.DataFrame, days_pre: int, r_pre: float) -> float:
        row_post = df[df["days"] >= days_to_meeting].iloc[0]
        r_post = row_post["rate"]
        days_post = row_post["days"] - days_pre

        return float((r_post * (days_pre + days_post) - r_pre * days_pre) / days_post)

    implied_rate = calculate_implied_rate(df, days_to_meeting, current_rate)

    probability_of_hike = (implied_rate - current_rate) / 0.25  # 25bps = 0.25%

    # Create probability distribution
    # If probability > 0: hike expected
    # If probability < 0: cut expected
    # Cap probabilities at 100%

    if probability_of_hike > 0:
        # Market implies hike
        prob_hike_25bps = min(probability_of_hike * 100, 100)
        prob_no_change = max(100 - prob_hike_25bps, 0)
        prob_cut_25bps = 0
    elif probability_of_hike < 0:
        # Market implies cut
        prob_cut_25bps = min(abs(probability_of_hike) * 100, 100)
        prob_no_change = max(100 - prob_cut_25bps, 0)
        prob_hike_25bps = 0
    else:
        # No change implied
        prob_no_change = 100
        prob_hike_25bps = 0
        prob_cut_25bps = 0

    return {
        "next_meeting_date": next_meeting_str,
        "days_to_meeting": days_to_meeting,
        "current_rate": round(current_rate, 3),
        "implied_rate": round(implied_rate, 3),
        "probabilities": {
            "no_change": round(prob_no_change, 1),
            "hike_25bps": round(prob_hike_25bps, 1),
            "cut_25bps": round(prob_cut_25bps, 1),
        },
    }


def process_market_data(data_json: dict[str, Any]) -> dict[str, Any] | None:
    """Process raw market data JSON into a structured format for the dashboard."""
    if not data_json or "rates" not in data_json:
        return None

    rates = data_json["rates"]
    df = pd.DataFrame(rates)

    # Convert tenors to approx years for plotting
    def tenor_to_years(t: str) -> float:
        t = t.upper()
        if "D" in t:
            return float(t.replace("D", "")) / 365
        if "W" in t:
            return float(t.replace("W", "")) / 52
        if "M" in t:
            return float(t.replace("M", "")) / 12
        if "Y" in t:
            return float(t.replace("Y", ""))
        return 0

    df["years"] = df["tenor"].apply(tenor_to_years)
    df = df.sort_values("years")

    # Calculate rate probabilities
    rate_probabilities = calculate_rate_probabilities(data_json)

    return {
        "curve": df.to_dict(orient="records"),
        "jgb_curve": data_json.get("jgb_curve", []),
        "latest_date": data_json.get("source_date"),
        "updated_at": data_json.get("updated_at"),
        "rate_probabilities": rate_probabilities,
        "credit_data": data_json.get("credit_data"),
    }
