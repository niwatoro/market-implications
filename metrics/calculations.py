import pandas as pd


def process_market_data(data_json):
    """
    Process raw market data JSON into a structured format for the dashboard.
    """
    if not data_json or "rates" not in data_json:
        return None

    rates = data_json["rates"]
    df = pd.DataFrame(rates)

    # Convert tenors to approx years for plotting
    def tenor_to_years(t):
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

    # Calculate simple forward rates (bootstrapping is complex, using simple implied fwd for visualization)
    # Forward rate between t1 and t2:
    # (1 + r2*t2) = (1 + r1*t1) * (1 + f * (t2-t1))
    # f = [ (1 + r2*t2) / (1 + r1*t1) - 1 ] / (t2 - t1)

    # We'll calculate 3M forward rates starting from each tenor
    # This is a simplification.

    return {
        "curve": df.to_dict(orient="records"),
        "latest_date": data_json.get("source_date"),
        "updated_at": data_json.get("updated_at"),
    }
