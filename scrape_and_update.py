#!/usr/bin/env python3
import os
import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Read environment variables
CREDENTIALS_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

# Parse service‐account creds
creds_dict = json.loads(CREDENTIALS_JSON)
creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ],
)

# Authorize gspread
gc = gspread.authorize(creds)

# Load the CSV and scrub NaNs
CSV_PATH = "ITTF_World_Rankings_2021-2025_updated.csv"
df = pd.read_csv(CSV_PATH)
df = df.fillna("")  # replace all NaN/Inf with empty strings

# Open the sheet (or create the tab if missing)
sh = gc.open_by_key(SPREADSHEET_ID)
try:
    worksheet = sh.worksheet(SHEET_NAME)
    worksheet.clear()
except gspread.WorksheetNotFound:
    worksheet = sh.add_worksheet(
        title=SHEET_NAME,
        rows=str(df.shape[0] + 10),
        cols=str(df.shape[1] + 5),
    )

# Prepare data (header + rows)
data = [df.columns.tolist()] + df.values.tolist()

# Upload using the new keyword-arg order
worksheet.update(values=data, range_name="A1")

print(f"✅ Uploaded {len(df)} rows to “{SHEET_NAME}” in spreadsheet {SPREADSHEET_ID}")
