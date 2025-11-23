import pandas as pd
import os

DATA_DIR = "data"
TEMP_PATH = os.path.join(DATA_DIR, "sample.xlsx")

if not os.path.exists(TEMP_PATH):
    print("sample.xlsx not found")
    exit(1)

print("Reading Excel file...")
xl = pd.ExcelFile(TEMP_PATH)
for sheet in xl.sheet_names:
    print(f"\n--- Inspecting sheet: {sheet} ---")
    df = pd.read_excel(TEMP_PATH, sheet_name=sheet)

    # Print first 50 rows to see structure
    print(df.head(50))

    # Search for "Rate", "Price", "価格", "金利"
    mask = (
        df.astype(str)
        .apply(lambda x: x.str.contains("Rate|Price|価格|金利", case=False, na=False))
        .any(axis=1)
    )
    if mask.any():
        print("Found keywords!")
        print(df[mask].head(20))
