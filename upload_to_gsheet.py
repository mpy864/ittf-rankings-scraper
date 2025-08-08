import os
import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Read environment variables (for GitHub Actions, set these as repo secrets or workflow env vars)
SPREADSHEET_ID = os.environ.get("1V4y_Uf8H4_dprZCDb0hxCuegY5XW1vwL")
SHEET_NAME = os.environ.get("Rankings")
CREDENTIALS_JSON = os.environ.get("github-bot@ittf-rankings-468409.iam.gserviceaccount.com")

if CREDENTIALS_JSON is None:
    raise Exception("github-bot@ittf-rankings-468409.iam.gserviceaccount.com")

creds_dict = json.loads(CREDENTIALS_JSON)
creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)

# Authorize gspread
gc = gspread.authorize(creds)

# Read your CSV (can also use a DataFrame you have in code)
CSV_PATH = "ITTF_World_Rankings_2021-2025_updated.csv"
df = pd.read_csv(CSV_PATH)

# Open the Google Sheet and worksheet
sh = gc.open_by_key(SPREADSHEET_ID)

try:
    worksheet = sh.worksheet(SHEET_NAME)
    worksheet.clear()
except gspread.WorksheetNotFound:
    worksheet = sh.add_worksheet(title=SHEET_NAME, rows=df.shape[0]+10, cols=df.shape[1]+5)

# Prepare data for upload (include header row)
data = [df.columns.values.tolist()] + df.values.tolist()

# Upload to Google Sheet
worksheet.update("A1", data)

print(f"✅ Uploaded {len(df)} rows to {SHEET_NAME} in https://docs.google.com/spreadsheets/d/1V4y_Uf8H4_dprZCDb0hxCuegY5XW1vwL")
