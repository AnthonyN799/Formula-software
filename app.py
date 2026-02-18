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
        
        # Setup for Inline Deletion
        display_inv = inventory.copy()
        display_inv['Cost/gram ($)'] = (display_inv['price_per_kg'] / 1000).map('${:,.4f}'.format)
        display_inv['🗑️'] = False # This creates the interactive delete column

        st.write("To delete: Enter passcode below, check the 🗑️ box, and click 'Confirm Wipes'.")
        
        # The Interactive Table with Delete Column
        edited_inv = st.data_editor(
            display_inv[['🗑️', 'rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/gram ($)', 'quantity_kg']],
            use_container_width=True,
            hide_index=True,
            disabled=['rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/gram ($)', 'quantity_kg']
        )
        
        col_sec, col_btn = st.columns([3, 1])
        with col_sec:
            del_pass = st.text_input("Security Passcode to enable deletion", type="password", key="inv_del_p")
        with col_btn:
            st.write("##") # Alignment
            if st.button("Confirm Wipes", type="primary"):
                if del_pass == "lab2026":
                    to_delete = edited_inv[edited_inv['🗑️'] == True]['trade_name'].tolist()
                    for item in to_delete:
                        supabase.table('inventory').delete().eq('trade_name', item).execute()
                    st.success(f"Successfully removed {len(to_delete)} items.")
                    st.rerun()
                else:
                    st.error("Incorrect Passcode")

        st.divider()
        st.subheader("📁 Document Vault")
        if not inventory.empty:
            d_names = [f"[{r['rm_code']}] {r['trade_name']}" for _, r in inventory.iterrows()]
            sel_d = st.selectbox("Select Material", d_names)
            sel_t_name = sel_d.split("] ")[1]
            m_info = inventory[inventory['trade_name'] == sel_t_name].iloc[0]
            c1, c2 = st.columns(2)
            with c1:
                if pd.notna(m_info.get('tds_url')) and m_info['tds_url'] != "":
                    st.link_button("📄 TDS", m_info['tds_url'], use_container_width=True)
            with c2:
                if pd.notna(m_info.get('msds_url')) and m_info['msds_url'] != "":
                    st.link_button("⚠️ MSDS", m_info['msds_url'], use_container_width=True)

        st.divider()
        st.subheader("➕ Add New Raw Material")
        with st.form("add_material_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                new_trade = st.text_input("Trade Name")
                new_inci = st.text_input("INCI Name"); new_func = st.text_input("Function")
                tds_f = st.file_uploader("TDS PDF", type=["pdf"])
            with c2:
                new_price = st.number_input("Price/Kg ($)", min_value=0.0)
                new_qty = st.number_input("Initial Qty (Kg)", min_value=0.0)
                new_use = st.text_input("Usage %"); msds_f = st.file_uploader("MSDS PDF", type=["pdf"])
            if st.form_submit_button("Save Material") and new_trade != "":
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
                st.rerun()

    # --- PAGE 2: FORMULA HUB ---
    elif menu == "Formula Hub":
        st.header("🧪 The Formula Hub")
        f_resp = supabase.table('formulas').select('*').execute()
        formulas_df = pd.DataFrame(f_resp.data) if f_resp.data else pd.DataFrame()

        with st.expander("Build New Formula"):
            f_name = st.text_input("Formula Name")
            if "builder" not in st.session_state: st.session_state.builder = pd.DataFrame([{"Ingredient": None, "%": 0.0}])
            edit_df = st.data_editor(st.session_state.builder, num_rows="dynamic", use_container_width=True)
            if st.button("Save Formula") and f_name and edit_df["%"].sum() == 100.0:
                next_fr_id = 1 if formulas_df.empty else int(formulas_df['id'].max()) + 1
                fr_code = f"FR{next_fr_id:05d}"
                supabase.table("formulas").insert({"fr_code": fr_code, "formula_name": f_name, "recipe": dict(zip(edit_df["Ingredient"], edit_df["%"]))}).execute()
                st.rerun()
        
        st.divider()
        if not formulas_df.empty:
            st.subheader("⚗️ Batch Production")
            
            # Inline Formula Delete Setup
            f_table = formulas_df.copy()
            f_table['🗑️'] = False
            
            st.write("Check 🗑️ to remove a formula from the hub.")
            edited_f = st.data_editor(f_table[['🗑️', 'fr_code', 'formula_name']], use_container_width=True, hide_index=True, disabled=['fr_code', 'formula_name'])
            
            c_f_pass, c_f_btn = st.columns([3, 1])
            with c_f_pass:
                f_del_pass = st.text_input("Passcode to Delete Formula", type="password", key="f_del_p")
            with c_f_btn:
                st.write("##")
                if st.button("Confirm Delete Formula", type="primary"):
                    if f_del_pass == "lab2026":
                        to_del_f = edited_f[edited_f['🗑️'] == True]['fr_code'].tolist()
                        for f_code in to_del_f:
                            supabase.table('formulas').delete().eq('fr_code', f_code).execute()
                        st.rerun()

            st.divider()
            f_list = [f"[{r['fr_code']}] {r['formula_name']}" for _, r in formulas_df.iterrows()]
            sel_f = st.selectbox("Select Formula to Produce", f_list)
            b_size = st.number_input("Batch Size (g)", min_value=1, value=1000)
            name_only = sel_f.split("] ")[1]; code_only = sel_f.split("]")[0].replace("[", ""); recipe = formulas_df[formulas_df['formula_name'] == name_only].iloc[0]['recipe']
            calc_data = []; stock_ok = True
            for ing, p in recipe.items():
                req_g = (p/100) * b_size; m = inventory[inventory['trade_name'] == ing]; s_kg = float(m['quantity_kg'].values[0]); p_kg = float(m['price_per_kg'].values[0])
                has_enough = s_kg >= (req_g/1000)
                if not has_enough: stock_ok = False
                calc_data.append({"RM": m['rm_code'].values[0], "Ingredient": ing, "Needed (g)": f"{req_g:.2f}g", "Stock (Kg)": f"{s_kg:.4f}Kg", "Status": "✅" if has_enough else "❌", "Cost": (req_g/1000)*p_kg, "raw_req_kg": req_g/1000, "raw_stock_kg": s_kg})
            st.table(pd.DataFrame(calc_data)[['RM', 'Ingredient', 'Needed (g)', 'Stock (Kg)', 'Status']])
            t_cost = sum([d['Cost'] for d in calc_data])
            st.info(f"**Total Batch Cost: ${t_cost:.2f}**")
            
            if st.button("🚀 Produce Batch", type="primary", use_container_width=True):
                if stock_ok:
                    log_resp = supabase.table('production_records').select("id").order("id", desc=True).limit(1).execute()
                    n_id = 1 if not log_resp.data else log_resp.data[0]['id'] + 1
                    b_no = f"B-{n_id:05d}"; l_no = f"LOT-{datetime.now().strftime('%Y%m%d')}-{n_id:02d}"
                    for d in calc_data: supabase.table('inventory').update({'quantity_kg': d['raw_stock_kg'] - d['raw_req_kg']}).eq('trade_name', d['Ingredient']).execute()
                    supabase.table('production_records').insert({"fr_code": code_only, "formula_name": name_only, "batch_number": b_no, "lot_number": l_no, "batch_size_g": b_size, "total_cost": t_cost}).execute()
                    st.balloons(); st.rerun()

    # --- PAGE 3: PRODUCTION LOGS ---
    elif menu == "Production Logs":
        st.header("📋 Production Records")
        logs = supabase.table('production_records').select("*").order("created_at", desc=True).execute()
        if logs.data:
            df = pd.DataFrame(logs.data)
            df['Date'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            df['🗑️'] = False
            
            st.write("Check 🗑️ and enter passcode to wipe a specific record.")
            edited_log = st.data_editor(df[['🗑️', 'Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g', 'total_cost']], use_container_width=True, hide_index=True, disabled=['Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g', 'total_cost'])
            
            c_l_pass, c_l_btn = st.columns([3, 1])
            with c_l_pass:
                log_del_pass = st.text_input("Passcode to Wipe Log", type="password", key="log_del_p")
            with c_l_btn:
                st.write("##")
                if st.button("Confirm Wipe Record", type="primary"):
                    if log_del_pass == "lab2026":
                        to_wipe = edited_log[edited_log['🗑️'] == True]['lot_number'].tolist()
                        for l_no in to_wipe:
                            supabase.table('production_records').delete().eq('lot_number', l_no).execute()
                        st.rerun()
        else: st.info("No records found.")
