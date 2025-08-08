import os
import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1) Pull in the three env vars by name!
CREDENTIALS_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
SPREADSHEET_ID    = os.environ["SPREADSHEET_ID"]
SHEET_NAME        = os.environ["SHEET_NAME"]

# 2) Parse your service‐account JSON
creds_dict = json.loads(CREDENTIALS_JSON)
creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)

# 3) Authorize gspread
gc = gspread.authorize(creds)

# 4) Load your freshly generated CSV
CSV_PATH = "ITTF_World_Rankings_2021-2025_updated.csv"
df = pd.read_csv(CSV_PATH)

# 5) Open the spreadsheet & get or create the worksheet
sh = gc.open_by_key(SPREADSHEET_ID)
try:
    worksheet = sh.worksheet(SHEET_NAME)
    worksheet.clear()
except gspread.WorksheetNotFound:
    # Add a new sheet big enough for your data
    worksheet = sh.add_worksheet(
        title=SHEET_NAME,
        rows=str(df.shape[0] + 10),
        cols=str(df.shape[1] + 5)
    )

# 6) Prep and push the data (including header row)
data = [df.columns.tolist()] + df.values.tolist()
worksheet.update("A1", data)

print(f"✅ Uploaded {len(df)} rows to “{SHEET_NAME}” in "
      f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
