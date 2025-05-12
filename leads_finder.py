
import os
import requests
import re
import pandas as pd
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# Store your API key here (auto-loaded each time)
BRAVE_API_KEY = "BSA38iIprdXXP87R1dZ2wCuG50ojMBz"
CSV_DB = "leads.csv"
EXCEL_EXPORT = "leads_export.xlsx"

def extract_emails_from_url(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text()
        emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        return list(set(emails))
    except:
        return []

def brave_search(query, api_key, count=10):
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": query,
        "count": count
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        return [{
            "source": "Brave",
            "title": item.get("title"),
            "url": item.get("url"),
            "description": item.get("description", "")
        } for item in data.get("web", {}).get("results", [])]
    except:
        return []

def ddg_search(query, max_results=10):
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

def smart_search(query, count=10, fallback_threshold=3):
    brave_results = brave_search(query, BRAVE_API_KEY, count)
    if len(brave_results) < fallback_threshold:
        ddg_results = ddg_search(query, max_results=count)
        return brave_results + ddg_results
    else:
        return brave_results

def append_leads_smart(leads, storage_file=CSV_DB):
    try:
        existing_df = pd.read_csv(storage_file)
    except FileNotFoundError:
        existing_df = pd.DataFrame(columns=["business_name", "url", "email", "description", "source"])

    combined = pd.concat([existing_df, pd.DataFrame(leads)], ignore_index=True)
    combined.drop_duplicates(subset=["email", "url"], inplace=True)
    combined.to_csv(storage_file, index=False)
    print(f"Database now contains {len(combined)} unique leads.")

def export_to_excel_and_reset(csv_file=CSV_DB, excel_file=EXCEL_EXPORT):
    try:
        df = pd.read_csv(csv_file)
        df.to_excel(excel_file, index=False)
        print(f"Exported {len(df)} leads to {excel_file}")
        df.iloc[0:0].to_csv(csv_file, index=False)
        print("Lead database reset. Ready for new searches.")
    except:
        print("No data found to export.")

def run_search_and_add(query):
    results = smart_search(query)
    leads = []
    for r in results:
        emails = extract_emails_from_url(r["url"])
        for email in emails:
            leads.append({
                "business_name": r["title"],
                "url": r["url"],
                "email": email,
                "description": r["description"],
                "source": r["source"]
            })
    append_leads_smart(leads)

def display_header():
    print("\033[1mLeads Finder\033[0m")  # bold black title
    print("\033[91mPowered by Proto Trading\033[0m\n")  # red subtitle

def main():
    display_header()
    while True:
        print("\nMenu:")
        print("1. Run new search and add leads")
        print("2. Export to Excel and reset database")
        print("3. View database size")
        print("4. Exit")
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            q = input("Enter your search query: ").strip()
            run_search_and_add(q)
        elif choice == "2":
            export_to_excel_and_reset()
        elif choice == "3":
            try:
                df = pd.read_csv(CSV_DB)
                print(f"Current database has {len(df)} leads.")
            except:
                print("Database is empty.")
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()
