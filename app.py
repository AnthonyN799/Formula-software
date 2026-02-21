import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from PIL import Image

# --- 1. PAGE CONFIGURATION ---
try:
    logo_img = Image.open("logo.jpg")
    st.set_page_config(page_title="Therapeutic Oils | Lab Portal", page_icon=logo_img, layout="wide", initial_sidebar_state="expanded")
except FileNotFoundError:
    st.set_page_config(page_title="Therapeutic Oils | Lab Portal", layout="wide", initial_sidebar_state="expanded")

# --- 2. CUSTOM CSS FOR PREMIUM UI ---
def inject_custom_css():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
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
    
    with st.sidebar:
        try: st.image("logo.jpg", use_container_width=True)
        except: st.markdown("<h3 style='text-align: center; padding-bottom: 20px;'>T / O</h3>", unsafe_allow_html=True)
        st.write("##")
        menu = st.radio("System Menu", ["Financial Overview", "Raw Material Library", "Packaging Library", "Formula Hub", "Production Logs"])
        st.write("<br><br>", unsafe_allow_html=True)
        if st.button("Log Out", use_container_width=True): st.session_state["authenticated"] = False; st.rerun()

    # --- Fetch Global Data ---
    inv_resp = supabase.table('inventory').select("*").execute()
    inventory = pd.DataFrame(inv_resp.data).sort_values('rm_code') if inv_resp.data else pd.DataFrame()
    pk_resp = supabase.table('packaging').select("*").execute()
    packaging = pd.DataFrame(pk_resp.data).sort_values('pm_code') if pk_resp.data else pd.DataFrame()

    # --- 1. FINANCIAL OVERVIEW ---
    if menu == "Financial Overview":
        st.title("Financial Overview")
        st.markdown("<p style='color: #64748B;'>Live tracking of physical assets and inventory valuation.</p>", unsafe_allow_html=True)
        st.write("##")
        rm_total = (inventory['price_per_kg'] * inventory['quantity_kg']).sum() if not inventory.empty else 0.0
        pm_total = (packaging['cost_per_unit'] * packaging['remaining_quantity']).sum() if not packaging.empty else 0.0
        
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Raw Materials Inventory", f"${rm_total:,.2f}")
        with col2: st.metric("Packaging Inventory", f"${pm_total:,.2f}")
        with col3: st.metric("Total Vault Assets", f"${(rm_total + pm_total):,.2f}")
        st.write("---")
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("#### High-Value Materials")
            if not inventory.empty:
                inv_chart = inventory.copy(); inv_chart['Total Value ($)'] = inv_chart['price_per_kg'] * inv_chart['quantity_kg']
                st.dataframe(inv_chart.sort_values(by="Total Value ($)", ascending=False).head(5)[['trade_name', 'Total Value ($)']], use_container_width=True, hide_index=True)
        with c_right:
            st.markdown("#### High-Value Packaging")
            if not packaging.empty:
                pk_chart = packaging.copy(); pk_chart['Total Value ($)'] = pk_chart['cost_per_unit'] * pk_chart['remaining_quantity']
                st.dataframe(pk_chart.sort_values(by="Total Value ($)", ascending=False).head(5)[['material_name', 'Total Value ($)']], use_container_width=True, hide_index=True)

    # --- 2. RAW MATERIAL LIBRARY ---
    elif menu == "Raw Material Library":
        st.title("Raw Material Library")
        st.markdown("<p style='color: #64748B;'>Manage essential oils, carriers, and active ingredients.</p>", unsafe_allow_html=True)
        if not inventory.empty:
            display_inv = inventory.copy()
            display_inv['Cost/g ($)'] = (display_inv['price_per_kg'] / 1000).map('${:,.4f}'.format)
            display_inv.insert(0, '🔍', False) 
            with st.container(border=True):
                edited_inv = st.data_editor(display_inv[['🔍', 'rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/g ($)', 'quantity_kg']], use_container_width=True, hide_index=True, disabled=['rm_code', 'Cost/g ($)'])
                if st.button("💾 Synchronize Vault"):
                    for idx, row in edited_inv.iterrows():
                        orig = inventory.loc[idx]
                        if row['trade_name'] != orig['trade_name'] or row['inci_name'] != orig['inci_name'] or row['price_per_kg'] != orig['price_per_kg'] or row['quantity_kg'] != orig['quantity_kg']:
                            supabase.table('inventory').update({"trade_name": row['trade_name'], "inci_name": row['inci_name'], "price_per_kg": row['price_per_kg'], "quantity_kg": row['quantity_kg']}).eq('id', int(orig['id'])).execute()
                    st.rerun()
            selected_mats = edited_inv[edited_inv['🔍'] == True]
            if not selected_mats.empty:
                mat = inventory.loc[selected_mats.index[0]]
                st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### {mat['trade_name']}")
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Code:** {mat['rm_code']}<br>**INCI:** {mat['inci_name']}", unsafe_allow_html=True)
                    c2.write(f"**Stock:** {mat['quantity_kg']} Kg<br>**Price:** ${mat['price_per_kg']}/Kg", unsafe_allow_html=True)
                    c3.write(f"**Shelf Value:** ${(mat['price_per_kg'] * mat['quantity_kg']):.2f}")
                    with st.expander("System Actions"):
                        del_pass = st.text_input("Authorization Passcode", type="password", key="dmp")
                        if st.button("Erase Record") and del_pass == "lab2026":
                            supabase.table('inventory').delete().eq('id', int(mat['id'])).execute(); st.rerun()
        st.write("---")
        with st.expander("➕ Register New Material"):
            with st.form("add_material", clear_on_submit=True):
                c1, c2 = st.columns(2); new_t = c1.text_input("Trade Name"); new_i = c1.text_input("INCI Name"); new_p = c2.number_input("Price/Kg ($)", min_value=0.0); new_q = c2.number_input("Initial Qty (Kg)", min_value=0.0)
                if st.form_submit_button("Register") and new_t != "":
                    next_id = 1 if inventory.empty else int(inventory['id'].max()) + 1
                    supabase.table('inventory').insert({"rm_code": f"RM{next_id:05d}", "trade_name": new_t, "inci_name": new_i, "price_per_kg": new_p, "quantity_kg": new_q}).execute(); st.rerun()

    # --- 3. PACKAGING LIBRARY ---
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

    # --- 4. FORMULA HUB ---
    elif menu == "Formula Hub":
        st.title("The Formula Hub")
        st.markdown("<p style='color: #64748B;'>Design, calculate, and execute batch productions.</p>", unsafe_allow_html=True)
        f_resp = supabase.table('formulas').select('*').execute()
        formulas_df = pd.DataFrame(f_resp.data) if f_resp.data else pd.DataFrame()

        if not formulas_df.empty:
            st.write("💡 *Click on any formula row below to inspect its recipe and execute a production batch.*")
            f_select = st.dataframe(formulas_df[['fr_code', 'formula_name']], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

            if f_select.selection.rows:
                f_idx = f_select.selection.rows[0]
                sel_f = formulas_df.iloc[f_idx]
                recipe_data = sel_f['recipe']
                
                st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### ⚗️ {sel_f['fr_code']} - {sel_f['formula_name']}")
                    b_size = st.number_input("Target Batch Size (grams)", min_value=1.0, value=1000.0, step=100.0)
                    st.write("---")
                    
                    calc_data = []; stock_ok = True; total_cost = 0.0
                    for ing, p in recipe_data.items():
                        req_g = (p/100) * b_size
                        m = inventory[inventory['trade_name'] == ing]
                        if not m.empty:
                            s_kg = float(m['quantity_kg'].values[0]); p_kg = float(m['price_per_kg'].values[0])
                            if s_kg < (req_g/1000): stock_ok = False
                            cost = (req_g/1000)*p_kg
                            total_cost += cost
                            calc_data.append({"Material": ing, "Formula %": f"{p}%", "Needed (g)": f"{req_g:.2f}", "Stock Status": "✅ Available" if s_kg >= (req_g/1000) else "❌ Shortage", "Est. Cost": f"${cost:.4f}", "req_kg": req_g/1000, "stock_kg": s_kg})
                        else:
                            stock_ok = False
                            calc_data.append({"Material": ing, "Formula %": f"{p}%", "Needed (g)": f"{req_g:.2f}", "Stock Status": "⚠️ Not in Vault", "Est. Cost": "$0.00", "req_kg": 0, "stock_kg": 0})
                    
                    st.dataframe(pd.DataFrame(calc_data)[['Material', 'Formula %', 'Needed (g)', 'Stock Status', 'Est. Cost']], use_container_width=True, hide_index=True)
                    
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
                    with st.expander("System Actions: Erase Formula"):
                        del_f_pass = st.text_input("Authorization Passcode", type="password", key="dfp")
                        if st.button("Permanently Delete Formula") and del_f_pass == "lab2026":
                            supabase.table('formulas').delete().eq('id', int(sel_f['id'])).execute(); st.rerun()
        else:
            st.info("No formulas architected yet.")

        st.write("---")
        
        # NEW DUAL-PANEL ARCHITECT BUILDER
        with st.expander("⚙️ Architect New Formula", expanded=True):
            c_build, c_metrics = st.columns([3, 2])
            
            with c_build:
                f_name = st.text_input("Formula Moniker", placeholder="e.g., Actiflam Hair Growth Oil")
                if "builder" not in st.session_state: st.session_state.builder = pd.DataFrame([{"Ingredient": None, "%": 0.0}])
                ing_options = inventory['trade_name'].tolist() if not inventory.empty else ["No materials registered"]
                edit_df = st.data_editor(st.session_state.builder, num_rows="dynamic", use_container_width=True, column_config={"Ingredient": st.column_config.SelectboxColumn("Ingredient", options=ing_options)})
                
            with c_metrics:
                st.write("<div style='margin-top: 2.2rem;'></div>", unsafe_allow_html=True)
                st.markdown("<p style='color: #64748B; font-weight: 600; font-size: 0.85rem; text-transform: uppercase;'>Live Cost Analysis (1 Kg Batch)</p>", unsafe_allow_html=True)
                
                total_cost_kg = 0.0
                live_data = []
                for _, row in edit_df.iterrows():
                    ing = row['Ingredient']
                    perc = row['%']
                    if ing and pd.notna(ing) and ing in inventory['trade_name'].values:
                        price = float(inventory[inventory['trade_name'] == ing]['price_per_kg'].values[0])
                        cost_contrib = (perc / 100.0) * price
                        total_cost_kg += cost_contrib
                        live_data.append({"Material": ing, "RM Base Price": f"${price:,.2f}/Kg", "Cost Contrib.": f"${cost_contrib:,.2f}"})
                
                if live_data:
                    st.dataframe(pd.DataFrame(live_data), use_container_width=True, hide_index=True)
                else:
                    st.info("Select ingredients to see live costs.")
                
                st.metric("Total Formula Cost / Kg", f"${total_cost_kg:,.2f}")
                
                total_perc = edit_df["%"].sum()
                if total_perc == 100.0:
                    st.success("✅ Formula is balanced (100%)")
                    if st.button("Commit Formula", type="primary", use_container_width=True) and f_name:
                        fr_c = f"FR{len(formulas_df)+1:05d}"
                        supabase.table("formulas").insert({"fr_code": fr_c, "formula_name": f_name, "recipe": dict(zip(edit_df["Ingredient"], edit_df["%"]))}).execute()
                        st.session_state.builder = pd.DataFrame([{"Ingredient": None, "%": 0.0}]) # Reset the builder after saving
                        st.rerun()
                else:
                    st.warning(f"⚠️ Total: {total_perc}% (Must equal 100%)")

    # --- 5. PRODUCTION LOGS ---
    elif menu == "Production Logs":
        st.title("Production Logs")
        st.markdown("<p style='color: #64748B;'>GMP-compliant traceability records.</p>", unsafe_allow_html=True)
        logs = supabase.table('production_records').select("*").order("created_at", desc=True).execute()
        if logs.data:
            df = pd.DataFrame(logs.data); df['Date'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            with st.container(border=True):
                st.dataframe(df[['Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g', 'total_cost']], use_container_width=True, hide_index=True)
        else: st.info("No records found in the vault.")
