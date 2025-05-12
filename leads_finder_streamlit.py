
import streamlit as st
import requests
import re
import pandas as pd
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import os
import random
import time

BRAVE_API_KEY = "BSA38iIprdXXP87R1dZ2wCuG50ojMBz"
CSV_DB = "leads.csv"
EXCEL_EXPORT = "leads_export.xlsx"

def extract_emails_from_url(url):
    try:
        response = requests.get(url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text()
        emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        return list(set(emails))
    except:
        return []

def brave_search(query, api_key, count=5, offset=0):
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
    params = {"q": query, "count": count, "offset": offset}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        data = response.json()
        return [{
            "source": "Brave",
            "title": item.get("title"),
            "url": item.get("url"),
            "description": item.get("description", "")
        } for item in data.get("web", {}).get("results", [])]
    except Exception as e:
        return []

def ddg_search(query, max_results=5):
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "source": "DuckDuckGo",
                    "title": r.get("title"),
                    "url": r.get("href"),
                    "description": r.get("body", "")
                })
    except:
        pass
    return results

def generate_query_variants(base_query):
    salt = random.randint(1000, 9999)
    variants = [
        f"{base_query} site:.co.za",
        f"{base_query} contact email",
        f"{base_query} suppliers #{salt}"
    ]
    return variants

def smart_search(base_query, pages=5):
    results = []
    progress_area = st.empty()
    for i, variant in enumerate(generate_query_variants(base_query), 1):
        progress_area.info(f"Searching variant {i}/3: {variant}")
        for j in range(pages):
            offset = random.randint(0, 50)
            brave_results = brave_search(variant, BRAVE_API_KEY, count=5, offset=offset)
            results.extend(brave_results)
            time.sleep(1)
            if len(brave_results) < 3:
                ddg_results = ddg_search(variant, max_results=5)
                results.extend(ddg_results)
    progress_area.empty()
    return results

def filter_unique_domains(df):
    df["domain"] = df["email"].str.extract(r"@([a-zA-Z0-9.-]+)")
    df = df.drop_duplicates(subset="domain")
    return df.drop(columns=["domain"])

def append_leads_smart(leads, storage_file=CSV_DB):
    try:
        existing_df = pd.read_csv(storage_file)
    except FileNotFoundError:
        existing_df = pd.DataFrame(columns=["business_name", "url", "email", "description", "source"])
    combined = pd.concat([existing_df, pd.DataFrame(leads)], ignore_index=True)
    combined.drop_duplicates(subset=["email", "url"], inplace=True)
    filtered = filter_unique_domains(combined)
    filtered.to_csv(storage_file, index=False)
    return filtered

def export_to_excel_and_reset(csv_file=CSV_DB, excel_file=EXCEL_EXPORT):
    try:
        df = pd.read_csv(csv_file)
        df.to_excel(excel_file, index=False)
        df.iloc[0:0].to_csv(csv_file, index=False)
        return excel_file, len(df)
    except:
        return None, 0

def run_search_and_add(query, debug_box):
    results = smart_search(query)
    leads = []
    for r in results:
        emails = extract_emails_from_url(r["url"])
        if emails:
            debug_box.text(f"✅ Found {len(emails)} email(s) at {r['url']}")
        else:
            debug_box.text(f"❌ No email at {r['url']}")
        for email in emails:
            leads.append({
                "business_name": r["title"],
                "url": r["url"],
                "email": email,
                "description": r["description"],
                "source": r["source"]
            })
    return append_leads_smart(leads)

st.markdown("""
# **Leads Finder**
#### <span style='color:red;'>Powered by Proto Trading</span>
""", unsafe_allow_html=True)

menu = st.sidebar.selectbox("Choose an action", ["Run New Search", "View Database", "Export to Excel & Reset"])

if menu == "Run New Search":
    query = st.text_input("Enter search query", "gift wholesalers gauteng")
    if st.button("Search & Save Leads"):
        debug_box = st.empty()
        df = run_search_and_add(query, debug_box)
        debug_box.empty()
        st.success(f"Added {len(df)} unique leads to database.")
        st.dataframe(df.tail())

elif menu == "View Database":
    if os.path.exists(CSV_DB):
        df = pd.read_csv(CSV_DB)
        st.write(f"Current database has {len(df)} leads.")
        st.dataframe(df)
    else:
        st.warning("No database found.")

elif menu == "Export to Excel & Reset":
    file, count = export_to_excel_and_reset()
    if file:
        with open(file, "rb") as f:
            st.download_button(label="Download Excel File", data=f, file_name=file)
        st.success(f"Exported {count} leads and reset the database.")
    else:
        st.warning("No leads to export.")
