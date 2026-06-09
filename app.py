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
    
    .temp-bill-row {
        background-color: #281c1c;
        padding: 6px 12px;
        margin-top: 4px;
        border-radius: 4px;
        border-left: 3px solid #f25c5c;
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
    temporary_expenses = []
    paid_slices = set()
    deleted_baseline = set()
    
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

    # Fetch One-Off Specific Weekly Temporary Expenses
    try:
        url_temp = get_csv_download_url(GOOGLE_SHEET_URL, "temporary_expenses")
        if url_temp:
            url_temp += f"&cache_bust={int(time.time())}"
            df_temp = pd.read_csv(url_temp)
            if len(df_temp) > 0:
                for _, row in df_temp.iterrows():
                    try:
                        temporary_expenses.append({
                            "week_target": int(row.iloc[0]),
                            "name": str(row.iloc[1]).strip(),
                            "val": float(str(row.iloc[2]).replace('$', '').replace(',', '').strip())
                        })
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
                        date_logged = datetime.datetime.strptime(str(row.iloc[1]).strip(), "%Y-%m-%d").date()
                        if date_logged >= current_wednesday:
                            paid_slices.add(slice_name)
                    except: pass
    except: pass

    # Fetch Muted Baseline Subscriptions
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

    # Fetch Custom Expenses
    try:
        url_ce = get_csv_download_url(GOOGLE_SHEET_URL, "custom_expenses")
        if url_ce:
            url_ce += f"&cache_bust={int(time.time())}"
            df_ce = pd.read_csv(url_ce)
            df_ce.columns = [str(c).strip().lower() for c in df_ce.columns]
            name_col = 'name' if 'name' in df_ce.columns else (df_ce.columns[0] if len(df_ce.columns) > 0 else None)
            val_col = 'val' if 'val' in df_ce.columns else ('value' if 'value' in df_ce.columns else ('amount' if 'amount' in df_ce.columns else None))
            freq_col = 'freq' if 'freq' in df_ce.columns else ('frequency' if 'frequency' in df_ce.columns else None)
            day_col = 'day' if 'day' in df_ce.columns else None

            if name_col and val_col:
                df_ce = df_ce.dropna(subset=[name_col, val_col])
                for _, row in df_ce.iterrows():
                    try:
                        val_float = float(str(row[val_col]).replace('$', '').replace(',', '').strip())
                        freq_val = str(row[freq_col]).strip() if freq_col and pd.notna(row[freq_col]) else "Monthly"
                        day_val = str(row[day_col]).strip() if day_col and pd.notna(row[day_col]) else "1st"
                        custom_expenses.append({"name": str(row[name_col]).strip(), "val": val_float, "freq": freq_val, "day": day_val, "is_custom": True})
                    except: pass
    except: pass

    # Fetch Afterpay Ledger
    try:
        url_ap = get_csv_download_url(GOOGLE_SHEET_URL, "afterpay_ledger")
        if url_ap:
            url_ap += f"&cache_bust={int(time.time())}"
            df_ap = pd.read_csv(url_ap)
            df_ap.columns = [str(c).strip().lower() for c in df_ap.columns]
            merchant_col = 'merchant' if 'merchant' in df_ap.columns else (df_ap.columns[0] if len(df_ap.columns) > 0 else None)
            cost_col = 'fortnightly cost' if 'fortnightly cost' in df_ap.columns else ('cost' if 'cost' in df_ap.columns else ('amount' if 'amount' in df_ap.columns else None))
            rem_col = 'remaining' if 'remaining' in df_ap.columns else None
            
            if merchant_col and cost_col:
                df_ap = df_ap.dropna(subset=[merchant_col, cost_col])
                for _, row in df_ap.iterrows():
                    try:
                        cost_float = float(str(row[cost_col]).replace('$', '').replace(',', '').strip())
                        rem_int = int(float(str(row[rem_col]).strip())) if rem_col and pd.notna(row[rem_col]) else 4
                        afterpay_ledger.append({"Merchant": str(row[merchant_col]).strip(), "Fortnightly Cost": cost_float, "Remaining": rem_int})
                    except: pass
    except: pass

    # Fetch Quick Spending Logs
    try:
        url_sl = get_csv_download_url(GOOGLE_SHEET_URL, "spending_log")
        if url_sl:
            url_sl += f"&cache_bust={int(time.time())}"
            df_sl = pd.read_csv(url_sl)
            if len(df_sl) > 0:
                for _, row in df_sl.iterrows():
                    try: spending_log.append({"category": str(row.iloc[0]).strip(), "amount": float(str(row.iloc[1]).replace('$', ''))})
                    except: pass
    except: pass
        
    return {"custom_expenses": custom_expenses, "afterpay_ledger": afterpay_ledger, "spending_log": spending_log, "paid_slices": paid_slices, "deleted_baseline": deleted_baseline, "saved_weekly_pay": saved_weekly_pay, "temporary_expenses": temporary_expenses}

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
    {"name": "Emergency Fund", "val": 100.00, "freq": "Weekly"}, {"name": "Church", "val": 170.00, "freq": "Weekly"},
    {"name": "Fuel Buffer", "val": 100.00, "freq": "Weekly"}, {"name": "Grocery Buffer", "val": 150.00, "freq": "Weekly"},
    {"name": "Rent (Cambridge)", "val": 480.00, "freq": "Weekly"}, {"name": "Gym", "val": 91.00, "freq": "Fortnightly"},
    {"name": "Isuzu mux", "val": 714.00, "freq": "Fortnightly"}, {"name": "TAX", "val": 65.00, "freq": "Fortnightly"},
    {"name": "Bakery Movement", "val": 180.00, "freq": "Weekly"}  # ✅ NEW FIXED WEEKLY BASELINE INJECTED HERE
]

