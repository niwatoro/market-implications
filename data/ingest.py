import json
import os
import re
import urllib.parse
from datetime import datetime
from typing import Any

import pdfplumber
import requests
from bs4 import BeautifulSoup

from metrics import calculate_default_probabilities

DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "market_data.json")
PDF_PATH = os.path.join(DATA_DIR, "latest_rates.pdf")


def get_pdf_url() -> str:
    """
    Retrieve the JPX PDF URL.

    Returns the URL string pointing to the latest rates PDF.
    """
    url = "https://www.jpx.co.jp/jscc/toukei_irs.html"
    print(f"Fetching {url}...")
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    link = soup.select_one("a[href$='pdf']")
    if not link:
        raise Exception("Could not find PDF link")

    href = link.get("href")
    return urllib.parse.urljoin(url, str(href) if href else "")


def download_pdf(url: str) -> str:
    """Download the PDF file."""
    print(f"Downloading PDF from {url}...")
    resp = requests.get(url)
    resp.raise_for_status()
    with open(PDF_PATH, "wb") as f:
        f.write(resp.content)
    return PDF_PATH


def fetch_boj_meeting_dates() -> list[str]:
    """
    Fetch upcoming BoJ monetary policy meeting dates from the official website.
    Returns a list of meeting dates in ISO format (YYYY-MM-DD).
    """
    url = "https://www.boj.or.jp/mopo/mpmsche_minu/index.htm"
    print(f"Fetching BoJ meeting schedule from {url}...")

    try:
        resp = requests.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        meetings = []
        current_year = datetime.now().year
        current_date = datetime.now()

        # Find all links that contain meeting dates
        # Pattern: "12月18日（木）・19日（金）" or "1月23日（木）・24日（金）"
        date_pattern = re.compile(r"(\d{1,2})月(\d{1,2})日（.）・(\d{1,2})日")

        # Get all text content
        page_text = soup.get_text()

        # Find all date matches
        for match in date_pattern.finditer(page_text):
            month = int(match.group(1))
            day2 = int(match.group(3))  # Second day is when decisions are announced

            # Determine year (if month < current month, it's next year)
            year = current_year
            if month < current_date.month or (
                month == current_date.month and day2 < current_date.day
            ):
                year = current_year + 1

            try:
                meeting_date = datetime(year, month, day2)
                # Only include future meetings
                if meeting_date > current_date:
                    iso_date = meeting_date.strftime("%Y-%m-%d")
                    if iso_date not in meetings:  # Avoid duplicates
                        meetings.append(iso_date)
            except ValueError:
                # Invalid date, skip
                continue

        # Sort meetings chronologically
        meetings.sort()
        print(f"Found {len(meetings)} upcoming meetings: {meetings[:3]}...")
        return meetings

    except Exception as e:
        print(f"Warning: Could not fetch BoJ meeting dates: {e}")
        return []


def parse_pdf(pdf_path: str) -> tuple[str | None, list[dict[str, Any]]]:
    """Parse the PDF file."""
    print("Parsing PDF...")
    data = []
    extracted_date = None

    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            return None, []

        page = pdf.pages[0]
        tables = page.extract_tables()

        if not tables:
            return None, []

        table = tables[0]

        # Try to find date in the second row (index 1)
        # Structure: ['', None, ..., '2025/11/21']
        for item in table[1]:
            if item and "202" in item and "/" in item:
                extracted_date = item
                break

        # OIS Data seems to start around row 4 (index 3)
        # Column indices based on inspection:
        # Col 3 (index 3): Tenor
        # Col 4 (index 4): Rate

        start_row_index = 3
        for row in table[start_row_index:]:
            # Check if row has enough columns
            if len(row) < 5:
                continue

            tenor = row[3]
            rate = row[4]

            # Stop if we hit empty or non-data rows
            if not tenor or not rate:
                continue

            # Clean up
            tenor = tenor.strip()
            # Rate might be string, keep it as is or convert to float
            try:
                rate_val = float(rate)
            except (ValueError, TypeError):
                continue

            data.append({"tenor": tenor, "rate": rate_val})

    return extracted_date, data


def download_jsda_csv() -> str | None:
    """
    Download the latest Reference Statistical Prices CSV from JSDA.
    Returns the path to the downloaded file.
    """
    base_url = "https://market.jsda.or.jp/shijyo/saiken/baibai/baisanchi"
    index_url = f"{base_url}/index.html"
    print(f"Checking JSDA for latest CSV at {index_url}...")

    try:
        # We need to find the link. The browser tool showed it's like:
        # ./files/2025/S251125.csv
        # We can try to construct it based on today's date or scrape it.
        # Scraping is safer.
        resp = requests.get(index_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        # Look for links ending in .csv
        # The link text usually contains dates like "2025.11.25"
        csv_links = []
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if href.lower().endswith(".csv") and "files" in href:
                csv_links.append(href)

        if not csv_links:
            print("No CSV links found on JSDA page.")
            return None

        # Sort to get the latest (assuming filenames contain dates like S251125.csv)
        # S251125 -> 25 (Year 2025) 11 (Month) 25 (Day)
        # Actually S + YYMMDD
        csv_links.sort(reverse=True)
        latest_csv_rel = csv_links[0]

        # Handle relative paths
        # href might be "./files/..." or "files/..."
        latest_csv_url = urllib.parse.urljoin(index_url, str(latest_csv_rel))

        filename = os.path.basename(latest_csv_url)
        save_path = os.path.join(DATA_DIR, filename)

        print(f"Downloading latest CSV from {latest_csv_url}...")
        r = requests.get(latest_csv_url)
        r.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(r.content)

        print(f"Saved CSV to {save_path}")
        return save_path

    except Exception as e:
        print(f"Error downloading JSDA CSV: {e}")
        return None


def main() -> None:
    """Ingest the latest rates PDF and JSDA CSV."""
    try:
        # 1. JPX OIS Rates
        url = get_pdf_url()
        print(f"Found PDF URL: {url}")

        pdf_path = download_pdf(url)
        date_str, rates = parse_pdf(pdf_path)

        if not rates:
            print("No rates extracted!")
            # We continue even if rates fail, to try credit data

        # Fetch BoJ meeting dates
        boj_meetings = fetch_boj_meeting_dates()

        # 2. JSDA Credit Data
        csv_path = download_jsda_csv()
        credit_data = []
        if csv_path:
            print("Calculating default probabilities...")
            credit_data = calculate_default_probabilities(csv_path)
            print(f"Calculated PDs for {len(credit_data)} issuers.")

        output = {
            "updated_at": datetime.now().isoformat(),
            "source_date": date_str,
            "source_url": url,
            "rates": rates,
            "boj_meetings": boj_meetings,
            "credit_data": credit_data,
        }

        with open(OUTPUT_FILE, "w") as f:
            json.dump(output, f, indent=2)

        print(f"Data saved to {OUTPUT_FILE}")
        print(f"Extracted {len(rates)} rates from {date_str}")
        print(f"Found {len(boj_meetings)} upcoming BoJ meetings")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
