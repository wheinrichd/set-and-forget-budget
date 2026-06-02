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
    
    /* Slice Container Styling */
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

# Helper Function: Feature 1 - Intelligent Due Date Calculator & Calendar Date String Maker
def get_due_date_details(day_str):
    try:
        due_day = int(''.join(c for c in day_str if c.isdigit()))
        today = datetime.datetime.now()
        
        # Try building the date for the current month
        try:
            target_date = today.replace(day=due_day)
        except ValueError:
            # Handle months with fewer days (e.g., if day is 30/31 and it's February)
            next_month = today.replace(day=28) + datetime.timedelta(days=4)
            last_day_this_month = (next_month - datetime.timedelta(days=next_month.day)).day
            target_date = today.replace(day=last_day_this_month)
            due_day = last_day_this_month
            
        if due_day < today.day:
            # If the day has already passed this month, it's due next month
            if today.month == 12:
                target_date = target_date.replace(year=today.year + 1, month=1)
            else:
                target_date = target_date.replace(month=today.month + 1)
                
        days_until = (target_date.date() - today.date()).days
        formatted_date = target_date.strftime("%d %b")
        return days_until, formatted_date
    except:
        return 99, "Custom"

# --- GOOGLE SHEET LIVE PARSING DATA ENGINE ---
def get_csv_download_url(sheet_url, sheet_name):
    try:
        if '/edit' in sheet_url:
            base_url = sheet_url.split('/edit')[0]
        elif '/pub' in sheet_url:
            base_url = sheet_url.split('/pub')[0]
        else:
            base_url = sheet_url.rstrip('/')
        return f"{base_url}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    except:
        return ""

def load_cloud_data():
    custom_expenses = []
    afterpay_ledger = []
    spending_log = []
    raw_sl_debug = []
    paid_slices = set()
    
    # Calculate current cycle's Wednesday boundary
    today = datetime.date.today()
    days_since_wednesday = (today.weekday() - 2) % 7
    current_wednesday = today - datetime.timedelta(days=days_since_wednesday)
    
    # 1. Fetch Paid Slices Checklist Status (Filtered dynamically for current Wednesday cycle)
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

    # 2. Fetch Custom Expenses
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

    # 3. Fetch Afterpay Ledger
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

    # 4. Fetch Quick Spending Logs
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
                        
                        raw_sl_debug.append({"Category Column": cat_str, "Amount Column": val_str})
                        
                        if val_str.lower() in ['amount', 'val', 'value', 'cost'] or cat_str.lower() in ['category', 'name']:
                            continue
                        clean_amt = float(val_str)
                        spending_log.append({"category": cat_str, "amount": clean_amt})
                    except: pass
    except: pass
        
    return {"custom_expenses": custom_expenses, "afterpay_ledger": afterpay_ledger, "spending_log": spending_log, "raw_sl_debug": raw_sl_debug, "paid_slices": paid_slices}

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

