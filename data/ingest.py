import requests
import pdfplumber
import os
import json
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime

DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "market_data.json")
PDF_PATH = os.path.join(DATA_DIR, "latest_rates.pdf")


def get_pdf_url():
    url = "https://www.jpx.co.jp/jscc/toukei_irs.html"
    print(f"Fetching {url}...")
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    # XPath logic: //*[@id="main_body"]/div[3]/table/tbody/tr/td[2]/a
    main_body = soup.find(id="main_body")
    if not main_body:
        raise Exception("Could not find id='main_body'")

    divs = [d for d in main_body.find_all("div", recursive=False)]
    if len(divs) < 3:
        # Fallback: try to find the table directly
        print("Div structure changed, trying to find table directly...")
        tables = main_body.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if rows:
                cols = rows[0].find_all("td")
                if len(cols) >= 2:
                    link = cols[1].find("a")
                    if link and link.get("href", "").endswith(".pdf"):
                        return urllib.parse.urljoin(url, link.get("href"))
        raise Exception("Could not find PDF link in any table")

    target_div = divs[2]
    table = target_div.find("table")
    if not table:
        raise Exception("No table in target div")

    rows = table.find_all("tr")
    if not rows:
        raise Exception("No rows in table")

    first_row = rows[0]
    cols = first_row.find_all("td")
    if len(cols) < 2:
        raise Exception("Not enough columns in first row")

    link = cols[1].find("a")
    if not link:
        raise Exception("No link in 2nd td")

    return urllib.parse.urljoin(url, link.get("href"))


def download_pdf(url):
    print(f"Downloading PDF from {url}...")
    resp = requests.get(url)
    resp.raise_for_status()
    with open(PDF_PATH, "wb") as f:
        f.write(resp.content)
    return PDF_PATH


def parse_pdf(pdf_path):
    print("Parsing PDF...")
    data = []
    extracted_date = None

    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            return None, None

        page = pdf.pages[0]
        tables = page.extract_tables()

        if not tables:
            return None, None

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
            except:
                continue

            data.append({"tenor": tenor, "rate": rate_val})

    return extracted_date, data


def main():
    try:
        url = get_pdf_url()
        print(f"Found PDF URL: {url}")

        pdf_path = download_pdf(url)
        date_str, rates = parse_pdf(pdf_path)

        if not rates:
            print("No rates extracted!")
            return

        output = {
            "updated_at": datetime.now().isoformat(),
            "source_date": date_str,
            "source_url": url,
            "rates": rates,
        }

        with open(OUTPUT_FILE, "w") as f:
            json.dump(output, f, indent=2)

        print(f"Data saved to {OUTPUT_FILE}")
        print(f"Extracted {len(rates)} rates from {date_str}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
