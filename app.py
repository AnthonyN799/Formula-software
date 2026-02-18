import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# --- Connect to the Database ---
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# --- Authentication Logic ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if st.session_state["authenticated"]:
        return True
    
    st.title("Therapeutic Oils - Lab Portal")
    password = st.text_input("Enter Team Password", type="password")
    if st.button("Login"):
        if password == "lab2026":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False

# --- Main App Execution ---
if check_password():
    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()

    menu = st.sidebar.radio("Navigation", ["Raw Material Library", "Packaging Library", "Formula Hub", "Production Logs"])

    # --- 1. RAW MATERIAL LIBRARY (WITH VAULT & AUTO-CODE) ---
    if menu == "Raw Material Library":
        st.header("Raw Material Library")
        inv_resp = supabase.table('inventory').select("*").execute()
        inventory = pd.DataFrame(inv_resp.data).sort_values('rm_code') if inv_resp.data else pd.DataFrame()
        
        if not inventory.empty:
            display_inv = inventory.copy()
            display_inv['Cost/g ($)'] = (display_inv['price_per_kg'] / 1000).map('${:,.4f}'.format)
            st.dataframe(display_inv[['rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/g ($)', 'quantity_kg']], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("📁 Document Vault")
            d_names = [f"[{r['rm_code']}] {r['trade_name']}" for _, r in inventory.iterrows()]
            sel_d = st.selectbox("Select Material to View PDFs", d_names)
            m_info = inventory[inventory['trade_name'] == sel_d.split("] ")[1]].iloc[0]
            c1, c2 = st.columns(2)
            with c1:
                if pd.notna(m_info.get('tds_url')) and m_info['tds_url'] != "":
                    st.link_button("📄 Download TDS", m_info['tds_url'], use_container_width=True)
            with c2:
                if pd.notna(m_info.get('msds_url')) and m_info['msds_url'] != "":
                    st.link_button("⚠️ Download MSDS", m_info['msds_url'], use_container_width=True)
        
        st.divider()
        st.subheader("➕ Add New Raw Material")
        with st.form("add_material", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_t = st.text_input("Trade Name")
                new_i = st.text_input("INCI Name")
                tds_f = st.file_uploader("TDS PDF", type=["pdf"])
            with col2:
                new_p = st.number_input("Price/Kg ($)", min_value=0.0)
                new_q = st.number_input("Initial Qty (Kg)", min_value=0.0)
                msds_f = st.file_uploader("MSDS PDF", type=["pdf"])
            
            if st.form_submit_button("Save Material") and new_t != "":
                next_id = 1 if inventory.empty else int(inventory['id'].max()) + 1
                rm_code = f"RM{next_id:05d}"
                t_url, m_url = "", ""
                if tds_f:
                    supabase.storage.from_("documents").upload(f"{rm_code}_TDS.pdf", tds_f.getvalue(), {"content-type": "application/pdf"})
                    t_url = supabase.storage.from_("documents").get_public_url(f"{rm_code}_TDS.pdf")
                if msds_f:
                    supabase.storage.from_("documents").upload(f"{rm_code}_MSDS.pdf", msds_f.getvalue(), {"content-type": "application/pdf"})
                    m_url = supabase.storage.from_("documents").get_public_url(f"{rm_code}_MSDS.pdf")
                supabase.table('inventory').insert({"rm_code": rm_code, "trade_name": new_t, "inci_name": new_i, "price_per_kg": new_p, "quantity_kg": new_q, "tds_url": t_url, "msds_url": m_url}).execute()
                st.rerun()

    # --- 2. PACKAGING LIBRARY (AUTO-CODE & VALUE TRACKING) ---
    elif menu == "Packaging Library":
        st.header("📦 Packaging Material Library")
        pk_resp = supabase.table('packaging').select("*").execute()
        packaging = pd.DataFrame(pk_resp.data).sort_values('pm_code') if pk_resp.data else pd.DataFrame()
        
        if not packaging.empty:
            display_pk = packaging.copy()
            display_pk['Cost/Unit'] = display_pk['cost_per_unit'].map('${:,.2f}'.format)
            display_pk['Total Value'] = display_pk['value_of_stock'].map('${:,.2f}'.format)
            st.dataframe(display_pk[['pm_code', 'material_name', 'supplier', 'Cost/Unit', 'remaining_quantity', 'Total Value']], use_container_width=True, hide_index=True)
            st.metric("Total Packaging Investment", f"${packaging['value_of_stock'].sum():.2f}")
        
        st.divider()
        st.subheader("➕ Add New Packaging Item")
        with st.form("add_packaging", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                p_name = st.text_input("Material Name")
                p_supplier = st.text_input("Supplier")
            with c2:
                p_cost = st.number_input("Cost/Unit ($)", min_value=0.0)
                p_qty = st.number_input("Initial Qty", min_value=0.0)
            
            if st.form_submit_button("Save Packaging") and p_name != "":
                next_pm_id = 1 if packaging.empty else int(packaging['id'].max()) + 1
                pm_code = f"PM{next_pm_id:05d}"
                supabase.table('packaging').insert({"pm_code": pm_code, "material_name": p_name, "supplier": p_supplier, "cost_per_unit": p_cost, "remaining_quantity": p_qty}).execute()
                st.rerun()

    # --- 3. FORMULA HUB (RECIPE BUILDER & PRODUCTION) ---
    elif menu == "Formula Hub":
        st.header("🧪 The Formula Hub")
        inv_resp = supabase.table('inventory').select("*").execute()
        inventory = pd.DataFrame(inv_resp.data) if inv_resp.data else pd.DataFrame()
        f_resp = supabase.table('formulas').select('*').execute()
        formulas_df = pd.DataFrame(f_resp.data) if f_resp.data else pd.DataFrame()

        with st.expander("Build New Formula (100% Total)"):
            f_name = st.text_input("New Formula Name")
            if "builder" not in st.session_state: st.session_state.builder = pd.DataFrame([{"Ingredient": None, "%": 0.0}])
            edit_df = st.data_editor(st.session_state.builder, num_rows="dynamic", use_container_width=True, 
                                     column_config={"Ingredient": st.column_config.SelectboxColumn("Ingredient", options=inventory['trade_name'].tolist())})
            
            if st.button("Save Formula") and f_name and edit_df["%"].sum() == 100.0:
                fr_c = f"FR{len(formulas_df)+1:05d}"
                supabase.table("formulas").insert({"fr_code": fr_c, "formula_name": f_name, "recipe": dict(zip(edit_df["Ingredient"], edit_df["%"]))}).execute()
                st.rerun()

        if not formulas_df.empty:
            st.divider()
            st.subheader("⚗️ Batch Production")
            sel_f = st.selectbox("Select Formula", [f"[{r['fr_code']}] {r['formula_name']}" for _, r in formulas_df.iterrows()])
            b_size = st.number_input("Batch Size (g)", min_value=1, value=1000)
            
            name = sel_f.split("] ")[1]
            code = sel_f.split("]")[0].replace("[", "")
            recipe = formulas_df[formulas_df['formula_name'] == name].iloc[0]['recipe']
            
            calc_data = []; stock_ok = True
            for ing, p in recipe.items():
                req_g = (p/100) * b_size
                m = inventory[inventory['trade_name'] == ing]
                s_kg = float(m['quantity_kg'].values[0]); p_kg = float(m['price_per_kg'].values[0])
                if s_kg < (req_g/1000): stock_ok = False
                calc_data.append({"RM": m['rm_code'].values[0], "Ingredient": ing, "Needed (g)": f"{req_g:.2f}g", "Stock (Kg)": f"{s_kg:.4f}Kg", "Status": "✅" if s_kg >= (req_g/1000) else "❌", "cost": (req_g/1000)*p_kg, "req_kg": req_g/1000, "stock_kg": s_kg})
            
            st.table(pd.DataFrame(calc_data)[['RM', 'Ingredient', 'Needed (g)', 'Stock (Kg)', 'Status']])
            st.info(f"**Total Batch Cost: ${sum([d['cost'] for d in calc_data]):.2f}**")

            if st.button("🚀 Produce Batch & Deduct Inventory", type="primary", use_container_width=True):
                if stock_ok:
                    l_r = supabase.table('production_records').select("id").order("id", desc=True).limit(1).execute()
                    n_id = 1 if not l_r.data else l_r.data[0]['id'] + 1
                    b_no, l_no = f"B-{n_id:05d}", f"LOT-{datetime.now().strftime('%Y%m%d')}-{n_id:02d}"
                    for d in calc_data:
                        supabase.table('inventory').update({'quantity_kg': d['stock_kg'] - d['req_kg']}).eq('trade_name', d['Ingredient']).execute()
                    supabase.table('production_records').insert({"fr_code": code, "formula_name": name, "batch_number": b_no, "lot_number": l_no, "batch_size_g": b_size, "total_cost": sum([d['cost'] for d in calc_data])}).execute()
                    st.balloons(); st.rerun()
                else: st.error("Shortage detected. Cannot produce.")

    # --- 4. PRODUCTION LOGS (GMP TRACEABILITY) ---
    elif menu == "Production Logs":
        st.header("📋 Production Records")
        logs = supabase.table('production_records').select("*").order("created_at", desc=True).execute()
        if logs.data:
            df = pd.DataFrame(logs.data)
            df['Date'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(df[['Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g', 'total_cost']], use_container_width=True, hide_index=True)
        else: st.info("No production history.")
