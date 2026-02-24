import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from PIL import Image
import re
import time
from fpdf import FPDF

# --- 1. PAGE CONFIGURATION ---
try:
    logo_img = Image.open("logo.jpg")
    st.set_page_config(page_title="Therapeutic Oils | Lab Portal", page_icon=logo_img, layout="wide", initial_sidebar_state="expanded")
except FileNotFoundError:
    st.set_page_config(page_title="Therapeutic Oils | Lab Portal", layout="wide", initial_sidebar_state="expanded")

# --- 2. CUSTOM CSS ---
def inject_custom_css():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {background-color: transparent !important;}
        .stApp { background-color: #FAFAFA; font-family: 'Inter', -apple-system, sans-serif; }
        [data-testid="stMetricValue"] { font-size: 2.2rem; font-weight: 300; color: #1E293B; letter-spacing: -0.02em; }
        [data-testid="stMetricLabel"] { font-size: 0.85rem; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; }
        [data-testid="metric-container"] { background-color: #FFFFFF; border: 1px solid #E2E8F0; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
        .stButton>button { border-radius: 4px; font-weight: 500; border: 1px solid #CBD5E1; background-color: #FFFFFF; color: #334155; transition: all 0.2s ease; }
        .stButton>button:hover { border-color: #94A3B8; color: #0F172A; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .stButton>button[kind="primary"] { background-color: #0F172A; color: #FFFFFF; border: none; }
        .stButton>button[kind="primary"]:hover { background-color: #1E293B; }
        h1, h2, h3 { color: #0F172A; font-weight: 400; letter-spacing: -0.01em; }
        </style>
    """, unsafe_allow_html=True)

# --- Connect to the Database ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
supabase = init_connection()

def fetch_vault_data(table_name, sort_column=None):
    for attempt in range(3): 
        try:
            resp = supabase.table(table_name).select("*").execute()
            df = pd.DataFrame(resp.data) if resp.data else pd.DataFrame()
            if not df.empty and sort_column and sort_column in df.columns:
                df = df.sort_values(sort_column)
            return df
        except Exception: time.sleep(0.5) 
    st.error(f"⚠️ Network timeout accessing {table_name}. Please refresh.")
    st.stop()

# --- PDF Engines ---
def generate_order_pdf(order_ref, items_df, client_name, date_str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "THERAPEUTIC OILS", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, "Official Order Summary", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(100, 8, f"Billed To: {client_name}")
    pdf.cell(0, 8, f"Date: {date_str}", ln=True, align="R")
    pdf.cell(0, 8, f"Order Ref: {order_ref}", ln=True, align="R")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(90, 8, "Product Description", border=1)
    pdf.cell(25, 8, "Qty", border=1, align="C")
    pdf.cell(35, 8, "Unit Price", border=1, align="R")
    pdf.cell(40, 8, "Line Total", border=1, align="R")
    pdf.ln()
    pdf.set_font("Arial", "", 10)
    grand_total = 0.0
    for _, row in items_df.iterrows():
        total = float(row['gross_revenue'])
        grand_total += total
        pdf.cell(90, 8, str(row['order_description'])[:45], border=1)
        pdf.cell(25, 8, str(row['quantity']), border=1, align="C")
        pdf.cell(35, 8, f"${float(row['unit_price']):,.2f}", border=1, align="R")
        pdf.cell(40, 8, f"${total:,.2f}", border=1, align="R")
        pdf.ln()
    pdf.set_font("Arial", "B", 10)
    pdf.cell(150, 8, "Grand Total", border=1, align="R")
    pdf.cell(40, 8, f"${grand_total:,.2f}", border=1, align="R")
    return pdf.output(dest="S").encode("latin-1")

def generate_consignment_pdf(order_ref, items_df, partner_name, date_str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "THERAPEUTIC OILS", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, "Official Consignment Agreement", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(100, 8, f"Consignee (Partner): {partner_name}")
    pdf.cell(0, 8, f"Date Issued: {date_str}", ln=True, align="R")
    pdf.cell(0, 8, f"Reference #: {order_ref}", ln=True, align="R")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 9)
    pdf.cell(75, 8, "Product Description", border=1)
    pdf.cell(20, 8, "Qty Sent", border=1, align="C")
    pdf.cell(30, 8, "Retail Price", border=1, align="R")
    pdf.cell(30, 8, "Owed to Maker", border=1, align="R")
    pdf.cell(35, 8, "Max Potential", border=1, align="R")
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    grand_total_owed = 0.0
    for _, row in items_df.iterrows():
        wholesale = float(row['wholesale_price'])
        total_owed = float(row['qty_consigned'] * wholesale)
        grand_total_owed += total_owed
        
        pdf.cell(75, 8, str(row['product_name'])[:35], border=1)
        pdf.cell(20, 8, str(row['qty_consigned']), border=1, align="C")
        pdf.cell(30, 8, f"${float(row['retail_price']):,.2f}", border=1, align="R")
        pdf.cell(30, 8, f"${wholesale:,.2f}", border=1, align="R")
        pdf.cell(35, 8, f"${total_owed:,.2f}", border=1, align="R")
        pdf.ln()
        
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(155, 8, "Total Capital Owed Upon 100% Sell-Through:", border=1, align="R")
    pdf.cell(35, 8, f"${grand_total_owed:,.2f}", border=1, align="R")
    pdf.ln(15)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Terms of Consignment:", ln=True)
    pdf.set_font("Arial", "", 9)
    terms = (
        "1. Title and ownership of all goods listed above remain strictly with Therapeutic Oils until sold to an end consumer.\n"
        "2. The Consignee agrees to display and store the goods appropriately.\n"
        "3. The 'Owed to Maker' amount must be paid to Therapeutic Oils for every unit sold during the reporting period.\n"
        "4. Unsold goods may be recalled by Therapeutic Oils or returned by the Consignee at any time, provided they are in sellable condition."
    )
    pdf.multi_cell(0, 5, terms)
    return pdf.output(dest="S").encode("latin-1")

def generate_balance_sheet_pdf(date_str, cash, ar, inv_rm, inv_pm, inv_fg, fixed_assets, ap, debt, total_assets, total_liab, equity):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "THERAPEUTIC OILS", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, "Balance Sheet", ln=True, align="C")
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 6, f"As of {date_str}", ln=True, align="C")
    pdf.ln(10)
    # ASSETS
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "ASSETS", ln=True, border="B")
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Current Assets", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(140, 6, "Cash & Equivalents:")
    pdf.cell(0, 6, f"${cash:,.2f}", ln=True, align="R")
    pdf.cell(140, 6, "Accounts Receivable:")
    pdf.cell(0, 6, f"${ar:,.2f}", ln=True, align="R")
    pdf.cell(140, 6, "Inventory (Raw Materials):")
    pdf.cell(0, 6, f"${inv_rm:,.2f}", ln=True, align="R")
    pdf.cell(140, 6, "Inventory (Packaging):")
    pdf.cell(0, 6, f"${inv_pm:,.2f}", ln=True, align="R")
    pdf.cell(140, 6, "Inventory (Finished Goods):")
    pdf.cell(0, 6, f"${inv_fg:,.2f}", ln=True, align="R")
    pdf.ln(2)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Fixed Assets", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(140, 6, "Property, Plant & Equipment:")
    pdf.cell(0, 6, f"${fixed_assets:,.2f}", ln=True, align="R")
    pdf.ln(2)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(140, 8, "TOTAL ASSETS:")
    pdf.cell(0, 8, f"${total_assets:,.2f}", ln=True, align="R")
    pdf.ln(10)
    # LIABILITIES
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "LIABILITIES & EQUITY", ln=True, border="B")
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Liabilities", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(140, 6, "Accounts Payable (Unpaid Bills):")
    pdf.cell(0, 6, f"${ap:,.2f}", ln=True, align="R")
    pdf.cell(140, 6, "Short/Long Term Debt:")
    pdf.cell(0, 6, f"${debt:,.2f}", ln=True, align="R")
    pdf.ln(2)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(140, 6, "Total Liabilities:")
    pdf.cell(0, 6, f"${total_liab:,.2f}", ln=True, align="R")
    pdf.ln(4)
    # EQUITY
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Owner's Equity", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(140, 6, "Total Equity (Assets - Liabilities):")
    pdf.cell(0, 6, f"${equity:,.2f}", ln=True, align="R")
    pdf.ln(2)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(140, 8, "TOTAL LIABILITIES & EQUITY:")
    pdf.cell(0, 8, f"${(total_liab + equity):,.2f}", ln=True, align="R")
    return pdf.output(dest="S").encode("latin-1")

def generate_batch_labels_pdf(product_name, batch_number, lot_number, date_str, copies=6):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "THERAPEUTIC OILS - GMP BATCH LABELS", ln=True, align="C")
    pdf.ln(5)

    # Label dimensions (A4 page is 210 x 297 mm)
    label_w = 90
    label_h = 45
    margin_x = 10
    margin_y = 30
    spacing_x = 10
    spacing_y = 10

    for i in range(copies):
        row = i // 2
        col = i % 2
        x = margin_x + col * (label_w + spacing_x)
        y = margin_y + row * (label_h + spacing_y)

        # Draw outer box boundary for the physical label
        pdf.rect(x, y, label_w, label_h)
        
        # Content formatting inside the box
        pdf.set_xy(x, y + 5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(label_w, 6, "THERAPEUTIC OILS", ln=True, align="C")
        
        pdf.set_xy(x, y + 13)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(label_w, 5, product_name[:35], ln=True, align="C")
        
        pdf.set_xy(x + 5, y + 22)
        pdf.set_font("Arial", "", 9)
        pdf.cell(label_w - 10, 5, f"BATCH: {batch_number}", ln=True)
        pdf.set_x(x + 5)
        pdf.cell(label_w - 10, 5, f"LOT: {lot_number}", ln=True)
        pdf.set_x(x + 5)
        pdf.cell(label_w - 10, 5, f"MFG DATE: {date_str}", ln=True)
        
        pdf.set_xy(x, y + label_h - 7)
        pdf.set_font("Arial", "I", 7)
        pdf.cell(label_w, 4, "Store in a cool, dark environment. Follow standard SOP.", ln=True, align="C")

    return pdf.output(dest="S").encode("latin-1")

# --- Authentication Logic ---
def check_password():
    if "authenticated" not in st.session_state: st.session_state["authenticated"] = False
    if st.session_state["authenticated"]: return True
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("<br><br><br>", unsafe_allow_html=True)
        try: st.image("logo.jpg", use_container_width=True)
        except: st.markdown("<h1 style='text-align: center; font-weight: 300;'>Therapeutic Oils</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748B;'>Secure Laboratory Portal</p>", unsafe_allow_html=True)
        password = st.text_input("Passcode", type="password", placeholder="Enter team passcode...")
        if st.button("Authenticate", use_container_width=True, type="primary"):
            if password == "lab2026":
                st.session_state["authenticated"] = True; st.rerun()
            else: st.error("Incorrect passcode.")
    return False

# --- Main App Execution ---
if check_password():
    inject_custom_css()
    
    # --- MODULAR SIDEBAR DESIGN ---
    with st.sidebar:
        try: st.image("logo.jpg", use_container_width=True)
        except: st.markdown("<h3 style='text-align: center; padding-bottom: 20px;'>T / O</h3>", unsafe_allow_html=True)
        
        st.write("##")
        st.markdown("<p style='color: #64748B; font-weight: 600; font-size: 0.85rem; text-transform: uppercase;'>Business Module</p>", unsafe_allow_html=True)
        
        system_module = st.selectbox(
            "Module", 
            ["📊 Finance & Sales", "📦 Inventory Management", "⚗️ R&D & Production"], 
            label_visibility="collapsed"
        )
        
        st.write("---")
        st.markdown("<p style='color: #64748B; font-weight: 600; font-size: 0.85rem; text-transform: uppercase;'>Navigation</p>", unsafe_allow_html=True)
        
        if system_module == "📊 Finance & Sales":
            menu = st.radio("Nav", ["Sales & Revenue", "Consignment Tracker", "Financial Overview", "Balance Sheet"], label_visibility="collapsed")
        elif system_module == "📦 Inventory Management":
            menu = st.radio("Nav", ["Raw Material Library", "Packaging Library", "Finished Products"], label_visibility="collapsed")
        else:
            menu = st.radio("Nav", ["Formula Hub", "COGS Calculator", "Production Logs"], label_visibility="collapsed")
            
        st.write("<br><br>", unsafe_allow_html=True)
        if st.button("Log Out", use_container_width=True): st.session_state["authenticated"] = False; st.rerun()

    # --- Fetch Global Data Securely ---
    inventory = fetch_vault_data('inventory', 'rm_code')
    packaging = fetch_vault_data('packaging', 'pm_code')
    finished_goods = fetch_vault_data('finished_products', 'fp_code')
    formulas_df = fetch_vault_data('formulas')
    cogs_records_df = fetch_vault_data('cogs_records', 'product_name')
    sales_records_df = fetch_vault_data('sales_records', 'sale_date')
    consignment_df = fetch_vault_data('consignment_records', 'created_at')

    # --- 1. SALES & REVENUE ---
    if menu == "Sales & Revenue":
        st.title("Sales & Revenue Tracker")
        st.markdown("<p style='color: #64748B;'>Monitor order volume, track pending receivables, and manage vault stock deductions.</p>", unsafe_allow_html=True)
        
        if not sales_records_df.empty:
            sales_records_df['sale_date'] = pd.to_datetime(sales_records_df['sale_date'])
            sales_records_df['Year'] = sales_records_df['sale_date'].dt.year
            years_available = sorted(sales_records_df['Year'].unique().tolist(), reverse=True)
            
            c_year, c_target = st.columns([1, 3])
            selected_year = c_year.selectbox("Fiscal Year", years_available)
            annual_target = c_target.number_input("Annual Revenue Target ($)", value=50000, step=5000)
            
            yr_df = sales_records_df[sales_records_df['Year'] == selected_year]
            yr_rev = yr_df['gross_revenue'].sum()
            yr_profit = yr_df['net_profit'].sum()
            yr_units = yr_df['quantity'].sum()
            avg_margin = (yr_profit / yr_rev * 100) if yr_rev > 0 else 0.0
            
            global_pending_df = sales_records_df[sales_records_df['status'] == 'Pending'].copy()
            global_pending_rev = global_pending_df['gross_revenue'].sum()
            
            st.write("---")
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric(f"{selected_year} Gross Revenue", f"${yr_rev:,.2f}")
            k2.metric("Total Pending Cash", f"${global_pending_rev:,.2f}", delta="-Uncollected" if global_pending_rev > 0 else None, delta_color="inverse")
            k3.metric("Net Profit", f"${yr_profit:,.2f}")
            k4.metric("Avg. Profit Margin", f"{avg_margin:.1f}%")
            k5.metric("Total Units Sold", f"{yr_units:,}")
            
            progress_pct = min(yr_rev / annual_target, 1.0) if annual_target > 0 else 0.0
            st.write(f"**Annual Target Progress:** {progress_pct*100:.1f}% (${yr_rev:,.0f} / ${annual_target:,.0f})")
            st.progress(progress_pct)
            
            if not global_pending_df.empty:
                st.write("")
                with st.expander(f"⚠️ View Aging Receivables ({len(global_pending_df)} Unpaid Line Items)"):
                    today = pd.Timestamp(datetime.now().date())
                    global_pending_df['Days Pending'] = (today - global_pending_df['sale_date']).dt.days
                    def format_age(days):
                        if days > 60: return f"🔴 {days} days"
                        elif days > 30: return f"🟠 {days} days"
                        else: return f"🟢 {days} days"
                    global_pending_df['Aging'] = global_pending_df['Days Pending'].apply(format_age)
                    aging_df = global_pending_df.sort_values(by='Days Pending', ascending=False)
                    aging_df['sale_date'] = aging_df['sale_date'].dt.strftime('%Y-%m-%d')
                    st.dataframe(aging_df[['Aging', 'sale_date', 'account', 'order_ref_number', 'order_description', 'gross_revenue']], use_container_width=True, hide_index=True, column_config={"gross_revenue": st.column_config.NumberColumn("Amount Due", format="$%.2f")})
            
            st.write("---")
            st.markdown("#### Transaction Ledger & Order Management")
            display_sales = yr_df.copy().sort_values('sale_date', ascending=False)
            display_sales['sale_date'] = display_sales['sale_date'].dt.strftime('%Y-%m-%d')
            display_sales.insert(0, '🔍', False)
            
            with st.container(border=True):
                edited_sales = st.data_editor(
                    display_sales[['🔍', 'id', 'sale_date', 'order_ref_number', 'account', 'order_description', 'quantity', 'gross_revenue', 'net_profit', 'channel', 'status']], 
                    use_container_width=True, hide_index=True,
                    disabled=['id', 'sale_date', 'order_ref_number', 'account', 'order_description', 'quantity', 'gross_revenue', 'net_profit', 'channel'],
                    column_config={
                        "id": None, "gross_revenue": st.column_config.NumberColumn("Gross Rev", format="$%.2f"),
                        "net_profit": st.column_config.NumberColumn("Net Profit", format="$%.2f"),
                        "status": st.column_config.SelectboxColumn("Status", options=["Paid", "Pending", "Cancelled"], required=True)
                    }
                )
                if st.button("💾 Synchronize Ledger Status", type="primary"):
                    for index, row in edited_sales.iterrows():
                        orig = display_sales.loc[index]
                        if row['status'] != orig['status']:
                            supabase.table('sales_records').update({'status': row['status']}).eq('id', int(row['id'])).execute()
                    st.success("Ledger payments synchronized!")
                    st.rerun()

            selected_sales = edited_sales[edited_sales['🔍'] == True]
            if not selected_sales.empty:
                sel_id = selected_sales.iloc[0]['id']
                sale_item = yr_df[yr_df['id'] == sel_id].iloc[0]
                ref_num = sale_item['order_ref_number']
                if pd.notna(ref_num) and str(ref_num).strip() != "":
                    order_items = yr_df[yr_df['order_ref_number'] == ref_num]
                else:
                    order_items = pd.DataFrame([sale_item])
                
                st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### 📦 Inspecting Order Reference: {ref_num if pd.notna(ref_num) else 'Unreferenced'}")
                    st.write(f"**Client:** {sale_item['account']} | **Date:** {sale_item['sale_date'].strftime('%Y-%m-%d')}")
                    st.dataframe(order_items[['order_description', 'quantity', 'unit_price', 'gross_revenue']], hide_index=True, use_container_width=True)
                    order_total = order_items['gross_revenue'].sum()
                    st.metric("Total Order Value", f"${order_total:,.2f}")
                    col_pdf, col_rev = st.columns(2)
                    with col_pdf:
                        pdf_bytes = generate_order_pdf(str(ref_num), order_items, str(sale_item['account']), sale_item['sale_date'].strftime('%Y-%m-%d'))
                        st.download_button(label="📄 Download PDF Order Summary", data=pdf_bytes, file_name=f"TherapeuticOils_Order_{ref_num}.pdf", mime="application/pdf", use_container_width=True)
                    with col_rev:
                        with st.expander("⚠️ System Actions: Reverse Line Item"):
                            rev_pass = st.text_input("Authorization Passcode", type="password", key=f"rev_{sel_id}")
                            if st.button("Reverse Sale & Restore Stock", type="primary"):
                                if rev_pass == "lab2026":
                                    fp_match = finished_goods[finished_goods['product_name'] == sale_item['order_description']]
                                    if not fp_match.empty:
                                        fp_id = int(fp_match.iloc[0]['id'])
                                        current_stock = int(fp_match.iloc[0]['stock_quantity'])
                                        new_stock = current_stock + int(sale_item['quantity'])
                                        supabase.table('finished_products').update({'stock_quantity': new_stock}).eq('id', fp_id).execute()
                                    supabase.table('sales_records').delete().eq('id', int(sel_id)).execute()
                                    st.success("Transaction reversed! Financials updated and FP stock restored.")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Incorrect passcode.")
        else:
            st.info("No sales records imported or logged yet.")

        st.write("---")
        with st.expander("➕ Log New Sales Order", expanded=False):
            if not finished_goods.empty:
                pkg_opts = ["None"]
                if not packaging.empty: pkg_opts += packaging['material_name'].tolist()

                with st.form("add_sale", clear_on_submit=True):
                    st.markdown("#### 1. Core Order Details")
                    s1, s2, s3 = st.columns(3)
                    fp_opts = finished_goods['product_name'].tolist()
                    sel_product = s1.selectbox("Finished Product Sold", fp_opts)
                    qty_sold = s2.number_input("Quantity Sold", min_value=1, value=1, step=1)
                    sale_date = s3.date_input("Date of Sale", value=datetime.today())
                    
                    c1, c2, c3 = st.columns(3)
                    client = c1.text_input("Account / Client Name", placeholder="e.g., Ralph J. Ghosn")
                    order_ref = c2.text_input("Order Ref. Number")
                    channel = c3.selectbox("Channel", ["Physiotherapists", "Beauty centers", "Direct to Consumer", "Wholesale"])
                    
                    c_price, c_status = st.columns(2)
                    fg_match = finished_goods[finished_goods['product_name'] == sel_product].iloc[0]
                    default_price = float(fg_match['retail_price'])
                    unit_cogs = float(fg_match['unit_cogs'])
                    current_stock = int(fg_match['stock_quantity'])
                    
                    unit_price = c_price.number_input("Final Unit Price Charged ($)", value=default_price, min_value=0.0)
                    status = c_status.selectbox("Payment Status", ["Paid", "Pending", "Cancelled"])
                    
                    st.write("---")
                    st.markdown("#### 2. Shipping & Fulfillment Materials")
                    default_f_df = pd.DataFrame([{"Fulfillment Material": "None", "Quantity": 1}])
                    f_edited = st.data_editor(default_f_df, num_rows="dynamic", use_container_width=True, hide_index=True, column_config={"Fulfillment Material": st.column_config.SelectboxColumn("Fulfillment Material", options=pkg_opts, required=True), "Quantity": st.column_config.NumberColumn("Quantity", min_value=1, step=1, required=True)})
                    
                    st.write("---")
                    if st.form_submit_button("Log Order & Deduct All Stock", type="primary", use_container_width=True):
                        if current_stock < qty_sold:
                            st.error(f"⚠️ Warning: You only have {current_stock} units of {sel_product} in stock. Sale aborted.")
                        else:
                            gross = qty_sold * unit_price
                            total_cogs = qty_sold * unit_cogs
                            fulfillment_cost = 0.0
                            pkg_updates = []
                            shortage_flag = False
                            
                            f_needs = {}
                            for _, f_row in f_edited.iterrows():
                                item = f_row.get("Fulfillment Material")
                                q = f_row.get("Quantity")
                                if pd.notna(item) and item != "None" and pd.notna(q):
                                    f_needs[item] = f_needs.get(item, 0) + int(q)
                                        
                            for item, q in f_needs.items():
                                pm_match = packaging[packaging['material_name'] == item]
                                if not pm_match.empty:
                                    pm_id = int(pm_match.iloc[0]['id'])
                                    pm_cost = float(pm_match.iloc[0]['cost_per_unit'])
                                    pm_stock = int(pm_match.iloc[0]['remaining_quantity'])
                                    if pm_stock < q:
                                        shortage_flag = True
                                        st.error(f"⚠️ Not enough '{item}' in Packaging Vault. Sale aborted.")
                                        break
                                    fulfillment_cost += (pm_cost * q)
                                    pkg_updates.append({"id": pm_id, "new_stock": pm_stock - q})
                            
                            if not shortage_flag:
                                total_cogs += fulfillment_cost
                                net = gross - total_cogs
                                gm = (net / gross) if gross > 0 else 0.0
                                
                                new_fp_stock = current_stock - qty_sold
                                supabase.table('finished_products').update({'stock_quantity': new_fp_stock}).eq('id', int(fg_match['id'])).execute()
                                for pu in pkg_updates: supabase.table('packaging').update({'remaining_quantity': pu['new_stock']}).eq('id', pu['id']).execute()
                                
                                supabase.table('sales_records').insert({
                                    "order_description": sel_product, "quantity": qty_sold, "unit_price": unit_price,
                                    "gross_revenue": gross, "cogs": total_cogs, "net_profit": net,
                                    "account": client, "order_ref_number": order_ref,
                                    "sale_date": sale_date.strftime('%Y-%m-%d'), "gm": gm, "channel": channel, "status": status
                                }).execute()
                                
                                st.success(f"Order logged! Deducted {qty_sold} {sel_product} and fulfillment materials from vaults.")
                                time.sleep(1.5); st.rerun()

    # --- 1.5 CONSIGNMENT TRACKER ---
    elif menu == "Consignment Tracker":
        st.title("Consignment Agreements")
        st.markdown("<p style='color: #64748B;'>Manage goods sitting on partner shelves. Consigned goods are deducted from your lab stock but do not count as Revenue until explicitly marked as sold here.</p>", unsafe_allow_html=True)
        
        if not consignment_df.empty:
            active_cons = consignment_df[consignment_df['status'] == 'Active'].copy()
            total_active_units = active_cons['qty_consigned'].sum() - active_cons['qty_sold'].sum()
            total_potential_rev = ((active_cons['qty_consigned'] - active_cons['qty_sold']) * active_cons['wholesale_price']).sum()
            
            col1, col2 = st.columns(2)
            col1.metric("Unsold Units on Partner Shelves", f"{total_active_units:,}")
            col2.metric("Total Potential Payout Revenue", f"${total_potential_rev:,.2f}")
            
            st.write("---")
            st.markdown("#### Active Consignment Ledgers")
            
            display_cons = consignment_df.copy().sort_values('created_at', ascending=False)
            display_cons['Date'] = pd.to_datetime(display_cons['created_at']).dt.strftime('%Y-%m-%d')
            display_cons['Remaining'] = display_cons['qty_consigned'] - display_cons['qty_sold']
            display_cons.insert(0, '🔍', False)
            
            with st.container(border=True):
                edited_cons = st.data_editor(
                    display_cons[['🔍', 'id', 'Date', 'partner_name', 'order_ref_number', 'product_name', 'qty_consigned', 'qty_sold', 'Remaining', 'status']], 
                    use_container_width=True, hide_index=True, 
                    disabled=['id', 'Date', 'partner_name', 'order_ref_number', 'product_name', 'qty_consigned', 'qty_sold', 'Remaining', 'status'],
                    column_config={
                        "id": None
                    }
                )

            selected_cons = edited_cons[edited_cons['🔍'] == True]
            if not selected_cons.empty:
                sel_id = selected_cons.iloc[0]['id']
                cons_item = consignment_df[consignment_df['id'] == sel_id].iloc[0]
                ref_num = cons_item['order_ref_number']
                
                if pd.notna(ref_num) and str(ref_num).strip() != "":
                    batch_items = consignment_df[consignment_df['order_ref_number'] == ref_num]
                else:
                    batch_items = pd.DataFrame([cons_item])
                
                st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### 🤝 Inspecting Consignment: {ref_num if pd.notna(ref_num) else 'Unreferenced'}")
                    st.write(f"**Partner:** {cons_item['partner_name']}")
                    
                    pdf_bytes = generate_consignment_pdf(str(ref_num), batch_items, str(cons_item['partner_name']), pd.to_datetime(cons_item['created_at']).strftime('%Y-%m-%d'))
                    st.download_button(label="📄 Download Official Consignment Agreement PDF", data=pdf_bytes, file_name=f"Consignment_{ref_num}.pdf", mime="application/pdf", use_container_width=True, type="secondary")
                    
                    st.write("---")
                    st.markdown(f"**Log Sales for: {cons_item['product_name']}**")
                    remaining_to_sell = cons_item['qty_consigned'] - cons_item['qty_sold']
                    
                    if remaining_to_sell > 0:
                        with st.form("log_cons_sale"):
                            c1, c2 = st.columns(2)
                            units_sold = c1.number_input("Units Sold by Partner", min_value=1, max_value=int(remaining_to_sell), step=1)
                            payment_status = c2.selectbox("Has the partner paid you for these yet?", ["Pending", "Paid"])
                            
                            if st.form_submit_button("Log as Revenue & Update Consignment", type="primary"):
                                new_qty_sold = cons_item['qty_sold'] + units_sold
                                new_status = "Completed" if new_qty_sold >= cons_item['qty_consigned'] else "Active"
                                
                                supabase.table('consignment_records').update({
                                    'qty_sold': new_qty_sold,
                                    'status': new_status
                                }).eq('id', int(sel_id)).execute()
                                
                                gross_rev = units_sold * cons_item['wholesale_price']
                                cogs = units_sold * cons_item['unit_cogs']
                                net_profit = gross_rev - cogs
                                gm = (net_profit / gross_rev) if gross_rev > 0 else 0.0
                                
                                supabase.table('sales_records').insert({
                                    "order_description": cons_item['product_name'], "quantity": units_sold, "unit_price": cons_item['wholesale_price'],
                                    "gross_revenue": gross_rev, "cogs": cogs, "net_profit": net_profit,
                                    "account": cons_item['partner_name'], "order_ref_number": ref_num,
                                    "sale_date": datetime.today().strftime('%Y-%m-%d'), "gm": gm, "channel": "Consignment Payout", "status": payment_status
                                }).execute()
                                
                                st.success(f"Successfully converted {units_sold} consigned units into Sales Revenue!")
                                time.sleep(1.5); st.rerun()
                    else:
                        st.success("✅ All units from this consignment line have been sold and logged.")
                        
        else:
            st.info("No consignment records found.")

       # Consign New Goods
        st.write("---")
        with st.expander("➕ Consign New Goods (Deducts from Lab Stock)"):
            if not finished_goods.empty:
                
                # --- Auto-Generator for CONS-XXXXXX ---
                next_cons_id = 250  # Changed baseline from 1 to 250
                if not consignment_df.empty:
                    cons_codes = consignment_df['order_ref_number'].astype(str).str.extract(r'CONS-(\d+)')[0].dropna().astype(int)
                    if not cons_codes.empty:
                        # Take the highest number, but ensure it never drops below 250
                        next_cons_id = max(250, cons_codes.max() + 1)
                default_ref = f"CONS-{next_cons_id:06d}"

                with st.form("add_consignment"):
                    st.info("💡 Goods entered here will leave your inventory vault but will NOT count towards Gross Revenue until the partner sells them.")
                    c1, c2, c3 = st.columns(3)
                    
                    partner = c1.text_input("Partner / Retailer Name")
                    ref = c2.text_input("Consignment Ref #", value=default_ref)  # Automatically pre-fills!
                    prod = c3.selectbox("Finished Product", finished_goods['product_name'].tolist())
                    
                    fg_match = finished_goods[finished_goods['product_name'] == prod].iloc[0]
                    def_retail = float(fg_match['retail_price'])
                    def_cogs = float(fg_match['unit_cogs'])
                    curr_stock = int(fg_match['stock_quantity'])
                    
                    c4, c5, c6 = st.columns(3)
                    qty = c4.number_input("Qty to Consign", min_value=1, step=1)
                    retail_p = c5.number_input("Suggested Retail Price ($)", value=def_retail, min_value=0.0)
                    wholesale_p = c6.number_input("Payout to Maker per Unit ($)", value=def_retail * 0.5, min_value=0.0)
                    
                    if st.form_submit_button("Ship Consignment & Deduct Stock", type="primary"):
                        if not partner or not ref:
                            st.error("⚠️ Please provide both the Partner Name and Consignment Ref #.")
                        elif curr_stock < qty:
                            st.error(f"⚠️ You only have {curr_stock} of {prod}. Aborted.")
                        else:
                            # 1. Deduct Stock
                            supabase.table('finished_products').update({'stock_quantity': curr_stock - qty}).eq('id', int(fg_match['id'])).execute()
                            # 2. Add to Consignment
                            supabase.table('consignment_records').insert({
                                "partner_name": partner, "order_ref_number": ref, "product_name": prod,
                                "qty_consigned": qty, "unit_cogs": def_cogs, "retail_price": retail_p, "wholesale_price": wholesale_p
                            }).execute()
                            st.success("Consignment logged securely!")
                            time.sleep(1.5); st.rerun()

    # --- 2. FINANCIAL OVERVIEW ---
    elif menu == "Financial Overview":
        st.title("Financial Overview")
        st.markdown("<p style='color: #64748B;'>Live tracking of physical assets, inventory valuation, and retail projections.</p>", unsafe_allow_html=True)
        st.write("##")
        
        rm_total = (inventory['price_per_kg'] * inventory['quantity_kg']).sum() if not inventory.empty else 0.0
        pm_total = (packaging['cost_per_unit'] * packaging['remaining_quantity']).sum() if not packaging.empty else 0.0
        fp_cogs_total = (finished_goods['unit_cogs'] * finished_goods['stock_quantity']).sum() if not finished_goods.empty else 0.0
        fp_retail_total = (finished_goods['retail_price'] * finished_goods['stock_quantity']).sum() if not finished_goods.empty else 0.0
        
        cons_cogs_total = 0.0
        if not consignment_df.empty:
            active_cons = consignment_df[consignment_df['status'] == 'Active'].copy()
            active_cons['unsold_qty'] = active_cons['qty_consigned'] - active_cons['qty_sold']
            cons_cogs_total = (active_cons['unsold_qty'] * active_cons['unit_cogs']).sum()
        
        vault_assets = rm_total + pm_total + fp_cogs_total + cons_cogs_total
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Raw Materials", f"${rm_total:,.2f}")
        with c2: st.metric("Packaging", f"${pm_total:,.2f}")
        with c3: st.metric("Finished Goods (In Lab)", f"${fp_cogs_total:,.2f}")
        with c4: st.metric("Finished Goods (Consigned)", f"${cons_cogs_total:,.2f}")
        
        st.write("---")
        st.markdown("#### Projected Revenue")
        st.metric("Potential Retail Value on Shelf", f"${fp_retail_total:,.2f}", f"Est. Gross Profit: ${(fp_retail_total - fp_cogs_total):,.2f}")

    # --- 3. BALANCE SHEET GENERATOR ---
    elif menu == "Balance Sheet":
        st.title("Balance Sheet Generator")
        st.markdown("<p style='color: #64748B;'>Generate a professional financial statement summarizing assets, liabilities, and owner's equity.</p>", unsafe_allow_html=True)
        
        rm_total = (inventory['price_per_kg'] * inventory['quantity_kg']).sum() if not inventory.empty else 0.0
        pm_total = (packaging['cost_per_unit'] * packaging['remaining_quantity']).sum() if not packaging.empty else 0.0
        fp_cogs_total = (finished_goods['unit_cogs'] * finished_goods['stock_quantity']).sum() if not finished_goods.empty else 0.0
        
        cons_cogs_total = 0.0
        if not consignment_df.empty:
            active_cons = consignment_df[consignment_df['status'] == 'Active'].copy()
            active_cons['unsold_qty'] = active_cons['qty_consigned'] - active_cons['qty_sold']
            cons_cogs_total = (active_cons['unsold_qty'] * active_cons['unit_cogs']).sum()
        
        total_inv_fg = fp_cogs_total + cons_cogs_total
        
        ar_total = 0.0
        if not sales_records_df.empty:
            ar_total = sales_records_df[sales_records_df['status'] == 'Pending']['gross_revenue'].sum()
            
        with st.form("balance_sheet_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### ASSETS")
                cash = st.number_input("Cash in Bank ($)", min_value=0.0, value=0.0, step=100.0)
                st.write(f"**Accounts Receivable (Pending Sales):** ${ar_total:,.2f}")
                st.write(f"**Inventory (Raw Materials):** ${rm_total:,.2f}")
                st.write(f"**Inventory (Packaging):** ${pm_total:,.2f}")
                st.write(f"**Inventory (Finished Goods + Consigned):** ${total_inv_fg:,.2f}")
                st.write("---")
                fixed_assets = st.number_input("Property & Equipment Value ($)", min_value=0.0, value=0.0, step=100.0)
            with col2:
                st.markdown("#### LIABILITIES")
                accounts_payable = st.number_input("Accounts Payable (Unpaid Bills) ($)", min_value=0.0, value=0.0, step=100.0)
                debt = st.number_input("Short/Long Term Debt ($)", min_value=0.0, value=0.0, step=100.0)
            submit_bs = st.form_submit_button("Calculate & Generate Balance Sheet", type="primary", use_container_width=True)
            
        if submit_bs:
            total_assets = cash + ar_total + rm_total + pm_total + total_inv_fg + fixed_assets
            total_liabilities = accounts_payable + debt
            owner_equity = total_assets - total_liabilities
            
            r1, r2, r3 = st.columns(3)
            r1.metric("Total Assets", f"${total_assets:,.2f}")
            r2.metric("Total Liabilities", f"${total_liabilities:,.2f}")
            r3.metric("Owner's Equity", f"${owner_equity:,.2f}")
            
            if owner_equity == (total_assets - total_liabilities):
                date_str = datetime.today().strftime('%B %d, %Y')
                pdf_bytes = generate_balance_sheet_pdf(date_str, cash, ar_total, rm_total, pm_total, total_inv_fg, fixed_assets, accounts_payable, debt, total_assets, total_liabilities, owner_equity)
                st.download_button("📄 Download Official PDF Balance Sheet", data=pdf_bytes, file_name=f"TherapeuticOils_BalanceSheet_{datetime.today().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)

    # --- 4. RAW MATERIAL LIBRARY ---
    elif menu == "Raw Material Library":
        st.title("Raw Material Library")
        st.markdown("<p style='color: #64748B;'>Manage essential oils, carriers, and active ingredients. Select a material to view its Lot Tracking.</p>", unsafe_allow_html=True)
        if not inventory.empty:
            display_inv = inventory.copy(); display_inv['Cost/g ($)'] = (display_inv['price_per_kg'] / 1000).map('${:,.4f}'.format); display_inv.insert(0, '🔍', False) 
            with st.container(border=True):
                # Disabled quantity_kg so it is strictly driven by the sum of lots
                edited_inv = st.data_editor(display_inv[['🔍', 'rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/g ($)', 'quantity_kg']], use_container_width=True, hide_index=True, disabled=['rm_code', 'Cost/g ($)', 'quantity_kg'])
                if st.button("💾 Synchronize Vault"):
                    for idx, row in edited_inv.iterrows():
                        orig = inventory.loc[idx]
                        if row['trade_name'] != orig['trade_name'] or row['inci_name'] != orig['inci_name'] or row['price_per_kg'] != orig['price_per_kg']:
                            supabase.table('inventory').update({"trade_name": row['trade_name'], "inci_name": row['inci_name'], "price_per_kg": row['price_per_kg']}).eq('id', int(orig['id'])).execute()
                    st.rerun()
            selected_mats = edited_inv[edited_inv['🔍'] == True]
            if not selected_mats.empty:
                mat = inventory.loc[selected_mats.index[0]]; st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### {mat['trade_name']}")
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Code:** {mat['rm_code']}<br>**INCI:** {mat['inci_name']}", unsafe_allow_html=True)
                    c2.write(f"**Total Stock:** {mat['quantity_kg']} Kg<br>**Price:** ${mat['price_per_kg']}/Kg", unsafe_allow_html=True)
                    c3.write(f"**Shelf Value:** ${(mat['price_per_kg'] * mat['quantity_kg']):.2f}")
                    
                   # --- NEW LOT TRACKING SECTION ---
                    st.write("---")
                    st.markdown("#### 📦 Lot Tracking Ledgers")
                    
                    lots = mat.get('lots', [])
                    
                    # Safely handle empty/null lots without crashing Pandas
                    if isinstance(lots, float): lots = []
                    elif isinstance(lots, str) and lots in ["", "nan", "[]"]: lots = []
                    
                    # Auto-generate a default lot if none exist
                    if not lots:
                        today_str = datetime.today().strftime('%Y-%m-%d')
                        exp_str = (datetime.today() + pd.DateOffset(years=2)).strftime('%Y-%m-%d')
                        lots = [{
                            "Lot Number": f"{mat['rm_code']}-L01",
                            "Mfg Date": today_str,
                            "Rcv Date": today_str,
                            "Exp Date": exp_str,
                            "Qty (Kg)": float(mat['quantity_kg']),
                            "Current": True
                        }]
                    
                    lots_df = pd.DataFrame(lots)
                    
                    with st.form(f"lots_form_{mat['id']}"):
                        st.info("💡 Edit quantities, add new lots, and mark exactly ONE lot as 'Current Lot'. Total Stock will auto-update.")
                        ed_lots = st.data_editor(
                            lots_df,
                            num_rows="dynamic",
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Current": st.column_config.CheckboxColumn("Current Lot", default=False),
                                "Mfg Date": st.column_config.TextColumn("Mfg Date (YYYY-MM-DD)"),
                                "Rcv Date": st.column_config.TextColumn("Rcv Date (YYYY-MM-DD)"),
                                "Exp Date": st.column_config.TextColumn("Exp Date (YYYY-MM-DD)"),
                                "Qty (Kg)": st.column_config.NumberColumn("Qty (Kg)", format="%.3f")
                            }
                        )
                        if st.form_submit_button("💾 Save Lots & Update Total Stock", type="primary"):
                            current_count = ed_lots['Current'].sum() if 'Current' in ed_lots.columns else 0
                            if current_count > 1:
                                st.error("⚠️ Only one lot can be marked as the 'Current' lot.")
                            else:
                                new_lots_json = ed_lots.to_dict(orient='records')
                                new_total_kg = ed_lots['Qty (Kg)'].sum() if 'Qty (Kg)' in ed_lots.columns else 0.0
                                
                                supabase.table('inventory').update({
                                    "lots": new_lots_json,
                                    "quantity_kg": float(new_total_kg)
                                }).eq('id', int(mat['id'])).execute()
                                st.success("Lots updated successfully! Total Stock recalculated.")
                                time.sleep(1.5)
                                st.rerun()
                    # --- END LOT TRACKING SECTION ---

                    with st.expander("System Actions"):
                        del_pass = st.text_input("Authorization Passcode", type="password", key="dmp")
                        if st.button("Erase Record") and del_pass == "lab2026":
                            supabase.table('inventory').delete().eq('id', int(mat['id'])).execute(); st.rerun()
        st.write("---")
        with st.expander("➕ Register New Material"):
            with st.form("add_material", clear_on_submit=True):
                c1, c2 = st.columns(2); new_t = c1.text_input("Trade Name"); new_i = c1.text_input("INCI Name"); new_p = c2.number_input("Price/Kg ($)", min_value=0.0); new_q = c2.number_input("Initial Qty (Kg)", min_value=0.0)
                
                st.markdown("**Initial Lot Details**")
                l1, l2, l3, l4 = st.columns(4)
                new_lot = l1.text_input("Lot Number", "L-01")
                new_mfg = l2.date_input("Mfg Date")
                new_rcv = l3.date_input("Rcv Date")
                new_exp = l4.date_input("Exp Date", value=datetime.today() + pd.DateOffset(years=2))

                if st.form_submit_button("Register") and new_t != "":
                    next_id = 1 if inventory.empty else int(inventory['id'].max()) + 1
                    rm_code = f"RM{next_id:05d}"
                    
                    init_lot = [{
                        "Lot Number": new_lot,
                        "Mfg Date": new_mfg.strftime('%Y-%m-%d'),
                        "Rcv Date": new_rcv.strftime('%Y-%m-%d'),
                        "Exp Date": new_exp.strftime('%Y-%m-%d'),
                        "Qty (Kg)": float(new_q),
                        "Current": True
                    }]
                    
                    supabase.table('inventory').insert({
                        "rm_code": rm_code, 
                        "trade_name": new_t, 
                        "inci_name": new_i, 
                        "price_per_kg": new_p, 
                        "quantity_kg": new_q, 
                        "lots": init_lot
                    }).execute(); st.rerun()

    # --- 5. PACKAGING LIBRARY ---
    elif menu == "Packaging Library":
        st.title("Packaging Library")
        st.markdown("<p style='color: #64748B;'>Track bottles, droppers, caps, and labels.</p>", unsafe_allow_html=True)
        if not packaging.empty:
            display_pk = packaging.copy(); display_pk.insert(0, '🔍', False)
            with st.container(border=True):
                edited_pk = st.data_editor(display_pk[['🔍', 'pm_code', 'material_name', 'supplier', 'cost_per_unit', 'remaining_quantity']], use_container_width=True, hide_index=True, disabled=['pm_code'])
                if st.button("💾 Synchronize Vault"):
                    for idx, row in edited_pk.iterrows():
                        orig = packaging.loc[idx]
                        if row['material_name'] != orig['material_name'] or row['supplier'] != orig['supplier'] or row['cost_per_unit'] != orig['cost_per_unit'] or row['remaining_quantity'] != orig['remaining_quantity']:
                            supabase.table('packaging').update({"material_name": row['material_name'], "supplier": row['supplier'], "cost_per_unit": row['cost_per_unit'], "remaining_quantity": row['remaining_quantity']}).eq('id', int(orig['id'])).execute()
                    st.rerun()
            selected_pk = edited_pk[edited_pk['🔍'] == True]
            if not selected_pk.empty:
                p_mat = packaging.loc[selected_pk.index[0]]; st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### {p_mat['material_name']}")
                    st.write(f"**Code:** {p_mat['pm_code']} | **Supplier:** {p_mat['supplier']} | **Stock:** {p_mat['remaining_quantity']} Units")
                    with st.expander("System Actions"):
                        if st.button("Erase Record") and st.text_input("Authorization", type="password", key="dpp") == "lab2026":
                            supabase.table('packaging').delete().eq('id', int(p_mat['id'])).execute(); st.rerun()
        st.write("---")
        with st.expander("➕ Register New Packaging"):
            with st.form("add_packaging", clear_on_submit=True):
                c1, c2 = st.columns(2); p_n = c1.text_input("Material Name"); p_s = c1.text_input("Supplier"); p_c = c2.number_input("Cost/Unit ($)", min_value=0.0); p_q = c2.number_input("Initial Qty", min_value=0.0)
                if st.form_submit_button("Register") and p_n != "":
                    next_pm = 1 if packaging.empty else int(packaging['id'].max()) + 1
                    supabase.table('packaging').insert({"pm_code": f"PM{next_pm:05d}", "material_name": p_n, "supplier": p_s, "cost_per_unit": p_c, "remaining_quantity": p_q}).execute(); st.rerun()

    # --- 6. FINISHED PRODUCTS LIBRARY ---
    elif menu == "Finished Products":
        st.title("Finished Products")
        st.markdown("<p style='color: #64748B;'>Manage retail-ready inventory directly from your saved COGS profiles.</p>", unsafe_allow_html=True)
        
        if not finished_goods.empty:
            display_fp = finished_goods.copy()
            display_fp.insert(0, '🔍', False)
            
            st.write("💡 *Edit stock quantities directly in the table below.*")
            with st.container(border=True):
                edited_fp = st.data_editor(
                    display_fp[['🔍', 'fp_code', 'product_name', 'stock_quantity', 'unit_cogs', 'retail_price']],
                    use_container_width=True, hide_index=True, disabled=['fp_code', 'unit_cogs', 'retail_price'],
                    column_config={
                        "unit_cogs": st.column_config.NumberColumn("Unit COGS", format="$%.2f"),
                        "retail_price": st.column_config.NumberColumn("Retail Price", format="$%.2f")
                    }
                )
                
                if st.button("💾 Synchronize Vault", type="primary"):
                    for idx, row in edited_fp.iterrows():
                        orig = finished_goods.loc[idx]
                        if row['stock_quantity'] != orig['stock_quantity']:
                            supabase.table('finished_products').update({
                                "stock_quantity": row['stock_quantity']
                            }).eq('id', int(orig['id'])).execute()
                    st.success("Finished goods synced!")
                    st.rerun()

            selected_fp = edited_fp[edited_fp['🔍'] == True]
            if not selected_fp.empty:
                fp_item = finished_goods.loc[selected_fp.index[0]]
                st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### {fp_item['product_name']}")
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Code:** {fp_item['fp_code']}")
                    c2.write(f"**In Stock:** {fp_item['stock_quantity']} Units")
                    
                    margin = ((fp_item['retail_price'] - fp_item['unit_cogs']) / fp_item['retail_price'] * 100) if fp_item['retail_price'] > 0 else 0
                    c3.write(f"**Profit Margin:** {margin:.1f}%")
                    
                    with st.expander("System Actions"):
                        if st.button("Erase Record") and st.text_input("Authorization Passcode", type="password", key="dfpp") == "lab2026":
                            supabase.table('finished_products').delete().eq('id', int(fp_item['id'])).execute(); st.rerun()
        else:
            st.info("No finished products currently in stock.")

        st.write("---")
        with st.expander("➕ Log New Finished Product Batch"):
            if not cogs_records_df.empty:
                with st.form("add_fp", clear_on_submit=True):
                    c1, c2 = st.columns([2, 1])
                    cogs_opts = [f"[{r['id']}] {r['product_name']}" for _, r in cogs_records_df.iterrows()]
                    sel_cogs = c1.selectbox("Select Target Product (From COGS Vault)", cogs_opts)
                    fp_q = c2.number_input("Bottles Produced (Qty)", min_value=1, value=10, step=1)
                    
                    if st.form_submit_button("Add to Stock"):
                        cogs_id = int(sel_cogs.split("]")[0].replace("[", ""))
                        matched_cogs = cogs_records_df[cogs_records_df['id'] == cogs_id].iloc[0]
                        target_name = matched_cogs['product_name']
                        target_cogs = float(matched_cogs['total_cogs'])
                        target_retail = float(matched_cogs['target_retail'])
                        
                        if not finished_goods.empty and target_name in finished_goods['product_name'].values:
                            existing_product = finished_goods[finished_goods['product_name'] == target_name]
                            existing_id = int(existing_product.iloc[0]['id'])
                            new_qty = int(existing_product.iloc[0]['stock_quantity']) + fp_q
                            supabase.table('finished_products').update({"stock_quantity": new_qty, "unit_cogs": target_cogs, "retail_price": target_retail}).eq('id', existing_id).execute()
                        else:
                            next_fp = 1 if finished_goods.empty else int(finished_goods['id'].max()) + 1
                            supabase.table('finished_products').insert({"fp_code": f"FP{next_fp:05d}", "product_name": target_name, "stock_quantity": fp_q, "unit_cogs": target_cogs, "retail_price": target_retail}).execute()
                        st.rerun()
            else:
                st.warning("⚠️ You need to architect and save a product profile in the **COGS Calculator** before you can log it to your finished inventory.")

    # --- 7. FORMULA HUB / R&D ---
    elif menu == "Formula Hub":
        st.title("The Formula Hub")
        st.markdown("<p style='color: #64748B;'>Design, calculate, execute, and version control batch productions.</p>", unsafe_allow_html=True)
        
        if not formulas_df.empty:
            formulas_df['base_code'] = formulas_df['fr_code'].apply(lambda x: str(x).split('-')[0])
            summary_df = formulas_df.sort_values(by='fr_code').drop_duplicates(subset=['base_code'], keep='first').copy()
            summary_df['Family Name'] = summary_df['formula_name'].apply(lambda x: re.sub(r' V\d+$', '', str(x)))
            
            st.write("💡 *Select a Formula Family below to inspect its editions and execute production.*")
            f_select = st.dataframe(summary_df[['base_code', 'Family Name']], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

            if f_select.selection.rows:
                sel_base = summary_df.iloc[f_select.selection.rows[0]]['base_code']
                family_editions = formulas_df[formulas_df['base_code'] == sel_base].sort_values(by='fr_code', ascending=False)
                
                st.write("##")
                with st.container(border=True):
                    if len(family_editions) > 1:
                        edition_opts = [f"[{r['fr_code']}] {r['formula_name']}" for _, r in family_editions.iterrows()]
                        sel_edition_str = st.selectbox("📌 Select Specific Edition:", edition_opts)
                        sel_fr_code = sel_edition_str.split("]")[0].replace("[", "")
                        sel_f = family_editions[family_editions['fr_code'] == sel_fr_code].iloc[0]
                    else:
                        sel_f = family_editions.iloc[0]
                        st.markdown(f"#### ⚗️ {sel_f['fr_code']} - {sel_f['formula_name']}")
                        
                    recipe_data = sel_f['recipe']
                    
                    if isinstance(recipe_data, dict):
                        recipe_items = [{"Phase": "A", "Ingredient": k, "%": v} for k, v in recipe_data.items()]
                    elif isinstance(recipe_data, list):
                        recipe_items = []
                        for item in recipe_data:
                            if "Phase" not in item: item["Phase"] = "A"
                            recipe_items.append(item)
                    else:
                        recipe_items = []
                    
                    st.write("---")
                    b_size = st.number_input("Target Batch Size (grams)", min_value=1.0, value=1000.0, step=100.0)
                    st.write("---")
                    
                    calc_data = []; stock_ok = True; total_cost = 0.0
                    for row in recipe_items:
                        ing = row.get('Ingredient'); p = row.get('%', 0); phase = row.get('Phase', 'A')
                        req_g = (p/100) * b_size
                        m = inventory[inventory['trade_name'] == ing]
                        if not m.empty:
                            s_kg = float(m['quantity_kg'].values[0]); p_kg = float(m['price_per_kg'].values[0])
                            if s_kg < (req_g/1000): stock_ok = False
                            cost = (req_g/1000)*p_kg; total_cost += cost
                            calc_data.append({"Phase": phase, "Material": ing, "Formula %": f"{p}%", "Needed (g)": f"{req_g:.2f}", "Stock Status": "✅ Available" if s_kg >= (req_g/1000) else "❌ Shortage", "Est. Cost": f"${cost:.4f}", "req_kg": req_g/1000, "stock_kg": s_kg})
                        else:
                            stock_ok = False
                            calc_data.append({"Phase": phase, "Material": ing, "Formula %": f"{p}%", "Needed (g)": f"{req_g:.2f}", "Stock Status": "⚠️ Not in Vault", "Est. Cost": "$0.00", "req_kg": 0, "stock_kg": 0})
                    
                    calc_df = pd.DataFrame(calc_data)
                    if not calc_df.empty:
                        st.dataframe(calc_df.sort_values(by="Phase")[['Phase', 'Material', 'Formula %', 'Needed (g)', 'Stock Status', 'Est. Cost']], use_container_width=True, hide_index=True)
                    
                    st.write("---")
                    st.markdown("#### 📋 Manufacturing Procedure")
                    proc_text = sel_f.get('procedure', 'No written procedure documented for this formula.')
                    if pd.isna(proc_text) or str(proc_text).strip() == "": proc_text = "No written procedure documented for this formula."
                    st.info(proc_text)
                    st.write("---")
                    
                    col_cost, col_btn = st.columns([1, 1])
                    col_cost.metric("Projected Batch Cost", f"${total_cost:.2f}")
                    with col_btn:
                        st.write("<br>", unsafe_allow_html=True)
                        if st.button("🚀 Execute Production", type="primary", use_container_width=True):
                            if stock_ok:
                                l_r = supabase.table('production_records').select("id").order("id", desc=True).limit(1).execute()
                                n_id = 1 if not l_r.data else l_r.data[0]['id'] + 1
                                b_no, l_no = f"B-{n_id:05d}", f"LOT-{datetime.now().strftime('%Y%m%d')}-{n_id:02d}"
                                for d in calc_data:
                                    supabase.table('inventory').update({'quantity_kg': d['stock_kg'] - d['req_kg']}).eq('trade_name', d['Material']).execute()
                                supabase.table('production_records').insert({"fr_code": sel_f['fr_code'], "formula_name": sel_f['formula_name'], "batch_number": b_no, "lot_number": l_no, "batch_size_g": b_size, "total_cost": total_cost}).execute()
                                st.balloons(); st.rerun()
                            else: st.error("Cannot produce: Material Shortage detected.")
                    
                    st.divider()
                    c_act1, c_act2, c_act3 = st.columns(3)
                    with c_act1:
                        with st.expander("✏️ Edit Current Edition"):
                            if st.button("Edit This Version", use_container_width=True):
                                st.session_state.builder = pd.DataFrame(recipe_items)
                                st.session_state.draft_name = sel_f['formula_name']
                                st.session_state.draft_procedure = str(proc_text) if proc_text != "No written procedure documented for this formula." else ""
                                st.session_state.edit_formula_id = int(sel_f['id'])
                                st.session_state.edit_fr_code = sel_f['fr_code']
                                if "base_fr_code" in st.session_state: del st.session_state["base_fr_code"]
                                st.rerun()
                    with c_act2:
                        with st.expander("🔄 Create New Edition"):
                            if st.button("Draft New Version", use_container_width=True):
                                st.session_state.builder = pd.DataFrame(recipe_items)
                                match = re.search(r' V(\d+)$', sel_f['formula_name'])
                                if match:
                                    new_v = int(match.group(1)) + 1
                                    new_name = re.sub(r' V\d+$', f' V{new_v}', sel_f['formula_name'])
                                else:
                                    new_name = f"{sel_f['formula_name']} V2"
                                st.session_state.draft_name = new_name
                                st.session_state.base_fr_code = sel_f['fr_code']
                                st.session_state.draft_procedure = str(proc_text) if proc_text != "No written procedure documented for this formula." else ""
                                if "edit_formula_id" in st.session_state: del st.session_state["edit_formula_id"]
                                st.rerun()
                    with c_act3:
                        with st.expander("🗑️ Erase Formula"):
                            del_f_pass = st.text_input("Authorization Passcode", type="password", key="dfp")
                            if st.button("Permanently Delete", use_container_width=True) and del_f_pass == "lab2026":
                                supabase.table('formulas').delete().eq('id', int(sel_f['id'])).execute(); st.rerun()
        else:
            st.info("No formulas architected yet.")

        st.write("---")
        with st.expander("⚙️ Architect Formula Builder", expanded=True):
            c_build, c_metrics = st.columns([3, 2])
            with c_build:
                if "edit_formula_id" in st.session_state:
                    st.markdown(f"<span style='color: #0F172A; font-size: 0.85rem; font-weight: 600;'>✏️ EDITING MODE: Overwriting {st.session_state.edit_fr_code}</span>", unsafe_allow_html=True)
                    if st.button("❌ Cancel Edit & Start Fresh"):
                        st.session_state.builder = pd.DataFrame([{"Phase": "A", "Ingredient": None, "%": 0.0}])
                        for key in ["draft_name", "edit_formula_id", "edit_fr_code", "draft_procedure"]:
                            if key in st.session_state: del st.session_state[key]
                        st.rerun()
                    st.write("")
                elif "base_fr_code" in st.session_state:
                    base_disp = st.session_state.base_fr_code.split('-')[0]
                    st.markdown(f"<span style='color: #0F172A; font-size: 0.85rem; font-weight: 600;'>🔗 NEW EDITION MODE: Linked to Parent {base_disp}</span>", unsafe_allow_html=True)
                    if st.button("❌ Cancel Edition & Start Fresh"):
                        st.session_state.builder = pd.DataFrame([{"Phase": "A", "Ingredient": None, "%": 0.0}])
                        for key in ["draft_name", "base_fr_code", "draft_procedure"]:
                            if key in st.session_state: del st.session_state[key]
                        st.rerun()
                    st.write("")
                
                f_name = st.text_input("Formula Moniker", value=st.session_state.get("draft_name", ""), placeholder="e.g., Actiflam Hair Growth Oil")
                
                if "builder" not in st.session_state: 
                    st.session_state.builder = pd.DataFrame([{"Phase": "A", "Ingredient": None, "%": 0.0}])
                
                ing_options = inventory['trade_name'].tolist() if not inventory.empty else ["No materials registered"]
                
                edit_df = st.data_editor(
                    st.session_state.builder, 
                    num_rows="dynamic", 
                    use_container_width=True, 
                    column_config={
                        "Phase": st.column_config.SelectboxColumn("Phase", options=["A", "B", "C", "D", "E", "F"], required=True),
                        "Ingredient": st.column_config.SelectboxColumn("Ingredient", options=ing_options, required=True)
                    }
                )
                
                procedure_text = st.text_area(
                    "Manufacturing Procedure", 
                    value=st.session_state.get("draft_procedure", ""),
                    placeholder="1. Heat Phase A to 75°C...",
                    height=150
                )
            
            with c_metrics:
                st.write("<div style='margin-top: 2.2rem;'></div>", unsafe_allow_html=True)
                total_cost_kg = 0.0; live_data = []
                for _, row in edit_df.iterrows():
                    ing = row.get('Ingredient'); perc = row.get('%', 0.0); phase = row.get('Phase', 'A')
                    if ing and pd.notna(ing) and ing in inventory['trade_name'].values:
                        price = float(inventory[inventory['trade_name'] == ing]['price_per_kg'].values[0])
                        cost_contrib = (perc / 100.0) * price; total_cost_kg += cost_contrib
                        live_data.append({"Phase": phase, "Material": ing, "Cost": f"${cost_contrib:,.2f}"})
                
                if live_data: 
                    st.dataframe(pd.DataFrame(live_data).sort_values('Phase'), use_container_width=True, hide_index=True)
                else: 
                    st.info("Select ingredients to see live costs.")
                    
                st.metric("Total Formula Cost / Kg", f"${total_cost_kg:,.2f}")
                total_perc = edit_df["%"].sum() if "%" in edit_df.columns else 0.0
                
                if round(total_perc, 2) == 100.0:
                    st.success("✅ Formula is balanced (100%)")
                    btn_label = "💾 Update Existing Edition" if "edit_formula_id" in st.session_state else "Commit Formula to Vault"
                    if st.button(btn_label, type="primary", use_container_width=True) and f_name:
                        recipe_json = edit_df.to_dict(orient='records')
                        if "edit_formula_id" in st.session_state:
                            supabase.table("formulas").update({
                                "formula_name": f_name, "recipe": recipe_json, "procedure": procedure_text
                            }).eq('id', st.session_state.edit_formula_id).execute()
                        else:
                            if "base_fr_code" in st.session_state:
                                base_code = st.session_state.base_fr_code.split('-')[0]
                                existing_v_count = formulas_df[formulas_df['fr_code'].str.startswith(base_code)].shape[0]
                                fr_c = f"{base_code}-{existing_v_count + 1}"
                            else:
                                if formulas_df.empty:
                                    fr_c = "FR00001"
                                else:
                                    root_codes = formulas_df['fr_code'].str.extract(r'FR(\d{5})')[0].dropna().astype(int)
                                    next_id = root_codes.max() + 1 if not root_codes.empty else 1
                                    fr_c = f"FR{next_id:05d}"
                            
                            supabase.table("formulas").insert({"fr_code": fr_c, "formula_name": f_name, "recipe": recipe_json, "procedure": procedure_text}).execute()
                            
                        st.session_state.builder = pd.DataFrame([{"Phase": "A", "Ingredient": None, "%": 0.0}])
                        for key in ["draft_name", "base_fr_code", "draft_procedure", "edit_formula_id", "edit_fr_code"]:
                            if key in st.session_state: del st.session_state[key]
                        st.rerun()
                else: st.warning(f"⚠️ Total: {total_perc}% (Must equal 100%)")

    # --- 8. COGS CALCULATOR ---
    elif menu == "COGS Calculator":
        st.title("Cost of Goods Sold (COGS)")
        st.markdown("<p style='color: #64748B;'>Calculate unit economics and profile profit margins.</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("#### Step 1: Physical Product Specs")
            c1, c2, c3 = st.columns(3)
            
            if not formulas_df.empty:
                f_opts = [f"[{r['fr_code']}] {r['formula_name']}" for _, r in formulas_df.iterrows()]
                sel_form = c1.selectbox("Base Formula", f_opts)
            else:
                sel_form = None; c1.warning("No formulas in vault.")
                
            fill_wt = c2.number_input("Fill Weight per Unit (grams)", min_value=1.0, value=30.0, step=5.0)
            
            if not packaging.empty:
                p_opts = [f"[{r['pm_code']}] {r['material_name']}" for _, r in packaging.iterrows()]
                p_opts.insert(0, "None / Custom")
                sel_pack = c3.selectbox("Primary Packaging", p_opts)
            else:
                sel_pack = "None / Custom"; c3.warning("No packaging in vault.")

        with st.container(border=True):
            st.markdown("#### Step 2: Component & Variable Costs (per unit)")
            cm1, cm2, cm3, cm4 = st.columns(4)
            cost_mfg = cm1.number_input("Labor / Mfg ($)", min_value=0.0, value=0.10, step=0.05)
            cost_lbl = cm2.number_input("Label Cost ($)", min_value=0.0, value=0.05, step=0.05)
            cost_sec = cm3.number_input("Secondary Box ($)", min_value=0.0, value=0.00, step=0.05)
            cost_ter = cm4.number_input("Tertiary/Carton ($)", min_value=0.0, value=0.00, step=0.05)

        st.write("##")

        bulk_cost = 0.0
        n_only = ""
        if sel_form:
            n_only = sel_form.split("] ")[1]
            rec = formulas_df[formulas_df['formula_name'] == n_only].iloc[0]['recipe']
            if isinstance(rec, dict):
                rec_items = [{"Ingredient": k, "%": v} for k, v in rec.items()]
            elif isinstance(rec, list):
                rec_items = rec
            else:
                rec_items = []
                
            for row in rec_items:
                ing = row.get('Ingredient'); p = row.get('%', 0)
                req_g = (p/100) * fill_wt
                m = inventory[inventory['trade_name'] == ing]
                if not m.empty:
                    p_kg = float(m['price_per_kg'].values[0])
                    bulk_cost += (req_g/1000) * p_kg

        pack_cost = 0.0
        if sel_pack != "None / Custom":
            p_only = sel_pack.split("] ")[1]
            pack_cost = float(packaging[packaging['material_name'] == p_only].iloc[0]['cost_per_unit'])

        total_cogs = bulk_cost + pack_cost + cost_mfg + cost_lbl + cost_sec + cost_ter

        st.markdown("#### Cost Breakdown & Profit Margin")
        r1, r2 = st.columns([2, 1])
        with r1:
            st.dataframe(pd.DataFrame([
                {"Component": "Formula (Bulk Oil)", "Cost per Unit": f"${bulk_cost:.4f}"},
                {"Component": "Primary Bottle/Dropper", "Cost per Unit": f"${pack_cost:.4f}"},
                {"Component": "Labeling", "Cost per Unit": f"${cost_lbl:.4f}"},
                {"Component": "Secondary Packaging", "Cost per Unit": f"${cost_sec:.4f}"},
                {"Component": "Tertiary Packaging", "Cost per Unit": f"${cost_ter:.4f}"},
                {"Component": "Labor / Mfg Overhead", "Cost per Unit": f"${cost_mfg:.4f}"}
            ]), use_container_width=True, hide_index=True)
            
        with r2:
            with st.container(border=True):
                st.metric("Total COGS per Unit", f"${total_cogs:.2f}")
                target_retail = st.number_input("Target Retail Price ($)", min_value=0.0, value=total_cogs * 4 if total_cogs > 0 else 0.0, step=1.0)
                margin_pct = 0.0
                if target_retail > 0:
                    gross_profit = target_retail - total_cogs
                    margin_pct = (gross_profit / target_retail) * 100
                    st.write("---")
                    st.metric("Gross Profit", f"${gross_profit:.2f}", f"{margin_pct:.1f}% Margin")

        st.write("##")
        with st.container(border=True):
            st.markdown("#### 💾 Save COGS Configuration")
            sc1, sc2 = st.columns([3, 1])
            cogs_name = sc1.text_input("Product Name / SKU", placeholder="e.g., Actiflam 30ml Retail Bottle")
            sc2.write("<br>", unsafe_allow_html=True)
            if sc2.button("Commit Profile to Vault", type="primary", use_container_width=True):
                if cogs_name:
                    supabase.table('cogs_records').insert({
                        "product_name": cogs_name, "formula_name": n_only if sel_form else "None",
                        "fill_weight_g": fill_wt, "primary_packaging": sel_pack.split("] ")[1] if sel_pack != "None / Custom" else "Custom",
                        "bulk_cost": bulk_cost, "packaging_cost": pack_cost, "mfg_cost": cost_mfg, "label_cost": cost_lbl,
                        "total_cogs": total_cogs, "target_retail": target_retail, "gross_margin_pct": margin_pct
                    }).execute()
                    st.success(f"Saved profile: {cogs_name}")
                    st.rerun()
                else:
                    st.error("Please enter a Product Name before saving.")

        st.write("---")
        st.markdown("#### 📂 Saved COGS Profiles")
        if not cogs_records_df.empty:
            display_cogs = cogs_records_df.copy()
            display_cogs['Date'] = pd.to_datetime(display_cogs['created_at']).dt.strftime('%Y-%m-%d')
            display_cogs.insert(0, '🔍', False)
            with st.container(border=True):
                edited_cogs = st.data_editor(
                    display_cogs[['🔍', 'Date', 'product_name', 'formula_name', 'fill_weight_g', 'total_cogs', 'target_retail', 'gross_margin_pct']],
                    use_container_width=True, hide_index=True, disabled=['Date', 'formula_name', 'fill_weight_g', 'total_cogs', 'gross_margin_pct'],
                    column_config={
                        "total_cogs": st.column_config.NumberColumn("Total COGS", format="$%.2f"),
                        "target_retail": st.column_config.NumberColumn("Target Retail", format="$%.2f"),
                        "gross_margin_pct": st.column_config.NumberColumn("Margin %", format="%.1f%%")
                    }
                )
                if st.button("💾 Synchronize COGS Vault", type="primary"):
                    for index, row in edited_cogs.iterrows():
                        orig = cogs_records_df.loc[index]
                        if row['product_name'] != orig['product_name'] or row['target_retail'] != orig['target_retail']:
                            new_retail = float(row['target_retail'])
                            new_cogs = float(orig['total_cogs'])
                            new_margin = ((new_retail - new_cogs) / new_retail * 100) if new_retail > 0 else 0.0
                            supabase.table('cogs_records').update({"product_name": row['product_name'], "target_retail": new_retail, "gross_margin_pct": new_margin}).eq('id', int(orig['id'])).execute()
                    st.success("COGS profiles synced!")
                    st.rerun()
            selected_cogs = edited_cogs[edited_cogs['🔍'] == True]
            if not selected_cogs.empty:
                cogs_item = cogs_records_df.loc[selected_cogs.index[0]]
                st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### {cogs_item['product_name']}")
                    st.write(f"**Base Formula:** {cogs_item['formula_name']} ({cogs_item['fill_weight_g']}g fill)")
                    st.write(f"**Primary Packaging:** {cogs_item['primary_packaging']}")
                    with st.expander("System Actions"):
                        del_cogs_pass = st.text_input("Authorization Passcode", type="password", key="dcogsp")
                        if st.button("Erase COGS Profile"):
                            if del_cogs_pass == "lab2026":
                                supabase.table('cogs_records').delete().eq('id', int(cogs_item['id'])).execute(); st.rerun()
                            else: st.error("Incorrect passcode.")
        else: st.info("No COGS profiles saved in the vault.")

    # --- 9. PRODUCTION LOGS (WITH LABELS) ---
    elif menu == "Production Logs":
        st.title("Production Logs")
        st.markdown("<p style='color: #64748B;'>GMP-compliant traceability records & Physical Batch Labels.</p>", unsafe_allow_html=True)
        
        logs = supabase.table('production_records').select("*").order("created_at", desc=True).execute()
        if logs.data:
            df = pd.DataFrame(logs.data)
            df['Date'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Label Generator Integration
            disp_logs = df.copy()
            disp_logs.insert(0, '🏷️', False)
            
            st.write("💡 *Check the box next to any batch to generate its GMP physical labels.*")
            with st.container(border=True):
                edited_logs = st.data_editor(
                    disp_logs[['🏷️', 'id', 'Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g', 'total_cost']], 
                    use_container_width=True, hide_index=True, 
                    disabled=['id', 'Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g', 'total_cost'], 
                    column_config={"id": None}
                )
            
            sel_logs = edited_logs[edited_logs['🏷️'] == True]
            if not sel_logs.empty:
                s_log = df[df['id'] == sel_logs.iloc[0]['id']].iloc[0]
                
                st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### 🖨️ Label Generator: {s_log['batch_number']}")
                    st.write(f"**Formula:** {s_log['formula_name']} | **Lot:** {s_log['lot_number']} | **Size:** {s_log['batch_size_g']}g")
                    
                    pdf_bytes = generate_batch_labels_pdf(
                        s_log['formula_name'], 
                        s_log['batch_number'], 
                        s_log['lot_number'], 
                        pd.to_datetime(s_log['created_at']).strftime('%Y-%m-%d')
                    )
                    
                    st.download_button(
                        label="📄 Download GMP Batch Label Sheet (PDF)", 
                        data=pdf_bytes, 
                        file_name=f"Labels_{s_log['batch_number']}.pdf", 
                        mime="application/pdf", 
                        use_container_width=True,
                        type="primary"
                    )
        else: 
            st.info("No records found in the vault.")
