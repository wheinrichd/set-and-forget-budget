import streamlit as st
import pandas as pd
import requests
import time
import datetime

# --- APP LAYOUT CONFIGURATION ---
st.set_page_config(
    page_title="Cloud Connected Paycheck Console",
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
        margin-bottom: 15px;
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
        
        # Shift months forward if looking into future windows
        target_month = today.month + target_month_offset
        target_year = today.year
        while target_month > 12:
            target_month -= 12
            target_year += 1
            
        try:
            target_date = datetime.datetime(target_year, target_month, due_day)
        except ValueError:
            # Handle month-end wrapping safely
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
    persistent_income = 0.0
    
    today = datetime.date.today()
    days_since_wednesday = (today.weekday() - 2) % 7
    current_wednesday = today - datetime.timedelta(days=days_since_wednesday)
    
    # 0. Fetch Persistent Paycheck Settings
    try:
        url_inc = get_csv_download_url(GOOGLE_SHEET_URL, "income_memory")
        if url_inc:
            url_inc += f"&cache_bust={int(time.time())}"
            df_inc = pd.read_csv(url_inc)
            if len(df_inc) > 0 and pd.notna(df_inc.iloc[0, 0]):
                persistent_income = float(str(df_inc.iloc[0, 0]).replace('$', '').replace(',', '').strip())
    except: pass

    # 1. Fetch Paid Slices Checklist Status
    try:
        url_ps = get_csv_download_url(GOOGLE_SHEET_URL, "paid_slices")
        if url_ps:
            url_ps += f"&cache_bust={int(time.time())}"
            df_ps = pd.read_csv(url_ps)
            if len(df_ps) > 0:
                for _, row in df_ps.iterrows():
                    try:
                        slice_name = str(row.iloc[0]).strip()
                        date_logged = datetime.datetime.strptime(str(row.iloc[1]).strip(), "%Y-%m-%d").date()
                        if date_logged >= current_wednesday:
                            paid_slices.add(slice_name)
                    except: pass
    except: pass

    # 2. Fetch Muted Baseline Subscriptions
    try:
        url_db = get_csv_download_url(GOOGLE_SHEET_URL, "deleted_baseline")
        if url_db:
            url_db += f"&cache_bust={int(time.time())}"
            df_db = pd.read_csv(url_db)
            if len(df_db) > 0:
                for _, row in df_db.iterrows():
                    try: deleted_baseline.add(str(row.iloc[0]).strip())
                    except: pass
    except: pass

    # 3. Fetch Custom Expenses
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
                        day_val = str(row[day_col]).strip() if day_col and pd.notna(row[day_col]) else "1st"
                        custom_expenses.append({"name": str(row[name_col]).strip(), "val": val_float, "desc": desc_val, "freq": freq_val, "day": day_val, "is_custom": True})
                    except: pass
    except: pass

    # 4. Fetch Afterpay Ledger
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

    # 5. Fetch Quick Spending Logs
    try:
        url_sl = get_csv_download_url(GOOGLE_SHEET_URL, "spending_log")
        if url_sl:
            url_sl += f"&cache_bust={int(time.time())}"
            df_sl = pd.read_csv(url_sl)
            if len(df_sl) > 0:
                cols = [str(c).strip().lower() for c in df_sl.columns]
                cat_idx = 0
                amt_idx = 1
                for idx, col in enumerate(cols):
                    if 'cat' in col or 'type' in col: cat_idx = idx
                    if 'amt' in col or 'val' in col or 'cost' in col or 'amount' in col: amt_idx = idx
                
                for _, row in df_sl.iterrows():
                    try:
                        cat_str = str(row.iloc[cat_idx]).strip()
                        val_str = str(row.iloc[amt_idx]).replace('$', '').replace(',', '').strip()
                        if val_str.lower() in ['amount', 'val', 'value', 'cost'] or cat_str.lower() in ['category', 'name']: continue
                        spending_log.append({"category": cat_str, "amount": float(val_str)})
                    except: pass
    except: pass
        
    return {"custom_expenses": custom_expenses, "afterpay_ledger": afterpay_ledger, "spending_log": spending_log, "paid_slices": paid_slices, "deleted_baseline": deleted_baseline, "persistent_income": persistent_income}

cloud_data = load_cloud_data()

# --- HARDCODED BASELINE BUDGET MATRIX ---
RAW_MONTHLY = [
    {"name": "GO credit", "val": 250.00, "day": "2nd"}, {"name": "STAN", "val": 22.00, "day": "4th"},
    {"name": "ExpressVPN", "val": 21.00, "day": "4th"}, {"name": "Prime", "val": 13.00, "day": "4th"},
    {"name": "DSC", "val": 12.00, "day": "7th"}, {"name": "Cba credit", "val": 302.00, "day": "8th"}, 
    {"name": "AIA", "val": 44.00, "day": "8th"}, {"name": "Telstra", "val": 461.00, "day": "8th"}, 
    {"name": "Kindle", "val": 14.00, "day": "9th"}, {"name": "Gamivo", "val": 7.00, "day": "9th"}, 
    {"name": "Paramount", "val": 9.00, "day": "11th"}, {"name": "Netflix", "val": 30.00, "day": "14th"}, 
    {"name": "Appletv", "val": 16.00, "day": "15th"}, {"name": "Humm90", "val": 10.00, "day": "16th"},
    {"name": "Spotify", "val": 16.00, "day": "17th"}, {"name": "Bupa", "val": 390.00, "day": "19th"},
    {"name": "NRMA Road Ass", "val": 22.00, "day": "20th"}, {"name": "NRMA comp", "val": 250.00, "day": "22nd"},
    {"name": "HomeContents", "val": 76.00, "day": "22nd"}, {"name": "Azora", "val": 15.00, "day": "22nd"},
    {"name": "Afterpayplus", "val": 10.00, "day": "23rd"}, {"name": "Microsoft", "val": 20.00, "day": "26th"},
    {"name": "Disney+", "val": 25.00, "day": "28th"}, {"name": "Binge", "val": 18.00, "day": "29th"},
    {"name": "Zip", "val": 100.00, "day": "30th"}
]

RAW_WEEKLY = [
    {"name": "Emergency Fund", "val": 100.00, "desc": "Weekly (Wed)", "freq": "Weekly"},
    {"name": "Church", "val": 170.00, "desc": "Weekly (Wed)", "freq": "Weekly"},
    {"name": "Fuel Buffer", "val": 100.00, "desc": "Weekly Allocation", "freq": "Weekly"},
    {"name": "Grocery Buffer", "val": 150.00, "desc": "Weekly Allocation", "freq": "Weekly"},
    {"name": "Rent (Cambridge)", "val": 480.00, "desc": "Weekly (Fri)", "freq": "Weekly"},
    {"name": "Gym", "val": 91.00, "desc": "Fortnightly (Wed)", "freq": "Fortnightly"},
    {"name": "Isuzu mux", "val": 714.00, "desc": "Fortnightly (Wed)", "freq": "Fortnightly"},
    {"name": "TAX", "val": 65.00, "desc": "Fortnightly (Wed)", "freq": "Fortnightly"}
]

RAW_QUARTERLY = [{"name": "Water", "val": 100.00, "desc": "Quarterly"}, {"name": "Electricity", "val": 550.00, "desc": "Quarterly"}]
RAW_YEARLY = [
    {"name": "NRMA CTP", "val": 305.00, "desc": "6-Monthly (Nov)", "freq": "6-Monthly"},
    {"name": "CAR REGO", "val": 335.00, "desc": "6-Monthly (Nov)", "freq": "6-Monthly"},
    {"name": "Costco", "val": 60.00, "desc": "Yearly (30 Apr)", "freq": "Yearly"},
    {"name": "PSPLUS", "val": 215.00, "desc": "Yearly (18 Aug)", "freq": "Yearly"},
    {"name": "Mccafe", "val": 150.00, "desc": "Yearly (16 Oct)", "freq": "Yearly"}
]

BASE_MONTHLY = [b for b in RAW_MONTHLY if b["name"] not in cloud_data["deleted_baseline"]]
BASE_WEEKLY = [b for b in RAW_WEEKLY if b["name"] not in cloud_data["deleted_baseline"]]
BASE_QUARTERLY = [b for b in RAW_QUARTERLY if b["name"] not in cloud_data["deleted_baseline"]]
BASE_YEARLY = [b for b in RAW_YEARLY if b["name"] not in cloud_data["deleted_baseline"]]

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

# Sinking Fund Structural Calculations
sum_fixed_monthly = sum((b["val"] * 12) / 52 for b in st.session_state.monthly_bills)
sum_fixed_weekly = sum(b["val"] if b["freq"] == "Weekly" else b["val"] / 2 for b in st.session_state.weekly_bills)
sum_utilities = sum(b["val"] / 13 for b in st.session_state.quarterly_bills)
sum_strategic_yearly = sum((b["val"] / 26) if b["freq"] == "6-Monthly" else (b["val"] / 52) for b in st.session_state.yearly_bills)
total_ap_weekly_impact = sum(plan["Fortnightly Cost"] / 2 for plan in st.session_state.afterpay_ledger)

total_weekly_sum = sum_fixed_monthly + sum_fixed_weekly + sum_utilities + sum_strategic_yearly + total_ap_weekly_impact

# --- PERMANENT MEMORY INTERACTIVE SIDEBAR ---
st.sidebar.title("🔒 Set & Forget Portal")

user_income = st.sidebar.number_input(
    "Wednesday Take-Home Pay ($)", 
    min_value=0.0, 
    value=cloud_data["persistent_income"], 
    step=50.0
)

# If the user edits their paycheck, instantly commit it to Google Sheets sheet 'income_memory'
if user_income != cloud_data["persistent_income"]:
    requests.post(APPS_SCRIPT_URL, json={"action": "clear_all_rows", "sheetName": "income_memory"})
    requests.post(APPS_SCRIPT_URL, json={"action": "add", "sheetName": "income_memory", "rowData": [user_income]})
    st.rerun()

st.title("🛡️ 4-Week Paycheck Horizon Matrix")
st.caption("Tracking exact calendar obligations week-by-week from Wednesday to Tuesday.")

# --- CALENDAR WINDOW MATRIX CALCULATOR ---
today = datetime.date.today()
days_since_wed = (today.weekday() - 2) % 7
wed0 = today - datetime.timedelta(days=days_since_wed)

windows = []
for i in range(4):
    start_w = wed0 + datetime.timedelta(weeks=i)
    end_t = start_w + datetime.timedelta(days=6)
    windows.append((start_w, end_t))

# Evaluate full bill targets landing inside each window
window_bills = [[], [], [], []]

# Map Monthly Bills
for b in st.session_state.monthly_bills:
    for offset in [0, 1]:
        d_date = get_due_date_details(b["day"], target_month_offset=offset)
        for idx, (ws_date, we_date) in enumerate(windows):
            if ws_date <= d_date <= we_date:
                window_bills[idx].append({"name": b["name"], "val": b["val"], "type": "Full Monthly Bill"})

# Map Weekly/Fortnightly Obligations
for idx, (ws_date, we_date) in enumerate(windows):
    for b in st.session_state.weekly_bills:
        if b["freq"] == "Weekly":
            window_bills[idx].append({"name": b["name"], "val": b["val"], "type": "Weekly Outflow"})
        else: # Fortnightly
            if idx % 2 == 0:
                window_bills[idx].append({"name": b["name"], "val": b["val"], "type": "Fortnightly Hit"})

# Map Afterpay Ledger
for plan in st.session_state.afterpay_ledger:
    window_bills[0].append({"name": f"🛍️ AP: {plan['Merchant']}", "val": plan["Fortnightly Cost"], "type": "Afterpay Installment"})
    window_bills[2].append({"name": f"🛍️ AP: {plan['Merchant']}", "val": plan["Fortnightly Cost"], "type": "Afterpay Installment"})

# --- DISPLAY THE 4-WEEK PAYCHECK MATRICES ---
cols_matrix = st.columns(4)
for i in range(4):
    ws_date, we_date = windows[i]
    with cols_matrix[i]:
        st.markdown(f"""
        <div class="paycheck-window-card">
            <h4>Week {i+1} Paycheck</h4>
            <span style="color: #8b949e; font-size: 0.85em;">📅 {ws_date.strftime('%d %b')} - {we_date.strftime('%d %b')}</span>
        </div>
        """, unsafe_allow_html=True)
        
        full_bills_sum = sum(b["val"] for b in window_bills[i])
        net_leftover = user_income - full_bills_sum
        
        st.metric(label="Total Owed Full", value=f"${full_bills_sum:,.2f}")
        if net_leftover >= 0:
            st.success(f"Leftover: ${net_leftover:,.2f}")
        else:
            st.error(f"Shortfall: ${net_leftover:,.2f}")
            
        st.write("---")
        for item in window_bills[i]:
            st.markdown(f"""
            <div class="bill-alert-row">
                <span>{item['name']}</span>
                <span style="font-weight: bold;">${item['val']:.0f}</span>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

tab_segments, tab_spend_track, tab_add_expense, tab_afterpay = st.tabs([
    "🗂️ Weekly Segment Core Reference", 
    "💰 Fuel & Grocery Loggers",
    "➕ Add New Custom Expense", 
    "🛍️ Afterpay Intercept Guard"
])

def render_slice_item(name_str, full_amt, weekly_amt, item_index, date_badge=""):
    is_paid = name_str in cloud_data["paid_slices"]
    style_class = "slice-container-paid" if is_paid else "slice-container"
    strike_start = "<s>" if is_paid else ""
    strike_end = "</s>" if is_paid else ""
    color_text = "color: #8b949e;" if is_paid else "color: #00e676; font-weight: bold;"
    badge_html = f" <span style='color: #f1c40f; font-size: 0.85em; background-color: #282114; padding: 2px 6px; border-radius: 4px; margin-left: 6px;'>📅 {date_badge}</span>" if date_badge else ""
    
    col_content, col_btn = st.columns([5, 1])
    with col_content:
        st.markdown(f"""
            <div class="{style_class}">
                {strike_start}<b>{name_str}</b>{badge_html}<br>
                Full Bill: ${full_amt:,.2f} | <span style="{color_text}">Weekly Segment Reference: ${weekly_amt:,.2f}/wk</span>{strike_end}
            </div>
        """, unsafe_allow_html=True)
    with col_btn:
        st.write("") 
        if is_paid:
            if st.button("↩️", key=f"unpay_{name_str}_{item_index}"):
                requests.post(APPS_SCRIPT_URL, json={"action": "delete", "sheetName": "paid_slices", "targetName": name_str})
                st.rerun()
        else:
            if st.button("✅", key=f"pay_{name_str}_{item_index}"):
                requests.post(APPS_SCRIPT_URL, json={"action": "add", "sheetName": "paid_slices", "rowData": [name_str, str(datetime.date.today())]})
                st.rerun()

with tab_segments:
    st.markdown("### 📊 long-Term Target Slices (Your Ideal Target Transfer: **${total_weekly_sum:,.2f}/wk**)")
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("<div class='category-header'><h4>🗓️ Fixed Monthly Slices (Weekly Values)</h4></div>", unsafe_allow_html=True)
        for idx, b in enumerate(st.session_state.monthly_bills):
            w_val = (b['val'] * 12) / 52
            render_slice_item(b['name'], b['val'], w_val, f"mon_{idx}", date_badge=b['day'])
            
    with col_right:
        st.markdown("<div class='category-header'><h4>⏳ Weekly & Fortnightly Base Slices</h4></div>", unsafe_allow_html=True)
        for idx, b in enumerate(st.session_state.weekly_bills):
            w_val = b['val'] if b['freq'] == 'Weekly' else b['val'] / 2
            render_slice_item(b['name'], b['val'], w_val, f"wek_{idx}", date_badge=b.get('desc', b['freq']))

with tab_spend_track:
    st.markdown("### 💰 Quick-Deduct Spending Buffers")
    fuel_spent = sum(item["amount"] for item in cloud_data["spending_log"] if item["category"] == "Fuel")
    grocery_spent = sum(item["amount"] for item in cloud_data["spending_log"] if item["category"] == "Groceries")
    f_rem = max(100.0 - fuel_spent, 0.0)
    g_rem = max(150.0 - grocery_spent, 0.0)
    
    c_f, c_g = st.columns(2)
    with c_f:
        st.subheader(f"⛽ Fuel Pocket: ${f_rem:,.2f} Left")
        st.progress(f_rem / 100.0)
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            if st.button("Log $20 Fuel", key="btn_f20", use_container_width=True):
                requests.post(APPS_SCRIPT_URL, json={"action": "add", "sheetName": "spending_log", "rowData": ["Fuel", 20, str(datetime.date.today())]})
                st.rerun()
        with c_f2:
            if st.button("Log $50 Fuel", key="btn_f50", use_container_width=True):
                requests.post(APPS_SCRIPT_URL, json={"action": "add", "sheetName": "spending_log", "rowData": ["Fuel", 50, str(datetime.date.today())]})
                st.rerun()
            
    with c_g:
        st.subheader(f"🛒 Grocery Pocket: ${g_rem:,.2f} Left")
        st.progress(g_rem / 150.0)
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            if st.button("Log $20 Groceries", key="btn_g20", use_container_width=True):
                requests.post(APPS_SCRIPT_URL, json={"action": "add", "sheetName": "spending_log", "rowData": ["Groceries", 20, str(datetime.date.today())]})
                st.rerun()
        with c_g2:
            if st.button("Log $50 Groceries", key="btn_g50", use_container_width=True):
                requests.post(APPS_SCRIPT_URL, json={"action": "add", "sheetName": "spending_log", "rowData": ["Groceries", 50, str(datetime.date.today())]})
                st.rerun()

    st.write("---")
    if cloud_data["spending_log"]:
        if st.button("🔥 Clear Weekly Logs", key="clear_spend", type="primary", use_container_width=True):
            requests.post(APPS_SCRIPT_URL, json={"action": "clear_all_rows", "sheetName": "spending_log"})
            st.rerun()

with tab_add_expense:
    st.markdown("### ➕ Google Sheet Custom Expense Injection")
    with st.form("custom_expense_form", clear_on_submit=True):
        new_name = st.text_input("Expense Description Name")
        col_f, col_a = st.columns(2)
        new_freq = col_f.selectbox("Billing Cycle Frequency", ["Weekly", "Fortnightly", "Monthly", "Quarterly", "6-Monthly", "Yearly"])
        new_amt = col_a.number_input("Full Bill Amount ($)", min_value=0.0, step=10.0)
        new_day = st.text_input("Due Day of Month (e.g. '14th')", value="1st")
        if st.form_submit_button("Upload to Google Sheets"):
            if new_name and new_amt > 0:
                payload = {"action": "add", "sheetName": "custom_expenses", "rowData": [new_name, new_amt, f"{new_freq} (Custom)", new_freq, new_day]}
                requests.post(APPS_SCRIPT_URL, json=payload)
                st.success("Uploaded!"); time.sleep(0.5); st.rerun()

    if cloud_data["custom_expenses"]:
        st.markdown("<div class='category-header'><h4>☁️ Manage / Delete Active Custom Expenses</h4></div>", unsafe_allow_html=True)
        for idx, item in enumerate(cloud_data["custom_expenses"]):
            c_left, c_right = st.columns([4, 1])
            with c_left: st.markdown(f"🔹 **{item['name']}** | Full Bill: ${item['val']:,.2f} ({item['freq']}) due {item['day']}")
            with c_right:
                if st.button("❌ Remove", key=f"del_ce_{item['name']}_{idx}"):
                    requests.post(APPS_SCRIPT_URL, json={"action": "delete", "sheetName": "custom_expenses", "targetName": item['name']})
                    st.rerun()

with tab_afterpay:
    st.markdown("### Interactive Afterpay Registry")
    with st.form("ap_entry_form", clear_on_submit=True):
        ap_merchant = st.text_input("Store Name / Item Description")
        col_x, col_y = st.columns(2)
        ap_fortnightly = col_x.number_input("Fortnightly Installment Amount ($)", min_value=0.0, step=5.0)
        ap_remaining = col_y.number_input("Payments Remaining", min_value=1, max_value=4, value=4, step=1)
        if st.form_submit_button("Lock Plan to Google Sheets"):
            if ap_merchant and ap_fortnightly > 0:
                payload = {"action": "add", "sheetName": "afterpay_ledger", "rowData": [ap_merchant, ap_fortnightly, ap_remaining, ap_fortnightly * ap_remaining]}
                requests.post(APPS_SCRIPT_URL, json=payload)
                st.rerun()

    if st.session_state.afterpay_ledger:
        st.markdown("<div class='category-header'><h4>🛍️ Active Afterpay Orders</h4></div>", unsafe_allow_html=True)
        for idx, plan in enumerate(st.session_state.afterpay_ledger):
            c_left, c_right = st.columns([4, 1])
            with c_left:
                pct_paid = ((4 - plan['Remaining']) / 4.0)
                st.markdown(f"🛍️ **{plan['Merchant']}** | Fortnightly Cost: ${plan['Fortnightly Cost']:,.2f} ({plan['Remaining']} payments left)")
                st.progress(pct_paid)
            with c_right:
                if st.button("❌ Clear", key=f"del_ap_{plan['Merchant']}_{idx}"):
                    requests.post(APPS_SCRIPT_URL, json={"action": "delete", "sheetName": "afterpay_ledger", "targetName": plan['Merchant']})
                    st.rerun()
