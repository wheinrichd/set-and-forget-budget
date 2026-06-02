import streamlit as st
import pandas as pd
import requests
import time

# --- APP LAYOUT CONFIGURATION ---
st.set_page_config(
    page_title="Cloud Connected Set & Forget Console",
    page_icon="🔒",
    layout="wide"
)

# ⚠️ PASTE YOUR SECURE GOOGLE SHEET LINKS HERE INSIDE THE QUOTES:
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1oFJyfxgVGPDx1kRkZlKI2a-aWFd3Dpln9Q6CA5sRZTk/edit?gid=0#gid=0"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaiAFHjaivojjtF1FEiZcb65n55TFiVQ5rK9hKCET130pbjxUMsscV1OtcZ0hJJsvA/exec"

# Custom Premium Dark Theme CSS Stylesheet
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
    </style>
""", unsafe_allow_html=True)

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
    
    # 1. Fetch & Process Custom Expenses Tab
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
                        
                        custom_expenses.append({
                            "name": str(row[name_col]).strip(),
                            "val": val_float,
                            "desc": desc_val,
                            "freq": freq_val,
                            "day": day_val,
                            "is_custom": True
                        })
                    except:
                        pass
    except:
        pass

    # 2. Fetch & Process Afterpay Ledger Tab
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
                        
                        afterpay_ledger.append({
                            "Merchant": str(row[merchant_col]).strip(),
                            "Fortnightly Cost": cost_float,
                            "Remaining": rem_int,
                            "Total Debt": debt_float
                        })
                    except:
                        pass
    except:
        pass
        
    return {"custom_expenses": custom_expenses, "afterpay_ledger": afterpay_ledger}

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
    {"name": "Fuel", "val": 100.00, "desc": "Weekly (Pump)", "freq": "Weekly"},
    {"name": "Rent (Cambridge)", "val": 480.00, "desc": "Weekly (Fri)", "freq": "Weekly"},
    {"name": "Gym", "val": 91.00, "desc": "Fortnightly (Wed)", "freq": "Fortnightly"},
    {"name": "Isuzu mux", "val": 714.00, "desc": "Fortnightly (Wed)", "freq": "Fortnightly"},
    {"name": "TAX", "val": 65.00, "desc": "Fortnightly (Wed)", "freq": "Fortnightly"}
]

BASE_QUARTERLY = [
    {"name": "Water", "val": 100.00, "desc": "Quarterly"},
    {"name": "Electricity", "val": 550.00, "desc": "Quarterly"}
]

BASE_YEARLY = [
    {"name": "NRMA CTP", "val": 305.00, "desc": "6-Monthly (Nov)", "freq": "6-Monthly"},
    {"name": "CAR REGO", "val": 335.00, "desc": "6-Monthly (Nov)", "freq": "6-Monthly"},
    {"name": "Costco", "val": 60.00, "desc": "Yearly (30 Apr)", "freq": "Yearly"},
    {"name": "PSPLUS", "val": 215.00, "desc": "Yearly (18 Aug)", "freq": "Yearly"},
    {"name": "Mccafe", "val": 150.00, "desc": "Yearly (16 Oct)", "freq": "Yearly"}
]

# Amalgamate baseline rows with pulled Google cloud records
st.session_state.monthly_bills = list(BASE_MONTHLY)
st.session_state.weekly_bills = list(BASE_WEEKLY)
st.session_state.quarterly_bills = list(BASE_QUARTERLY)
st.session_state.yearly_bills = list(BASE_YEARLY)
st.session_state.afterpay_ledger = cloud_data["afterpay_ledger"]

for item in cloud_data["custom_expenses"]:
    if item["freq"] == "Weekly" or item["freq"] == "Fortnightly":
        st.session_state.weekly_bills.append(item)
    elif item["freq"] == "Monthly":
        st.session_state.monthly_bills.append(item)
    elif item["freq"] == "Quarterly":
        st.session_state.quarterly_bills.append(item)
    elif item["freq"] == "6-Monthly" or item["freq"] == "Yearly":
        st.session_state.yearly_bills.append(item)

# --- DYNAMIC CALCULATOR MATHEMATICAL LAUNCH ---
total_weekly_sum = 0.0

for item in st.session_state.monthly_bills:
    total_weekly_sum += (item["val"] * 12) / 52

for item in st.session_state.weekly_bills:
    if item["freq"] == "Weekly":
        total_weekly_sum += item["val"]
    elif item["freq"] == "Fortnightly":
        total_weekly_sum += item["val"] / 2

for item in st.session_state.quarterly_bills:
    total_weekly_sum += item["val"] / 13

for item in st.session_state.yearly_bills:
    if item["freq"] == "6-Monthly":
        total_weekly_sum += item["val"] / 26
    elif item["freq"] == "Yearly":
        total_weekly_sum += item["val"] / 52

total_ap_weekly_impact = sum(plan["Fortnightly Cost"] / 2 for plan in st.session_state.afterpay_ledger)
total_weekly_sum += total_ap_weekly_impact

# --- INTERACTIVE CONTROL PANEL ---
st.sidebar.title("🔒 Set & Forget Portal")
user_income = st.sidebar.number_input("Wednesday Take-Home Pay ($)", min_value=0.0, value=2200.0, step=50.0)

st.title("🛡️ Automated Bills Command Center")
st.markdown("### Live Cloud-Synchronized 'Set & Forget' Architecture")
st.markdown("---")

leftover_cash = user_income - total_weekly_sum

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Wednesday Paycheck", f"${user_income:,.2f}", "Total Revenue In")
with col2:
    ap_label = "Synchronized to Google Sheets Database"
    st.metric("Set & Forget Bill Transfer", f"${total_weekly_sum:,.2f}", ap_label, delta_color="inverse")
with col3:
    color_state = "normal" if leftover_cash >= 0 else "inverse"
    st.metric("Leftover Personal Cash", f"${leftover_cash:,.2f}", "Safe Spending Balance" if leftover_cash >= 0 else "Income Deficit Warning", delta_color=color_state)

st.markdown("---")

tab_segments, tab_add_expense, tab_afterpay = st.tabs([
    "🗂️ Weekly Increment Slices", 
    "➕ Add New Custom Expense (Cloud Saved)", 
    "🛍️ Live Afterpay Intercept Guard"
])

with tab_segments:
    st.markdown("### Active Weekly Target Slices")
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("<div class='category-header'><h4>🗓️ Fixed Monthly Slices (Weekly Value)</h4></div>", unsafe_allow_html=True)
        for b in st.session_state.monthly_bills:
            w_val = (b['val'] * 12) / 52
            is_custom = " ☁️" if "is_custom" in b else ""
            st.markdown(f"<div class='increment-row'><b>{b['name']}{is_custom}</b><br>Full Bill: ${b['val']:,.2f} | <span style='color:#00e676; font-weight:bold;'>Weekly Segment: ${w_val:,.2f}/wk</span></div>", unsafe_allow_html=True)
    with col_right:
        st.markdown("<div class='category-header'><h4>⏳ Weekly & Fortnightly Base Slices</h4></div>", unsafe_allow_html=True)
        for b in st.session_state.weekly_bills:
            w_val = b['val'] if b['freq'] == 'Weekly' else b['val'] / 2
            is_custom = " ☁️" if "is_custom" in b else ""
            st.markdown(f"<div class='increment-row'><b>{b['name']}{is_custom}</b> ({b['desc']})<br>Full Bill: ${b['val']:,.2f} | <span style='color:#00e676; font-weight:bold;'>Weekly Segment: ${w_val:,.2f}/wk</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='category-header'><h4>⚡ Quarterly Utility Slices</h4></div>", unsafe_allow_html=True)
        for b in st.session_state.quarterly_bills:
            w_val = b['val'] / 13
            is_custom = " ☁️" if "is_custom" in b else ""
            st.markdown(f"<div class='increment-row'><b>{b['name']}{is_custom}</b> ({b['desc']})<br>Full Bill: ${b['val']:,.2f} | <span style='color:#00e676; font-weight:bold;'>Weekly Segment: ${w_val:,.2f}/wk</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='category-header'><h4>🦅 6-Month & Yearly Strategic Slices</h4></div>", unsafe_allow_html=True)
        for b in st.session_state.yearly_bills:
            w_val = (b['val'] / 26) if b['freq'] == '6-Monthly' else (b['val'] / 52)
            is_custom = " ☁️" if "is_custom" in b else ""
            st.markdown(f"<div class='increment-row'><b>{b['name']}{is_custom}</b> ({b['desc']})<br>Full Bill: ${b['val']:,.2f} | <span style='color:#00e676; font-weight:bold;'>Weekly Segment: ${w_val:,.2f}/wk</span></div>", unsafe_allow_html=True)

with tab_add_expense:
    st.markdown("### ➕ Google Sheet Custom Expense Injection")
    with st.form("custom_expense_form", clear_on_submit=True):
        new_name = st.text_input("Expense Description Name")
        col_f, col_a = st.columns(2)
        new_freq = col_f.selectbox("Billing Cycle Frequency", ["Weekly", "Fortnightly", "Monthly", "Quarterly", "6-Monthly", "Yearly"])
        new_amt = col_a.number_input("Full Bill Amount ($)", min_value=0.0, step=10.0)
        
        if st.form_submit_button("Upload to Google Sheets"):
            if new_name and new_amt > 0:
                desc_str = f"{new_freq} (Custom)"
                payload = {
                    "action": "add",
                    "sheetName": "custom_expenses",
                    "rowData": [new_name, new_amt, desc_str, new_freq, "Custom"]
                }
                try:
                    response = requests.post(APPS_SCRIPT_URL, json=payload)
                    st.success(f"Successfully pinned to Google Cloud!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Network error linking data: {e}")

    # Display list of active custom expenses with custom row-by-row deletion buttons
    if cloud_data["custom_expenses"]:
        st.markdown("<div class='category-header'><h4>☁️ Manage / Delete Active Custom Expenses</h4></div>", unsafe_allow_html=True)
        for item in cloud_data["custom_expenses"]:
            c_left, c_right = st.columns([4, 1])
            with c_left:
                st.markdown(f"🔹 **{item['name']}** | Full Bill: ${item['val']:,.2f} ({item['freq']})")
            with c_right:
                if st.button("❌ Remove", key=f"del_ce_{item['name']}"):
                    del_payload = {"action": "delete", "sheetName": "custom_expenses", "targetName": item['name']}
                    try:
                        requests.post(APPS_SCRIPT_URL, json=del_payload)
                        st.success(f"Erased {item['name']}!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Link error: {e}")

with tab_afterpay:
    st.markdown("### Interactive Afterpay Registry")
    with st.form("ap_entry_form", clear_on_submit=True):
        ap_merchant = st.text_input("Store Name / Item Description")
        col_x, col_y = st.columns(2)
        ap_fortnightly = col_x.number_input("Fortnightly Installment Amount ($)", min_value=0.0, step=5.0)
        ap_remaining = col_y.number_input("Payments Remaining", min_value=1, max_value=4, value=4, step=1)
        
        if st.form_submit_button("Lock Plan to Google Sheets"):
            if ap_merchant and ap_fortnightly > 0:
                payload = {
                    "action": "add",
                    "sheetName": "afterpay_ledger",
                    "rowData": [ap_merchant, ap_fortnightly, ap_remaining, ap_fortnightly * ap_remaining]
                }
                try:
                    requests.post(APPS_SCRIPT_URL, json=payload)
                    st.success("Afterpay order successfully committed to cloud ledger!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Link error: {e}")

    if st.session_state.afterpay_ledger:
        st.markdown("<div class='category-header'><h4>🛍️ Active Afterpay Orders (Tap to Clear)</h4></div>", unsafe_allow_html=True)
        for plan in st.session_state.afterpay_ledger:
            c_left, c_right = st.columns([4, 1])
            with c_left:
                st.markdown(f"""
                    <div class='ap-active-row' style='margin-bottom:0px;'>
                        <b>{plan['Merchant']}</b> | Total Debt: <b>${plan['Total Debt']:,.2f}</b><br>
                        Fortnightly Cost: ${plan['Fortnightly Cost']:,.2f} ({plan['Remaining']} left) | 
                        <span style='color:#ff5252; font-weight:bold;'>Weekly Impact: ${plan['Fortnightly Cost']/2:,.2f}/wk</span>
                    </div>
                """, unsafe_allow_html=True)
            with c_right:
                st.write("") # Quick padding layout shift to align button vertically
                if st.button("❌ Clear Plan", key=f"del_ap_{plan['Merchant']}"):
                    del_payload = {"action": "delete", "sheetName": "afterpay_ledger", "targetName": plan['Merchant']}
                    try:
                        requests.post(APPS_SCRIPT_URL, json=del_payload)
                        st.success(f"Cleared {plan['Merchant']}!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Link error: {e}")