BASE_MONTHLY = [b for b in RAW_MONTHLY if b["name"] not in cloud_data["deleted_baseline"]]
BASE_WEEKLY = [b for b in RAW_WEEKLY if b["name"] not in cloud_data["deleted_baseline"]]

st.session_state.monthly_bills = list(BASE_MONTHLY)
st.session_state.weekly_bills = list(BASE_WEEKLY)
st.session_state.afterpay_ledger = cloud_data["afterpay_ledger"]

for item in cloud_data["custom_expenses"]:
    if item["freq"] in ["Weekly", "Fortnightly"]: st.session_state.weekly_bills.append(item)
    elif item["freq"] == "Monthly": st.session_state.monthly_bills.append(item)

# Sinking Fund Reference Total
sum_fixed_monthly = sum((b["val"] * 12) / 52 for b in st.session_state.monthly_bills)
sum_fixed_weekly = sum(b["val"] if b["freq"] == "Weekly" else b["val"] / 2 for b in st.session_state.weekly_bills)
total_weekly_sum = sum_fixed_monthly + sum_fixed_weekly + sum(p["Fortnightly Cost"] / 2 for p in st.session_state.afterpay_ledger)

st.title("🛡️ 4-Week Paycheck Horizon Matrix")
st.caption("Change individual paycheck boxes below dynamically based on your exact hours or scheduled income for that specific week.")

# --- CALENDAR WINDOW MATRIX CALCULATOR ---
today = datetime.date.today()
days_since_wed = (today.weekday() - 2) % 7
wed0 = today - datetime.timedelta(days=days_since_wed)

windows = []
for i in range(4):
    start_w = wed0 + datetime.timedelta(weeks=i)
    end_t = start_w + datetime.timedelta(days=6)
    windows.append((start_w, end_t))

window_bills = [[], [], [], []]

# Map Monthly Bills to actual weeks
for b in st.session_state.monthly_bills:
    for offset in [0, 1]:
        d_date = get_due_date_details(b["day"], target_month_offset=offset)
        for idx, (ws_date, we_date) in enumerate(windows):
            if ws_date <= d_date <= we_date:
                window_bills[idx].append({"name": b["name"], "val": b["val"], "is_temp": False})

# Map Weekly/Fortnightly Obligations
for idx, (ws_date, we_date) in enumerate(windows):
    for b in st.session_state.weekly_bills:
        if b["freq"] == "Weekly":
            window_bills[idx].append({"name": b["name"], "val": b["val"], "is_temp": False})
        else:
            if idx % 2 == 0:
                window_bills[idx].append({"name": b["name"], "val": b["val"], "is_temp": False})

# Map Afterpay Ledger
for plan in st.session_state.afterpay_ledger:
    window_bills[0].append({"name": f"🛍️ AP: {plan['Merchant']}", "val": plan["Fortnightly Cost"], "is_temp": False})
    window_bills[2].append({"name": f"🛍️ AP: {plan['Merchant']}", "val": plan["Fortnightly Cost"], "is_temp": False})

# Inject Custom One-Off Specific Weekly Temporary Expenses
for t_exp in cloud_data["temporary_expenses"]:
    target_idx = t_exp["week_target"]
    if 0 <= target_idx < 4:
        window_bills[target_idx].append({"name": f"⚠️ {t_exp['name']}", "val": t_exp["val"], "is_temp": True})

