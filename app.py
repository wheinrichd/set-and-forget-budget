import streamlit as st
import pandas as pd
import requests
import time
import datetime

# --- APP LAYOUT CONFIGURATION ---
st.set_page_config(
    page_title="Dynamic Paycheck Horizon Console",
    page_icon="🔒",
    layout="wide"
)

# ⚠️ PASTE YOUR SECURE GOOGLE SHEET LINKS HERE INSIDE THE QUOTES:
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oFJyfxgVGPDx1kRkZlKI2a-aWFd3Dpln9Q6CA5sRZTk/edit?gid=1235427596#gid=1235427596"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaiAFHjaivojjtF1FEiZcb65n55TFiVQ5rK9hKCET130pbjxUMsscV1OtcZ0hJJsvA/exec"

# Premium Dark Command Center CSS Custom Stylesheet
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    div[data-testid="metric-container"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    h1, h2, h3, h4 { color: #f0f6fc !important; font-weight: 700; font-family: -apple-system, sans-serif; }
    
    /* Dynamic Paycheck Box Styling */
    .paycheck-window-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-top: 4px solid #58a6ff;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 5px;
    }
    
    .bill-alert-row {
        background-color: #21262d;
        padding: 6px 12px;
        margin-top: 4px;
        border-radius: 4px;
        border-left: 3px solid #ff7b72;
        display: flex;
        justify-content: space-between;
    }
    
    .slice-container {
        background-color: #1f242c;
        border-left: 4px solid #00e676;
        padding: 10px 14px;
        margin-bottom: 6px;
        border-radius: 6px;
    }
    .slice-container-paid {
        background-color: #14191f;
        border-left: 4px solid #30363d;
        padding: 10px 14px;
        margin-bottom: 6px;
        border-radius: 6px;
        opacity: 0.40;
    }
    .category-header {
        background-color: #21262d;
        padding: 6px 12px;
        border-radius: 6px;
        margin-top: 15px;
        color: #c9d1d9;
    }
    </style>
""", unsafe_allow_html=True)

# Helper Function: Feature 1 - Intelligent Due Date Calculator
def get_due_date_details(day_str, target_month_offset=0):
    try:
        due_day = int(''.join(c for c in day_str if c.isdigit()))
        today = datetime.datetime.now()
        
        target_month = today.month + target_month_offset
        target_year = today.year
        while target_month > 12:
            target_month -= 12
            target_year += 1
            
        try:
            target_date = datetime.datetime(target_year, target_month, due_day)
        except ValueError:
            next_m = datetime.datetime(target_year, target_month, 28) + datetime.timedelta(days=4)
            last_day = (next_m - datetime.timedelta(days=next_m.day)).day
            target_date = datetime.datetime(target_year, target_month, last_day)
            
        return target_date.date()
    except:
        return datetime.date.today()

# --- GOOGLE SHEET LIVE PARSING DATA ENGINE ---
def get_csv_download_url(sheet_url, sheet_name):
    try:
        if '/edit' in sheet_url: base_url = sheet_url.split('/edit')[0]
        elif '/pub' in sheet_url: base_url = sheet_url.split('/pub')[0]
        else: base_url = sheet_url.rstrip('/')
        return f"{base_url}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    except: return ""

def load_cloud_data():
    custom_expenses = []
    afterpay_ledger = []
    spending_log = []
    paid_slices = set()
    deleted_baseline = set()
    
    # Core Weekly Income Matrix Memory Defaults
    saved_weekly_pay = {0: 1200.0, 1: 1200.0, 2: 1200.0, 3: 1200.0}
    
    today = datetime.date.today()
    days_since_wednesday = (today.weekday() - 2) % 7
    current_wednesday = today - datetime.timedelta(days=days_since_wednesday)
    
    # Fetch 4-Week Saved Income Matrix
    try:
        url_inc = get_csv_download_url(GOOGLE_SHEET_URL, "weekly_income_memory")
        if url_inc:
            url_inc += f"&cache_bust={int(time.time())}"
            df_inc = pd.read_csv(url_inc)
            if len(df_inc) > 0:
                for _, row in df_inc.iterrows():
                    try:
                        wk_idx = int(row.iloc[0])
                        wk_val = float(str(row.iloc[1]).replace('$', '').replace(',', '').strip())
                        if wk_idx in saved_weekly_pay:
                            saved_weekly_pay[wk_idx] = wk_val
                    except: pass
    except: pass

    # Fetch Paid Slices Checklist
    try:
        url_ps = get_csv_download_url(GOOGLE_SHEET_URL, "paid_slices")
        if url_ps:
            url_ps += f"&cache_bust={int(time.time())}"
            df_ps = pd.read_csv(url_ps)
            if len(df_ps) > 0:
                for _, row in df_ps.iterrows():
                    try:
                        slice_name = str(row.iloc[0]).strip()
                        date_logged = datetime.datetime.strptime(str(row.iloc[1]).strip(),
