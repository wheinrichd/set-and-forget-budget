import streamlit as st
import pandas as pd
import requests
import time
import datetime

# --- APP LAYOUT CONFIGURATION ---
st.set_page_config(
    page_title="Cloud Connected Set & Forget Console",
    page_icon="🔒",
    layout="wide"
)

# ⚠️ PASTE YOUR SECURE GOOGLE SHEET LINKS HERE INSIDE THE QUOTES:
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oFJyfxgVGPDx1kRkZlKI2a-aWFd3Dpln9Q6CA5sRZTk/edit?gid=0#gid=0"
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
    .increment-row {
        background-color: #1f242c;
        border-left: 4px solid #00e676;
        padding: 12px 16px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
    .ap-active-row {
        background-color: #211c27;
        border-left: 4px solid #ff5252;
        padding: 12px 16px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
    .category-header {
        background-color: #21262d;
        padding: 6px 12px;
        border-radius: 6px;
        margin-top: 15px;
        color: #c9d1d9;
    }
    .alert-banner {
        background-color: #2b2214;
        border-left: 4px solid #f1c40f;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 15px;
        color: #f39c12;
    }
    </style>
""", unsafe_allow_html=True)

# Helper Function: Feature 1 - Intelligent Due Date Calculator
def get_days_until_due(day_str):
    try:
        due_day = int(''.join(c for c in day_str if c.isdigit()))
        today = datetime.datetime.now()
        today_day = today.day
        if due_day >= today_day:
            return due_day - today_day
        else:
            next_month = today.replace(day=28) + datetime.timedelta(days=4)
            last_day_this_month = (next_month - datetime.timedelta(days=next_month.day)).day
            return (last_day_this_month - today_day) + due_day
    except:
        return 99

# --- GOOGLE SHEET LIVE PARSING DATA ENGINE ---
def get_csv_download_url(sheet_url, sheet_name):
    try:
        if '/edit' in sheet_url:
            base_url = sheet_url.split('/edit')[0]
        elif '/pub' in sheet_url:
            base_url = sheet_url.split('/pub')[0]
        else:
            base_url = sheet_url.rstrip('/')
        return f"{base_url}/export?format=csv&sheet={sheet_name}"
    except:
        return ""

def load_cloud_data():
    custom_expenses = []
    afterpay_ledger = []
    spending_log = []
    
    # 1. Fetch Custom Expenses
    try:
        url_ce = get_csv_download_url(GOOGLE_SHEET_URL, "custom_expenses")
        if url_ce:
            url_ce += f"&cache_bust={int(time.time())}"
            df_ce = pd.read_csv(url_ce)
            df_ce.columns = [str(c).strip().lower() for c in df_ce.columns]
            name_col = 'name' if 'name' in df_ce.columns else (df_ce.columns[0] if len(df_ce.columns) > 0 else None)
            val_col = 'val' if 'val' in df_ce.columns else ('value' if 'value' in df_ce.columns else ('amount' if 'amount' in df_ce.columns else None))
            freq_col = 'freq' if 'freq' in df_ce.columns else ('frequency' if 'frequency' in df_ce.columns else None)
            desc_col = 'desc' if 'desc' in df_ce.columns else ('description' if 'description' in df_ce.columns else None)
            day_col = 'day' if 'day' in df_ce.columns else None

            if name_col and val_col:
                df_ce = df_ce.dropna(subset=[name_col, val_col])
                for _, row in df_ce.iterrows():
                    try:
                        val_float = float(str(row[val_col]).replace('$', '').replace(',', '').strip())
                        freq_val = str(row[freq_col]).strip() if freq_col and pd.notna(row[freq_col]) else "Monthly"
                        desc_val = str(row[desc_col]).strip() if desc_col and pd.notna(row[desc_col]) else f"{freq_val} (Custom)"
                        day_val = str(row[day_col]).strip() if day_col and pd.notna(row[day_col]) else "Custom"
                        custom_expenses.append({"name": str(row[name_col]).strip(), "val": val_float, "desc": desc_val, "freq": freq_val, "day": day_val, "is_custom": True})
                    except: pass
    except: pass

    # 2. Fetch Afterpay Ledger
    try:
        url_ap = get_csv_download_url(GOOGLE_SHEET_URL, "afterpay_ledger")
        if url_ap:
            url_ap += f"&cache_bust={int(time.time())}"
            df_ap = pd.read_csv(url_ap)
            df_ap.columns = [str(c).strip().lower() for c in df_ap.columns]
            merchant_col = 'merchant' if 'merchant' in df_ap.columns else (df_ap.columns[0] if len(df_ap.columns) > 0 else None)
            cost_col = 'fortnightly cost' if 'fortnightly cost' in df_ap.columns else ('cost' if 'cost' in df_ap.columns else ('amount' if 'amount' in df_ap.columns else None))
            rem_col = 'remaining' if 'remaining' in df_ap.columns else None
            debt_col = 'total debt' if 'total debt' in df_ap.columns else ('debt' if 'debt' in df_ap.columns else None)
            
            if merchant_col and cost_col:
                df_ap = df_ap.dropna(subset=[merchant_col, cost_col])
                for _, row in df_ap.iterrows():
                    try:
                        cost_float = float(str(row[cost_col]).replace('$', '').replace(',', '').strip())
                        rem_int = int(float(str(row[rem_col]).strip())) if rem_col and pd.notna(row[rem_col]) else 4
                        debt_float = float(str(row[debt_col]).replace('$', '').replace(',', '').strip()) if debt_col and pd.notna(row[debt_col]) else cost_float * rem_int
                        afterpay_ledger.append({"Merchant": str(row[merchant_col]).strip(), "Fortnightly Cost": cost_float, "Remaining": rem_int, "Total Debt": debt_float})
                    except: pass
    except: pass

    # 3. Fetch Feature 4 Quick Spending Logs
    try:
        url_sl = get_csv_download_url(GOOGLE_SHEET_URL, "spending_log")
        if url_sl:
            url_sl += f"&cache_bust={int(time.time())}"
            df_sl = pd.read_csv(url_sl)
            df_sl.columns = [str(c).strip().lower() for c in df_sl.columns]
            if len(df_sl) > 0:
                for _, row in df_sl.iterrows():
                    try:
                        spending_log.append({"category": str(row.iloc[0]).strip(), "amount": float(str(row.iloc[1]).replace('$', ''))})
                    except: pass
    except: pass
        
    return {"custom_expenses": custom_expenses, "afterpay_ledger": afterpay_ledger, "spending_log": spending_log}

cloud_data = load_cloud_data()

# --- HARDCODED BASELINE BUDGET MATRIX ---
BASE_MONTHLY = [
    {"name": "GO credit", "val": 250.00, "day": "2nd"}, {"name": "STAN", "val": 22.00, "day": "4th"},
    {"name": "ExpressVPN", "val": 21.00, "day": "4th"}, {"name": "DSC", "val": 12.00, "day": "7th"},
    {"name": "Cba credit", "val": 302.00, "day": "8th"}, {"name": "AIA", "val": 44.00, "day": "8th"},
    {"name": "Telstra", "val": 461.00, "day": "8th"}, {"name": "Kindle", "val": 14.00, "day": "9th"},
    {"name": "Gamivo", "val": 7.00, "day": "9th"}, {"name": "Paramount", "val": 9.00, "day": "11th"},
    {"name": "Netflix", "val": 30.00, "day": "14th"}, {"name": "Appletv", "val": 16.00, "day": "15th"},
    {"name": "Prime", "val": 13.00, "day": "16th"}, {"name": "Humm90", "val": 10.00, "day": "16th"},
    {"name": "Spotify", "val": 16.00, "day": "17th"}, {"name": "Bupa", "val": 390.00, "day": "19th"},
    {"name": "NRMA Road Ass", "val": 22.00, "day": "20th"}, {"name": "NRMA comp", "val": 250.00, "day": "22nd"},
    {"name": "HomeContents", "val": 76.00, "day": "22nd"}, {"name": "Azora", "val": 15.00, "day": "22nd"},
    {"name": "Afterpayplus", "val": 10.00, "day": "23rd"}, {"name": "Microsoft", "val": 20.00, "day": "26th"},
    {"name": "Disney+", "val": 25.00, "day": "28th"}, {"name": "Binge", "val": 18.00, "day": "29th"},
    {"name": "Zip", "val": 100.00, "day": "30th"}
]

BASE_WEEKLY = [
    {"name": "Emergency Fund", "val": 100.00, "desc": "Weekly (Wed)", "freq": "Weekly"},
    {"name": "Church", "val": 170.00, "desc": "Weekly (Wed)", "freq": "Weekly"},
    {"name": "Fuel Buffer", "val": 100.00, "desc": "Weekly Allocation", "freq": "Weekly"},
    {"name": "Grocery Buffer", "val": 150.00, "desc": "Weekly Allocation", "freq": "Weekly"},
    {"name": "Rent (Cambridge)", "val": 480.00, "desc": "Weekly (Fri)", "freq": "Weekly"},
    {"name": "Gym", "val": 91.00, "desc": "Fortnightly (Wed)", "freq": "Fortnightly"},
    {"name": "Isuzu mux", "val": 714.00, "desc": "Fortnightly (Wed)", "freq": "Fortnightly"},
    {"name": "TAX", "val": 65.00, "desc": "Fortnightly (Wed)", "freq": "Fortnightly"}
]

BASE_QUARTERLY = [{"name": "Water", "val": 100.00, "desc": "Quarterly"}, {"name": "Electricity", "val": 550.00, "desc": "Quarterly"}]
BASE_YEARLY = [
    {"name": "NRMA CTP", "val": 305.00, "desc": "6-Monthly (Nov)", "freq": "6-Monthly"},
    {"name": "CAR REGO", "val": 335.00, "desc": "6-Monthly (Nov)", "freq": "6-Monthly"},
    {"name": "Costco", "val": 60.00, "desc": "Yearly (30 Apr)", "freq": "Yearly"},
    {"name": "PSPLUS", "val": 215.00, "desc": "Yearly (18 Aug)", "freq": "Yearly"},
    {"name": "Mccafe", "val": 150.00, "desc": "Yearly (16 Oct)", "freq": "Yearly"}
]

st.session_state.monthly_bills = list(BASE_MONTHLY)
st.session_state.weekly_bills = list(BASE_WEEKLY)
st.session_state.quarterly_bills = list(BASE_QUARTERLY)
st.session_state.yearly_bills = list(BASE_YEARLY)
st.session_state.afterpay_ledger = cloud_data["afterpay_ledger"]

for item in cloud_data["custom_expenses"]:
    if item["freq"] in ["Weekly", "Fortnightly"]: st.session_state.weekly_bills.append(item)
    elif item["freq"] == "Monthly": st.session_state.monthly_bills.append(item)
    elif item["freq"] == "Quarterly": st.session_state.quarterly_bills.append(item)
    elif item["freq"] in ["6-Monthly", "Yearly"]: st.session_state.yearly_bills.append(item)

# --- DYNAMIC CALCULATOR LAUNCH ---
sum_fixed_monthly = sum((b["val"] * 12) / 52 for b in st.session_state.monthly_bills)
sum_fixed_weekly = sum(b["val"] if b["freq"] == "Weekly" else b["val"] / 2 for b in st.session_state.weekly_bills)
sum_utilities = sum(b["val"] / 13 for b in st.session_state.quarterly_bills)
sum_strategic_yearly = sum((b["val"] / 26) if b["freq"] == "6-Monthly" else (b["val"] / 52) for b in st.session_state.yearly_bills)
total_ap_weekly_impact = sum(plan["Fortnightly Cost"] / 2 for plan in st.session_state.afterpay_ledger)

total_weekly_sum = sum_fixed_monthly + sum_fixed_weekly + sum_utilities + sum_strategic_yearly + total_ap_weekly_impact

# --- INTERACTIVE SIDEBAR & FEATURE 5 INTEL TOGGLE ---
st.sidebar.title("🔒 Set & Forget Portal")
user_income = st.sidebar.number_input("Wednesday Take-Home Pay ($)", min_value=0.0, value=2200.0, step=50.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🚀 Feature 5: Wealth Mode")
wealth_mode = st.sidebar.toggle("Activate 'Safe-To-Save' Targets")
extra_savings_target = 0.0
if wealth_mode:
    extra_savings_target = st.sidebar.slider("Extra High-Yield Savings Push ($/wk)", 0, 500, 200, step=25)

st.title("🛡️ Automated Bills Command Center")

# --- FEATURE 1: DUE THIS WEEK MICRO-ALERTS ---
upcoming_bills = [b for b in BASE_MONTHLY if 0 <= get_days_until_due(b["day"]) <= 7]
if upcoming_bills:
    alert_text = "⏰ **Due Within 7 Days:** " + ", ".join([f"{b['name']} (${b['val']:.0f} on the {b['day']})" for b in upcoming_bills])
    st.markdown(f"<div class='alert-banner'>{alert_text}</div>", unsafe_allow_html=True)

st.markdown("---")

leftover_cash = user_income - total_weekly_sum - extra_savings_target

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Wednesday Paycheck", f"${user_income:,.2f}", "Verified Total Income In")
with col2