# --- RENDER CLOUD-PERSISTENT INPUT COLUMNS ---
cols_matrix = st.columns(4)
for i in range(4):
    ws_date, we_date = windows[i]
    with cols_matrix[i]:
        st.markdown(f"""
        <div class="paycheck-window-card">
            <h4>Week {i+1} Paycheck</h4>
            <span style="color: #8b949e; font-size: 0.82em;">📅 {ws_date.strftime('%d %b')} - {we_date.strftime('%d %b')}</span>
        </div>
        """, unsafe_allow_html=True)
        
        cloud_val = cloud_data["saved_weekly_pay"].get(i, 1200.0)
        
        this_weeks_pay = st.number_input(
            "Income ($)",
            min_value=0.0,
            value=float(cloud_val),
            step=50.0,
            key=f"pay_input_wk_{i}"
        )
        
        if st.button(f"💾 Save Week {i+1} Income", key=f"save_wk_btn_{i}", use_container_width=True):
            requests.post(APPS_SCRIPT_URL, json={"action": "delete", "sheetName": "weekly_income_memory", "targetName": str(i)})
            requests.post(APPS_SCRIPT_URL, json={"action": "add", "sheetName": "weekly_income_memory", "rowData": [i, this_weeks_pay]})
            st.success(f"Week {i+1} Saved!")
            time.sleep(0.4)
            st.rerun()
        
        full_bills_sum = sum(b["val"] for b in window_bills[i])
        net_leftover = this_weeks_pay - full_bills_sum
        
        st.metric(label="Total Owed Full", value=f"${full_bills_sum:,.2f}")
        if net_leftover >= 0:
            st.success(f"Leftover: ${net_leftover:,.2f}")
        else:
            st.error(f"Shortfall: ${net_leftover:,.2f}")
            
        st.write("---")
        for item in window_bills[i]:
            row_style = "temp-bill-row" if item.get("is_temp", False) else "bill-alert-row"
            st.markdown(f"""
            <div class="{row_style}">
                <span>{item['name']}</span>
                <span style="font-weight: bold;">${item['val']:.0f}</span>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# --- CONSOLE TABS FOR REFERENCE AND LOGS ---
tab_segments, tab_spend_track, tab_oneoff_temp, tab_add_expense, tab_afterpay = st.tabs([
    "🗂️ Weekly Segment Core Reference", 
    "💰 Fuel & Grocery Loggers",
    "🚨 One-Off Week Expenses",
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
    st.markdown(f"### 📊 Long-Term Target Slices (Your Ideal Target Transfer: **${total_weekly_sum:,.2f}/wk**)")
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
            render_slice_item(b['name'], b['val'], w_val, f"wek_{idx}", date_badge=b.get('freq'))

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

with tab_oneoff_temp:
    st.markdown("### 🚨 Add Temporary One-Off Expense to a Specific Week")
    st.caption("Perfect for unexpected costs that happen once, allowing you to intercept a specific paycheck row.")
    with st.form("temporary_expense_form", clear_on_submit=True):
        target_wk_sel = st.selectbox("Target Paycheck Card Location", ["Week 1", "Week 2", "Week 3", "Week 4"])
        temp_name = st.text_input("Expense Title (e.g. 'Car Mechanic', 'Birthday Gift')")
        temp_amt = st.number_input("Amount Owed ($)", min_value=0.0, step=10.0)
        
        if st.form_submit_button("Inject into Target Week Row"):
            if temp_name and temp_amt > 0:
                wk_mapping = {"Week 1": 0, "Week 2": 1, "Week 3": 2, "Week 4": 3}
                payload = {"action": "add", "sheetName": "temporary_expenses", "rowData": [wk_mapping[target_wk_sel], temp_name, temp_amt]}
                requests.post(APPS_SCRIPT_URL, json=payload)
                st.success(f"Injected into {target_wk_sel}!"); time.sleep(0.5); st.rerun()

    if cloud_data["temporary_expenses"]:
        st.markdown("<div class='category-header'><h4>🗑️ Active Temporary Expenses (Click to Remove / Pay Off)</h4></div>", unsafe_allow_html=True)
        for idx, item in enumerate(cloud_data["temporary_expenses"]):
            c_left, c_right = st.columns([4, 1])
            with c_left: st.markdown(f"🚨 **Week {item['week_target']+1}** | {item['name']}: **${item['val']:,.2f}**")
            with c_right:
                if st.button("✅ Remove / Paid Off", key=f"del_temp_{item['name']}_{idx}"):
                    requests.post(APPS_SCRIPT_URL, json={"action": "delete", "sheetName": "temporary_expenses", "targetName": item['name']})
                    st.rerun()

with tab_add_expense:
    st.markdown("### ➕ Google Sheet Custom Expense Injection")
    with st.form("custom_expense_form", clear_on_submit=True):
        new_name = st.text_input("Expense Description Name")
        col_f, col_a = st.columns(2)
        new_freq = col_f.selectbox("Billing Cycle Frequency", ["Weekly", "Fortnightly", "Monthly"])
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
                st.success("Committed!"); time.sleep(0.5); st.rerun()

    if st.session_state.afterpay_ledger:
        st.markdown("<div class='category-header'><h4>🛍️ Active Afterpay Orders</h4></div>", unsafe_allow_html=True)
        for idx, plan in enumerate(st.session_state.afterpay_ledger):
            c_left, c_right = st.columns([4, 1])
            with c_left:
                pct_paid = ((4 - plan['Remaining']) / 4.0)
                st.markdown(f"🛍️ **{plan['Merchant']}** | Fortnightly Cost: ${plan['Fortnightly Cost']:,.2f} ({plan['Remaining']} payments left)")
            with c_right:
                if st.button("❌ Clear", key=f"del_ap_{plan['Merchant']}_{idx}"):
                    requests.post(APPS_SCRIPT_URL, json={"action": "delete", "sheetName": "afterpay_ledger", "targetName": plan['Merchant']})
                    st.rerun()
