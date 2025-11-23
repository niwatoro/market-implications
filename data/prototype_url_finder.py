import requests
from bs4 import BeautifulSoup
import urllib.parse


def find_pdf_with_xpath_logic():
    url = "https://www.jpx.co.jp/jscc/toukei_irs.html"
    print(f"Fetching {url}...")
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    # XPath: //*[@id="main_body"]/div[3]/table/tbody/tr/td[2]/a
    # Note: div[3] in XPath is 1-indexed, so it's the 3rd div.

    main_body = soup.find(id="main_body")
    if not main_body:
        print("Could not find id='main_body'")
        return

    # Find direct div children
    # BeautifulSoup's find_all(recursive=False) might be useful, or just iterating children
    divs = [d for d in main_body.find_all("div", recursive=False)]

    if len(divs) < 3:
        print(f"Found only {len(divs)} divs under main_body")
        # Fallback: maybe the user meant nested divs or just the 3rd div appearing in main_body
        # Let's try to find the table directly if the div structure is loose
    else:
        target_div = divs[2]  # 0-indexed index 2 is 3rd element
        print("Found target div")

        table = target_div.find("table")
        if table:
            rows = table.find_all("tr")
            if rows:
                first_row = rows[0]
                cols = first_row.find_all("td")
                if len(cols) >= 2:
                    target_td = cols[1]  # 2nd td
                    link = target_td.find("a")
                    if link:
                        href = link.get("href")
                        full_url = urllib.parse.urljoin(url, href)
                        print(f"Found URL via strict path: {full_url}")
                        return
                    else:
                        print("No link in 2nd td")
                else:
                    print("Not enough columns in first row")
            else:
                print("No rows in table")
        else:
            print("No table in target div")

    # Fallback: Look for any table that looks like it has links in the 2nd column
    print("\n--- Fallback Search ---")
    tables = main_body.find_all("table")
    for i, table in enumerate(tables):
        rows = table.find_all("tr")
        if not rows:
            continue

        # Check first row
        cols = rows[0].find_all("td")
        if len(cols) >= 2:
            link = cols[1].find("a")
            if link:
                print(f"Table {i + 1}, Row 1, Col 2 Link: {link.get('href')}")


if __name__ == "__main__":
    find_pdf_with_xpath_logic()
