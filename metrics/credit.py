import re
import unicodedata
from typing import Any

import numpy as np
import pandas as pd

# -----------------------------
# Parameters
# -----------------------------
RECOVERY_RATE = 0.10
LGD = 1.0 - RECOVERY_RATE


def parse_ymd_int(x: Any) -> pd.Timestamp | Any:
    """Convert YYYYMMDD integer/string to datetime."""
    try:
        return pd.to_datetime(str(int(x)), format="%Y%m%d", errors="coerce")
    except (ValueError, TypeError):
        return pd.NaT


def extract_issuer(name: str) -> str:
    """
    Extract issuer name from bond name.
    Example: 'SoftBank Group 55' -> 'SoftBank Group'.
    """
    if not isinstance(name, str):
        return str(name) if name is not None else ""
    # Remove full-width and half-width digits at the end, and common suffixes
    s = re.sub(
        r"劣$",
        "",
        re.sub(
            r"(?<=[^0-9A-Za-z])-",
            "ー",
            re.sub(r"\s*\d+.*$", "", name),
        ),
    )
    return unicodedata.normalize("NFKC", s.strip())


def calculate_default_probabilities(csv_path: str) -> list[dict[str, Any]]:
    """
    Calculate default probabilities from JSDA bond market data CSV.

    Args:
        csv_path: Path to the downloaded JSDA CSV file.

    Returns:
        List of dictionaries containing issuer credit data.

    """
    # Read CSV
    # JSDA CSV usually has no header, encoding is Shift-JIS (cp932)
    try:
        df = pd.read_csv(csv_path, header=None, encoding="cp932")
    except Exception as e:
        print(f"Error reading CSV {csv_path}: {e}")
        return []

    # Assign columns based on JSDA spec (approximate based on user snippet)
    # 0: trade_date, 1: category, 2: issue_code
    # 3: name, 4: maturity, 5: coupon, 6: yield
    # We need at least up to col 6.
    if df.shape[1] < 7:
        print("CSV format unexpected: too few columns")
        return []

    df.columns = pd.Index(
        [
            "trade_date",
            "category",
            "issue_code",
            "name",
            "maturity",
            "coupon",
            "yield",
        ]
        + [f"c{i}" for i in range(7, df.shape[1])]
    )

    # Preprocessing
    df["trade_date_dt"] = df["trade_date"].apply(parse_ymd_int)
    df["maturity_dt"] = df["maturity"].apply(parse_ymd_int)

    # Years to maturity
    # Years to maturity
    # Ensure datetime type for subtraction
    maturity_series = pd.to_datetime(df["maturity_dt"])
    trade_date_series = pd.to_datetime(df["trade_date_dt"])

    # Calculate difference and extract days
    # pd.to_datetime ensures it's datetime
    diff_series = maturity_series - trade_date_series

    # Access .dt.days.
    # Using apply to be safe and avoid .dt accessor issues with stubs
    df["years_to_maturity"] = diff_series.dt.days / 365.0

    # Clean yield
    df["yield"] = pd.to_numeric(df["yield"], errors="coerce")
    # 999.999 usually indicates missing/invalid in these datasets
    df.loc[df["yield"] >= 999, "yield"] = np.nan

    # -----------------------------
    # Construct Risk-Free Curve (JGBs)
    # -----------------------------
    # Filter for JGBs (Government Bonds)
    # Usually category or name can identify them.
    # User snippet uses name contains "国庫短期証券|国債"
    gov_mask = df["name"].astype(str).str.contains("国庫短期証券|国債", na=False)
    gov = df[gov_mask & df["yield"].notna() & df["years_to_maturity"].notna()].copy()

    if gov.empty:
        print("No government bonds found for RF curve.")
        return []

    gov["T_bucket"] = gov["years_to_maturity"].round(3)
    gov_curve = (
        gov.groupby("T_bucket")["yield"].mean().reset_index().sort_values("T_bucket")
    )

    T_points = np.asarray(gov_curve["T_bucket"].values, dtype=float)
    y_points = np.asarray(gov_curve["yield"].values, dtype=float)

    if len(T_points) < 2:
        print("Not enough points for RF curve.")
        return []

    # -----------------------------
    # Corporate Bonds
    # -----------------------------
    # Category 40 is typically "General Corporate Bonds"
    corp_mask = (
        (df["category"] == 40)
        & df["yield"].notna()
        & df["years_to_maturity"].notna()
        & (df["years_to_maturity"] > 0)
    )

    corp = df[corp_mask].copy()

    if corp.empty:
        print("No corporate bonds found.")
        return []

    corp["issuer"] = corp["name"].apply(extract_issuer)

    # Interpolate RF yield
    corp["rf_yield"] = np.interp(
        np.asarray(corp["years_to_maturity"].values, dtype=float), T_points, y_points
    )

    # Calculate Spread
    corp["spread_pct"] = corp["yield"] - corp["rf_yield"]
    corp["spread_dec"] = corp["spread_pct"] / 100.0

    # -----------------------------
    # Estimate Hazard Rate & PD per Issuer
    # -----------------------------
    # spread ≈ LGD * lambda
    # lambda = spread / LGD
    # We average spreads per issuer to get a stable lambda
    issuer_stats = (
        corp.groupby("issuer")
        .agg(
            n_bonds=("issue_code", "count"),
            avg_spread_dec=("spread_dec", "mean"),
            avg_years=("years_to_maturity", "mean"),
        )
        .reset_index()
    )

    # Filter out issuers with negative spreads (anomalies or better than gov)
    # or maybe keep them but PD will be 0.
    issuer_stats["lambda"] = (issuer_stats["avg_spread_dec"] / LGD).clip(lower=0.0)

    # Calculate PDs for different horizons (1Y, 3Y, 5Y, 10Y)
    horizons = [1, 3, 5, 10]
    for t in horizons:
        issuer_stats[f"PD{t}Y"] = 1.0 - np.exp(-issuer_stats["lambda"] * t)

    # Format for output
    results = []
    for _, row in issuer_stats.iterrows():
        # Convert PD to percentage string or float
        results.append(
            {
                "issuer": row["issuer"],
                "n_bonds": int(row["n_bonds"]),
                "avg_spread_bps": round(row["avg_spread_dec"] * 10000, 1),
                "avg_years": round(row["avg_years"], 1),
                "pd_1y": round(row["PD1Y"] * 100, 2),
                "pd_3y": round(row["PD3Y"] * 100, 2),
                "pd_5y": round(row["PD5Y"] * 100, 2),
                "pd_10y": round(row["PD10Y"] * 100, 2),
            }
        )

    # Sort by 5Y PD descending (riskiest first)
    results.sort(key=lambda x: x["pd_5y"], reverse=True)

    return results
