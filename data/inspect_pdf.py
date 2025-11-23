import requests
import pdfplumber
import os

DATA_DIR = "data"
PDF_PATH = os.path.join(DATA_DIR, "settlement_rates.pdf")
URL = "https://www.jpx.co.jp/jscc/cimhll0000000umu-att/SettlementRates_20251121.pdf"


def inspect_pdf():
    print(f"Downloading {URL}...")
    resp = requests.get(URL)
    resp.raise_for_status()

    with open(PDF_PATH, "wb") as f:
        f.write(resp.content)

    print("Inspecting PDF...")
    with pdfplumber.open(PDF_PATH) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"\n--- Page {i + 1} ---")
            text = page.extract_text()
            print(text[:500])  # Print first 500 chars

            print("\n--- Tables ---")
            tables = page.extract_tables()
            for j, table in enumerate(tables):
                print(f"Table {j + 1}:")
                # Print first 5 rows
                for row in table[:5]:
                    print(row)


if __name__ == "__main__":
    inspect_pdf()