# --- INTERACTIVE SIDEBAR & WEALTH MODE ---
st.sidebar.title("🔒 Set & Forget Portal")
user_income = st.sidebar.number_input("Wednesday Take-Home Pay ($)", min_value=0.0, value=2200.0, step=50.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🚀 Feature 5: Wealth Mode")
wealth_mode = st.sidebar.toggle("Activate 'Safe-To-Save' Targets")
extra_savings_target = 0.0
if wealth_mode:
    extra_savings_target = st.sidebar.slider("Extra High-Yield Savings Push ($/wk)", 0, 500, 200, step=25)

st.title("🛡️ Automated Bills Command Center")

# --- MICRO-ALERTS FOR MONTHLY BILLS ---
upcoming_bills = []
for b in BASE_MONTHLY:
    days_left, due_date_str = get_due_date_details(b["day"])
    if 0 <= days_left <= 7:
        upcoming_bills.append(f"{b['name']} (${b['val']:.0f} on {due_date_str})")

if upcoming_bills:
    alert_text = "⏰ **Due Within 7 Days:** " + ", ".join(upcoming_bills)
    st.markdown(f"<div class='alert-banner'>{alert_text}</div>", unsafe_allow_html=True)

st.markdown("---")

leftover_cash = user_income - total_weekly_sum - extra_savings_target

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Wednesday Paycheck", f"${user_income:,.2f}", "Verified Total Income In")
with col2:
    st.metric("Set & Forget Bill Transfer", f"${total_weekly_sum + extra_savings_target:,.2f}", f"Includes Afterpay + Base Commitments")
with col3:
    label = "Guilt-Free Personal Cash" if wealth_mode else "Leftover Spending Cash"
    st.metric(label, f"${leftover_cash:,.2f}", "Safe Discretionary Balance" if leftover_cash >= 0 else "Income Deficit Warning", delta_color="normal" if leftover_cash >= 0 else "inverse")

if wealth_mode:
    st.info(f"📈 **Wealth Mode Active:** We have successfully carved out an extra **${extra_savings_target:,.2f}/week** directly into your high-yield goals before showing your personal spending cash.")

st.markdown("---")

tab_segments, tab_spend_track, tab_add_expense, tab_afterpay = st.tabs([
    "🗂️ Weekly Slices & Breakdown", 
    "💰 Fuel & Grocery Loggers",
    "➕ Add New Custom Expense", 
    "🛍️ Afterpay Intercept Guard"
])

# Interactive Component: Checkbox Actions Engine
def render_slice_item(name_str, full_amt, weekly_amt, date_badge=""):
    is_paid = name_str in cloud_data["paid_slices"]
    style_class = "slice-container-paid" if is_paid else "slice-container"
    strike_start = "<s>" if is_paid else ""
    strike_end = "</s>" if is_paid else ""
    color_text = "color: #8b949e;" if is_paid else "color: #00e676; font-weight: bold;"
    
    # Render badges visually next to the bill name
    badge_html = f" <span style='color: #f1c40f; font-size: 0.85em; background-color: #282114; padding: 2px 6px; border-radius: 4px; margin-left: 6px;'>📅 {date_badge}</span>" if date_badge else ""
    
    col_content, col_btn = st.columns([5, 1])
    with col_content:
        st.markdown(f"""
            <div class="{style_class}">
                {strike_start}<b>{name_str}</b>{badge_html}<br>
                Full Bill: ${full_amt:,.2f} | <span style="{color_text}">Weekly Segment: ${weekly_amt:,.2f}/wk</span>{strike_end}
            </div>
        """, unsafe_allow_html=True)
    with col_btn:
        st.write("") # spacing alignment
        if is_paid:
            if st.button("↩️", key=f"unpay_{name_str}", help="Mark as unpaid"):
                requests.post(APPS_SCRIPT_URL, json={"action": "delete", "sheetName": "paid_slices", "targetName": name_str})
                st.rerun()
        else:
            if st.button("✅", key=f"pay_{name_str}", help="Mark as paid for this week"):
                requests.post(APPS_SCRIPT_URL, json={"action": "add", "sheetName": "paid_slices", "rowData": [name_str, str(datetime.date.today())]})
                st.rerun()

with tab_segments:
    st.markdown("### 📊 Live Paycheck Allocation Breakdown")
    categories = {
        "🗓️ Subscriptions & Monthly Debits": sum_fixed_monthly,
        "⏳ Living, Church & Core Base Slices": sum_fixed_weekly,
        "⚡ Quarterly Utility Provisions": sum_utilities,
        "🦅 Strategic Long-Term Rego & Insurances": sum_strategic_yearly,
        "🛍️ Active Afterpay Intercept Balance": total_ap_weekly_impact,
        "📈 Strategic Extra Savings Push": extra_savings_target
    }
    for cat_name, cat_val in categories.items():
        if cat_val > 0:
            pct = (cat_val / user_income) * 100
            st.write(f"**{cat_name}** — ${cat_val:,.2f}/wk ({pct:.1f}% of check)")
            st.progress(min(pct / 100, 1.0))
            
    st.markdown("---")
    st.markdown("### 🗺️ Active Weekly Slices & Paid Checklist")
    st.caption("Tap ✅ when you transfer or clear a slice for the week. It will automatically reset to unpaid next Wednesday morning.")
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("<div class='category-header'><h4>🗓️ Fixed Monthly Slices (Weekly Value)</h4></div>", unsafe_allow_html=True)
        st.write("")
        for b in st.session_state.monthly_bills:
            w_val = (b['val'] * 12) / 52
            _, due_date_str = get_due_date_details(b['day'])
            render_slice_item(b['name'], b['val'], w_val, date_badge=due_date_str)
            
    with col_right:
        st.markdown("<div class='category-header'><h4>⏳ Weekly & Fortnightly Base Slices</h4></div>", unsafe_allow_html=True)
        st.write("")
        for b in st.session_state.weekly_bills:
            w_val = b['val'] if b['freq'] == 'Weekly' else b['val'] / 2
            # Use the descriptive text directly for weekly frequency notes
            render_slice_item(b['name'], b['val'], w_val, date_badge=b.get('desc', b['freq']))

    st.markdown("---")
    col_util, col_yearly = st.columns(2)
    with col_util:
        st.markdown("<div class='category-header'><h4>⚡ Quarterly Utility Provisions</h4></div>", unsafe_allow_html=True)
        st.write("")
        if st.session_state.quarterly_bills:
            for b in st.session_state.quarterly_bills:
                w_val = b['val'] / 13
                render_slice_item(b['name'], b['val'], w_val, date_badge=b.get('desc', 'Quarterly'))
        else:
            st.caption("No quarterly provisions active.")
            
    with col_yearly:
        st.markdown("<div class='category-header'><h4>🦅 Strategic Long-Term Slices (6-Month & Yearly)</h4></div>", unsafe_allow_html=True)
        st.write("")
        if st.session_state.yearly_bills:
            for b in st.session_state.yearly_bills:
                w_val = (b['val'] / 26) if b['freq'] == "6-Monthly" else (b['val'] / 52)
                render_slice_item(b['name'], b['val'], w_val, date_badge=b.get('desc', b['freq']))
        else:
            st.caption("No long-term strategic slices active.")

with tab_spend_track:
    st.markdown("### 💰 Quick-Deduct Spending Buffers")
    st.write("Tap a button while standing at the register to log variable spends against your allowances.")
    
    fuel_spent = sum(item["amount"] for item in cloud_data["spending_log"] if item["category"] == "Fuel")
    grocery_spent = sum(item["amount"] for item in cloud_data["spending_log"] if item["category"] == "Groceries")
    
    f_rem = max(100.0 - fuel_spent, 0.0)
    g_rem = max(150.0 - grocery_spent, 0.0)
    
    c_f, c_g = st.columns(2)
    with c_f:
        st.subheader(f"⛽ Fuel Pocket: ${f_rem:,.2f} Left")
        st.progress(f_rem / 100.0)
        st.caption(f"Spent: ${fuel_spent:,.2f} of $100.00 cap")
        if st.button("Log $20 Fuel Pump", key="btn_f20"):
            requests.post(APPS_SCRIPT_URL, json={"action": "add", "sheetName": "spending_log", "rowData": ["Fuel", 20, str(datetime.date.today())]})
            st.success("Logged!"); time.sleep(0.5); st.rerun()
        if st.button("Log $50 Fuel Pump", key="btn_f50"):
            requests.post(APPS_SCRIPT_URL, json={"action": "add", "sheetName": "spending_log", "rowData": ["Fuel", 50, str(datetime.date.today())]})
            st.success("Logged!"); time.sleep(0.5); st.rerun()
            
    with c_g:
        st.subheader(f"🛒 Grocery Pocket: ${g_rem:,.2f} Left")
        st.progress(g_rem / 150.0)
        st.caption(f"Spent: ${grocery_spent:,.2f} of $150.00 cap")
        if st.button("Log $20 Groceries", key="btn_g20"):
            requests.post(APPS_SCRIPT_URL, json={"action": "add", "sheetName": "spending_log", "rowData": ["Groceries", 20, str(datetime.date.today())]})
            st.success("Logged!"); time.sleep(0.5); st.rerun()
        if st.button("Log $50 Groceries", key="btn_g50"):
            requests.post(APPS_SCRIPT_URL, json={"action": "add", "sheetName": "spending_log", "rowData": ["Groceries", 50, str(datetime.date.today())]})
            st.success("Logged!"); time.sleep(0.5); st.rerun()

    st.markdown("---")
    with st.expander("📋 Live Cloud Diagnostics (Raw Rows Found in spending_log Tab)"):
        if cloud_data["raw_sl_debug"]:
            st.dataframe(pd.DataFrame(cloud_data["raw_sl_debug"]))
        else:
            st.warning("No data returned yet. Make sure your tab name is spelled exactly lowercase: spending_log")

    if cloud_data["spending_log"]:
        if st.button("🔄 Reset Spending Logs For New Week", key="clear_spend"):
            requests.post(APPS_SCRIPT_URL, json={"action": "delete", "sheetName": "spending_log", "targetName": "Fuel"})
            requests.post(APPS_SCRIPT_URL, json={"action": "delete", "sheetName": "spending_log", "targetName": "Groceries"})
            st.success("Logs reset!"); time.sleep(0.5); st.rerun()

with tab_add_expense:
    st.markdown("### ➕ Google Sheet Custom Expense Injection")
    with st.form("custom_expense_form", clear_on_submit=True):
        new_name = st.text_input("Expense Description Name")
        col_f, col_a = st.columns(2)
        new_freq = col_f.selectbox("Billing Cycle Frequency", ["Weekly", "Fortnightly", "Monthly", "Quarterly", "6-Monthly", "Yearly"])
        new_amt = col_a.number_input("Full Bill Amount ($)", min_value=0.0, step=10.0)
        if st.form_submit_button("Upload to Google Sheets"):
            if new_name and new_amt > 0:
                payload = {"action": "add", "sheetName": "custom_expenses", "rowData": [new_name, new_amt, f"{new_freq} (Custom)", new_freq, "Custom"]}
                requests.post(APPS_SCRIPT_URL, json=payload)
                st.success("Uploaded!"); time.sleep(0.5); st.rerun()

    if cloud_data["custom_expenses"]:
        st.markdown("<div class='category-header'><h4>☁️ Manage / Delete Active Custom Expenses</h4></div>", unsafe_allow_html=True)
        for item in cloud_data["custom_expenses"]:
            c_left, c_right = st.columns([4, 1])
            with c_left: st.markdown(f"🔹 **{item['name']}** | Full Bill: ${item['val']:,.2f} ({item['freq']})")
            with c_right:
                if st.button("❌ Remove", key=f"del_ce_{item['name']}"):
                    requests.post(APPS_SCRIPT_URL, json={"action": "delete", "sheetName": "custom_expenses", "targetName": item['name']})
                    st.success("Erased!"); time.sleep(0.5); st.rerun()

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
        for plan in st.session_state.afterpay_ledger:
            c_left, c_right = st.columns([4, 1])
            with c_left:
                pct_paid = ((4 - plan['Remaining']) / 4.0)
                st.markdown(f"🛍️ **{plan['Merchant']}** | Fortnightly Cost: ${plan['Fortnightly Cost']:,.2f} ({plan['Remaining']} payments left)")
                st.progress(pct_paid)
                st.caption(f"Total Remaining Debt: ${plan['Total Debt']:,.2f} | {pct_paid*100:.0f}% Paid Off")
            with c_right:
                st.write("")
                if st.button("❌ Clear", key=f"del_ap_{plan['Merchant']}"):
                    requests.post(APPS_SCRIPT_URL, json={"action": "delete", "sheetName": "afterpay_ledger", "targetName": plan['Merchant']})
                    st.success("Cleared!"); time.sleep(0.5); st.rerun()
