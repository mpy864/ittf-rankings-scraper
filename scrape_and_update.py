#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import sys
import requests, re, unicodedata
import pandas as pd
from bs4 import BeautifulSoup, Tag
from tqdm import tqdm
from urllib.parse import urljoin
from datetime import datetime, date
from dateutil.parser import parse as parse_dt

def main():
    # 1) Configuration
    ARCHIVE_URLS = [
        "https://www.ittf.com/ittf-table-tennis-world-ranking/",
        "https://ittf.com/ittf-table-tennis-world-ranking/"
    ]
    HEADERS = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }
    CUTOFF_DATE = date(2025, 6, 24)  # include Week 26 onward

    # pick working base URL
    archive = None
    for url in ARCHIVE_URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=5)
            resp.raise_for_status()
            archive = url
            break
        except requests.RequestException:
            continue
    if not archive:
        raise RuntimeError("Cannot reach ITTF archive URL")

    # 2) Helpers
    week_re = re.compile(r"^\d{4}\s+Week")
    def is_week_label(txt: str) -> bool:
        return bool(txt and week_re.match(txt.strip()))

    def parse_header_date(s: str) -> date:
        m = re.search(r'(\d{1,2}(?:st|nd|rd|th)?\s+\w+\.?\s+\d{4})', s)
        if not m:
            return None
        core = re.sub(r'(st|nd|rd|th)', '', m.group(1))
        try:
            return datetime.strptime(core, "%d %B %Y").date()
        except ValueError:
            return parse_dt(core, dayfirst=True, fuzzy=True).date()

    # 3) Scrape category links Week 26 onward
    session = requests.Session()
    page = session.get(archive, headers=HEADERS, timeout=10)
    page.raise_for_status()
    soup = BeautifulSoup(page.text, "html.parser")

    entries = []
    for header in soup.find_all(
        lambda tag: tag.name in ("h2","h3","p")
                    and is_week_label(tag.get_text(strip=True))
    ):
        raw = unicodedata.normalize("NFKC", header.get_text(strip=True))
        parts = re.split(r'\s*[–-]\s*', raw, maxsplit=1)
        if len(parts) != 2:
            continue
        week_lbl, date_part = parts[0].strip(), parts[1].strip()
        wd = parse_header_date(date_part)
        if not wd or wd < CUTOFF_DATE:
            continue

        for sib in header.find_next_siblings():
            txt = sib.get_text(strip=True) if isinstance(sib, Tag) else ""
            if is_week_label(txt):
                break
            if not isinstance(sib, Tag):
                continue
            for a in sib.find_all("a", href=True):
                link_text = a.get_text(strip=True)
                m = re.match(r"^(Men’s|Men's|Women’s|Women's|Mixed)\s+(.+)$", link_text, re.I)
                if m:
                    gender = m.group(1).replace("’","'").split("'")[0]
                    category = m.group(2).strip()
                else:
                    li = a.find_parent("li")
                    full = unicodedata.normalize(
                        "NFKC", li.get_text(" ", strip=True)
                    ) if li else ""
                    if ":" not in full:
                        continue
                    category = full.split(":",1)[0].strip()
                    gender = link_text
                url = urljoin(archive, a["href"].strip())
                entries.append({
                    "Week": week_lbl,
                    "Date": date_part,
                    "Category": category,
                    "Gender": gender,
                    "URL": url
                })

    # dedupe
    entries = [dict(t) for t in {tuple(e.items()) for e in entries}]

    # 4) Download & parse tables
    rows = []
    for e in tqdm(entries, desc="Fetching tables"):
        try:
            r2 = session.get(e["URL"], headers=HEADERS, timeout=10)
            r2.raise_for_status()
            tbls = pd.read_html(r2.text)
            if not tbls:
                continue
            df = tbls[0].iloc[:,:3].copy()
            df.columns = ["Ranking","Name","Association"]
            df["Week"], df["Date"], df["Category"], df["Gender"] = \
                e["Week"], e["Date"], e["Category"], e["Gender"]
            rows.append(df)
        except Exception:
            continue

    if not rows:
        print("⚠️ No new tables scraped.", file=sys.stderr)
        sys.exit(1)

    full_df = pd.concat(rows, ignore_index=True)[
        ["Week","Date","Category","Gender","Ranking","Name","Association"]
    ]

    # 5) Clean data
    full_df["Ranking"] = (
        full_df["Ranking"].astype(str)
               .str.extract(r"^(\d+)", expand=False)
    )
    full_df["Ranking"] = pd.to_numeric(full_df["Ranking"],
                                       errors="coerce").astype("Int64")
    full_df["Association"] = (
        full_df["Association"].astype(str)
               .str.replace(r"\s*[/&sol;]\s*", "/", regex=True)
    )

    # 6) Merge into master
    OLD_CSV = "ITTF_World_Rankings_2021-2025.csv"
    UPDATED_CSV = "ITTF_World_Rankings_2021-2025_updated.csv"
    if os.path.exists(OLD_CSV):
        old_df = pd.read_csv(OLD_CSV)
    else:
        old_df = pd.DataFrame(columns=full_df.columns)

    combined = pd.concat([full_df, old_df], ignore_index=True)
    combined.to_csv(UPDATED_CSV, index=False)

    # 7) Excel export
    XLSX = "ITTF_Master_Rankings.xlsx"
    with pd.ExcelWriter(XLSX, engine="xlsxwriter") as writer:
        combined.to_excel(writer, index=False, sheet_name="Rankings")
        ws = writer.sheets["Rankings"]
        ws.freeze_panes(1, 0)
        for i, col in enumerate(combined.columns):
            w = max(combined[col].astype(str).map(len).max(), len(col)) + 2
            ws.set_column(i, i, w)

    print("✅ Done.")
    print(f"• {UPDATED_CSV}")
    print(f"• {XLSX}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ Fatal error:", e, file=sys.stderr)
        sys.exit(1)
