#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import sys
import json
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials

def main():
    # 1) Read & validate env-vars
    for var in ("GOOGLE_SERVICE_ACCOUNT_JSON","SPREADSHEET_ID","SHEET_NAME"):
        if var not in os.environ:
            print(f"❌ Missing environment variable: {var}", file=sys.stderr)
            sys.exit(1)

    CRED_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
    SHEET_NAME = os.environ["SHEET_NAME"]

    # 2) Parse service-account credentials
    try:
        creds_info = json.loads(CRED_JSON)
    except json.JSONDecodeError:
        print("❌ Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON", file=sys.stderr)
        sys.exit(1)

    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )

    # 3) Authorize gspread
    gc = gspread.authorize(creds)

    # 4) Load CSV (must run scraper first)
    CSV = "ITTF_World_Rankings_2021-2025_updated.csv"
    if not os.path.exists(CSV):
        print(f"❌ CSV not found: {CSV}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(CSV)
    # scrub NaN, ∞ → empty string
    df = df.replace([np.inf, -np.inf], np.nan).fillna("")

    # 5) Open spreadsheet & get or create worksheet
    try:
        sh = gc.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        print("❌ Cannot open sheet:", e, file=sys.stderr)
        sys.exit(1)

    try:
        ws = sh.worksheet(SHEET_NAME)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(
            title=SHEET_NAME,
            rows=str(df.shape[0] + 10),
            cols=str(df.shape[1] + 5),
        )

    # 6) Prepare & push data
    data = [df.columns.tolist()] + df.values.tolist()
    ws.update(range_name="A1", values=data)

    print(f"✅ Uploaded {len(df)} rows to “{SHEET_NAME}” "
          f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ Fatal error:", e, file=sys.stderr)
        sys.exit(1)
