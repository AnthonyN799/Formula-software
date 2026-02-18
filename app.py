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

# --- Security ---
def check_password():
    st.title("Therapeutic Oils - Lab Portal")
    password = st.text_input("Enter Team Password", type="password")
    if password == "lab2026": 
        return True
    elif password != "":
        st.error("Incorrect password.")
    return False

# --- Main App ---
if check_password():
    menu = st.sidebar.radio("Navigation", ["Raw Material Library", "Formula Hub", "Production Logs"])

    # 1. Fetch LIVE inventory data
    inv_resp = supabase.table('inventory').select("*").execute()
    if inv_resp.data:
        inventory = pd.DataFrame(inv_resp.data).sort_values('rm_code')
        ingredient_list = inventory['trade_name'].tolist()
    else:
        inventory = pd.DataFrame(columns=['id', 'rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'quantity_kg', 'function', 'recommended_use', 'tds_url', 'msds_url'])
        ingredient_list = []

    # --- PAGE 1: RAW MATERIAL LIBRARY ---
    if menu == "Raw Material Library":
        st.header("Raw Material Library")
        display_inv = inventory.copy()
        display_inv['Cost/gram ($)'] = (display_inv['price_per_kg'] / 1000).map('${:,.4f}'.format)
        
        st.dataframe(
            display_inv[['rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/gram ($)', 'quantity_kg', 'function']], 
            use_container_width=True, hide_index=True
        )
        
        st.divider()
        st.subheader("📁 Document Vault")
        if not inventory.empty:
            display_names = [f"[{row['rm_code']}] {row['trade_name']}" for _, row in inventory.iterrows()]
            selected_display = st.selectbox("Select Material", display_names)
            selected_trade_name = selected_display.split("] ")[1]
            material_info = inventory[inventory['trade_name'] == selected_trade_name].iloc[0]
            c1, c2 = st.columns(2)
            with c1:
                if pd.notna(material_info.get('tds_url')) and material_info['tds_url'] != "":
                    st.link_button(f"📄 Download TDS", material_info['tds_url'], use_container_width=True)
            with c2:
                if pd.notna(material_info.get('msds_url')) and material_info['msds_url'] != "":
                    st.link_button(f"⚠️ Download MSDS", material_info['msds_url'], use_container_width=True)
        
        st.divider()
        st.subheader("➕ Add New Raw Material")
        with st.form("add_material_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_trade = st.text_input("Trade Name")
                new_inci = st.text_input("INCI Name")
                new_func = st.text_input("Function")
                tds_f = st.file_uploader("Upload TDS", type=["pdf"])
            with col2:
                new_price = st.number_input("Price/Kg ($)", min_value=0.0)
                new_qty = st.number_input("Starting Qty (Kg)", min_value=0.0)
                new_use = st.text_input("Recommended Use")
                msds_f = st.file_uploader("Upload MSDS", type=["pdf"])
            
            if st.form_submit_button("Save to Database") and new_trade != "":
                next_id = 1 if inventory.empty else int(inventory['id'].max()) + 1
                rm_code = f"RM{next_id:05d}"
                t_url, m_url = "", ""
                if tds_f:
                    supabase.storage.from_("documents").upload(f"{rm_code}_TDS.pdf", tds_f.getvalue())
                    t_url = supabase.storage.from_("documents").get_public_url(f"{rm_code}_TDS.pdf")
                if msds_f:
                    supabase.storage.from_("documents").upload(f"{rm_code}_MSDS.pdf", msds_f.getvalue())
                    m_url = supabase.storage.from_("documents").get_public_url(f"{rm_code}_MSDS.pdf")
                supabase.table('inventory').insert({"rm_code": rm_code, "trade_name": new_trade, "inci_name": new_inci, "price_per_kg": new_price, "quantity_kg": new_qty, "function": new_func, "recommended_use": new_use, "tds_url": t_url, "msds_url": m_url}).execute()
                st.success(f"{rm_code} added!")
                st.rerun()

    # --- PAGE 2: FORMULA HUB ---
    elif menu == "Formula Hub":
        st.header("🧪 The Formula Hub")
        f_resp = supabase.table('formulas').select('*').execute()
        formulas_df = pd.DataFrame(f_resp.data) if f_resp.data else pd.DataFrame()

        with st.expander("Build New Formula"):
            f_name = st.text_input("New Formula Name")
            if "builder" not in st.session_state: st.session_state.builder = pd.DataFrame([{"Ingredient": None, "%": 0.0}])
            edit_df = st.data_editor(st.session_state.builder, num_rows="dynamic", use_container_width=True)
            if st.button("Save Formula") and f_name and edit_df["%"].sum() == 100.0:
                next_fr_id = 1 if formulas_df.empty else int(formulas_df['id'].max()) + 1
                fr_code = f"FR{next_fr_id:05d}"
                supabase.table("formulas").insert({"fr_code": fr_code, "formula_name": f_name, "recipe": dict(zip(edit_df["Ingredient"], edit_df["%"]))}).execute()
                st.success("Formula saved!")
                st.rerun()

        st.divider()

        if not formulas_df.empty:
            st.subheader("⚗️ Batch Production")
            f_list = [f"[{r['fr_code']}] {r['formula_name']}" for _, r in formulas_df.iterrows()]
            sel_f = st.selectbox("Select Formula", f_list)
            b_size = st.number_input("Batch Size (g)", min_value=1, value=1000)
            
            name_only = sel_f.split("] ")[1]
            code_only = sel_f.split("]")[0].replace("[", "")
            recipe = formulas_df[formulas_df['formula_name'] == name_only].iloc[0]['recipe']
            
            calc_data = []
            stock_ok = True
            for ing, p in recipe.items():
                req_g = (p/100) * b_size
                m = inventory[inventory['trade_name'] == ing]
                s_kg = float(m['quantity_kg'].values[0])
                p_kg = float(m['price_per_kg'].values[0])
                
                has_enough = s_kg >= (req_g/1000)
                if not has_enough: stock_ok = False
                
                calc_data.append({
                    "RM": m['rm_code'].values[0],
                    "Ingredient": ing,
                    "Needed (g)": f"{req_g:.2f}g",
                    "Stock (Kg)": f"{s_kg:.4f}Kg",
                    "Status": "✅" if has_enough else "❌ Shortage",
                    "Cost": (req_g/1000)*p_kg,
                    "raw_req_kg": req_g/1000,
                    "raw_stock_kg": s_kg
                })
            
            # --- THE TABLE WITH STATUS RESTORED ---
            display_table = pd.DataFrame(calc_data)
            st.table(display_table[['RM', 'Ingredient', 'Needed (g)', 'Stock (Kg)', 'Status']])
            
            t_cost = sum([d['Cost'] for d in calc_data])
            st.info(f"**Total Batch Cost: ${t_cost:.2f}**")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 Check Stock", use_container_width=True):
                    if stock_ok: st.success("Stock is sufficient!")
                    else: st.error("Shortage detected!")
            with col2:
                if st.button("🚀 Produce Batch", type="primary", use_container_width=True):
                    if stock_ok:
                        log_resp = supabase.table('production_records').select("id").order("id", desc=True).limit(1).execute()
                        n_id = 1 if not log_resp.data else log_resp.data[0]['id'] + 1
                        b_no = f"B-{n_id:05d}"; l_no = f"LOT-{datetime.now().strftime('%Y%m%d')}-{n_id:02d}"
                        for d in calc_data:
                            supabase.table('inventory').update({'quantity_kg': d['raw_stock_kg'] - d['raw_req_kg']}).eq('trade_name', d['Ingredient']).execute()
                        supabase.table('production_records').insert({"fr_code": code_only, "formula_name": name_only, "batch_number": b_no, "lot_number": l_no, "batch_size_g": b_size, "total_cost": t_cost}).execute()
                        st.balloons(); st.success(f"Produced! Batch: {b_no} | Lot: {l_no}"); st.rerun()
                    else: st.error("Cannot produce: Fix stock shortages.")

    # --- PAGE 3: PRODUCTION LOGS ---
    elif menu == "Production Logs":
        st.header("📋 Production Records")
        logs = supabase.table('production_records').select("*").order("created_at", desc=True).execute()
        if logs.data:
            df = pd.DataFrame(logs.data)
            df['Date'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(df[['Date', 'batch_number', 'lot_number', 'fr_code', 'formula_name', 'batch_size_g', 'total_cost']], use_container_width=True, hide_index=True)
        else: st.info("No records yet.")
