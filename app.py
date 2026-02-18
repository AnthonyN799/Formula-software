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
    inventory = pd.DataFrame(inv_resp.data).sort_values('rm_code') if inv_resp.data else pd.DataFrame()
    ingredient_list = inventory['trade_name'].tolist() if not inventory.empty else []

    # --- PAGE 1: RAW MATERIAL LIBRARY ---
    if menu == "Raw Material Library":
        st.header("Raw Material Library")
        
        # Simple, Clean View
        display_inv = inventory.copy()
        display_inv['Cost/g ($)'] = (display_inv['price_per_kg'] / 1000).map('${:,.4f}'.format)
        st.dataframe(display_inv[['rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/g ($)', 'quantity_kg']], use_container_width=True, hide_index=True)
        
        # Hidden Management
        with st.expander("🛠️ Manage Inventory (Edit/Delete)"):
            st.warning("Deletions are permanent.")
            manage_inv = inventory.copy()
            manage_inv['❌'] = False
            edited_inv = st.data_editor(manage_inv[['❌', 'rm_code', 'trade_name']], use_container_width=True, hide_index=True)
            
            pass_inv = st.text_input("Manager Passcode", type="password", key="p_inv")
            if st.button("Confirm Changes", type="primary"):
                if pass_inv == "lab2026":
                    to_del = edited_inv[edited_inv['❌'] == True]['trade_name'].tolist()
                    for item in to_del:
                        supabase.table('inventory').delete().eq('trade_name', item).execute()
                    st.rerun()
        
        st.divider()
        st.subheader("➕ Add New Raw Material")
        with st.form("add_material_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                new_trade = st.text_input("Trade Name")
                new_inci = st.text_input("INCI Name")
                tds_f = st.file_uploader("TDS PDF", type=["pdf"])
            with c2:
                new_price = st.number_input("Price/Kg ($)", min_value=0.0)
                new_qty = st.number_input("Initial Qty (Kg)", min_value=0.0)
                msds_f = st.file_uploader("MSDS PDF", type=["pdf"])
            if st.form_submit_button("Save Material") and new_trade != "":
                next_id = 1 if inventory.empty else int(inventory['id'].max()) + 1
                rm_code = f"RM{next_id:05d}"
                # ... (File Upload Logic) ...
                supabase.table('inventory').insert({"rm_code": rm_code, "trade_name": new_trade, "inci_name": new_inci, "price_per_kg": new_price, "quantity_kg": new_qty}).execute()
                st.rerun()

    # --- PAGE 2: FORMULA HUB ---
    elif menu == "Formula Hub":
        st.header("🧪 The Formula Hub")
        f_resp = supabase.table('formulas').select('*').execute()
        formulas_df = pd.DataFrame(f_resp.data) if f_resp.data else pd.DataFrame()

        # 1. Formula Display & Management
        if not formulas_df.empty:
            f_list = [f"[{r['fr_code']}] {r['formula_name']}" for _, r in formulas_df.iterrows()]
            sel_f = st.selectbox("Select Formula to Produce", f_list)
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
                calc_data.append({"RM": m['rm_code'].values[0], "Ingredient": ing, "Needed": f"{req_g:.2f}g", "Stock": f"{s_kg:.4f}Kg", "Status": "✅" if has_enough else "❌", "cost": (req_g/1000)*p_kg, "req_kg": req_g/1000, "stock_kg": s_kg})
            
            st.table(pd.DataFrame(calc_data)[['RM', 'Ingredient', 'Needed', 'Stock', 'Status']])
            st.info(f"**Total Batch Cost: ${sum([d['cost'] for d in calc_data]):.2f}**")
            
            if st.button("🚀 Produce Batch", type="primary", use_container_width=True):
                if stock_ok:
                    log_r = supabase.table('production_records').select("id").order("id", desc=True).limit(1).execute()
                    n_id = 1 if not log_r.data else log_r.data[0]['id'] + 1
                    b_no = f"B-{n_id:05d}"; l_no = f"LOT-{datetime.now().strftime('%Y%m%d')}-{n_id:02d}"
                    for d in calc_data: supabase.table('inventory').update({'quantity_kg': d['stock_kg'] - d['req_kg']}).eq('trade_name', d['Ingredient']).execute()
                    supabase.table('production_records').insert({"fr_code": code_only, "formula_name": name_only, "batch_number": b_no, "lot_number": l_no, "batch_size_g": b_size, "total_cost": sum([d['cost'] for d in calc_data])}).execute()
                    st.balloons(); st.rerun()

        st.divider()
        with st.expander("📝 Manage Formulas (Create/Delete)"):
            c1, c2 = st.columns(2)
            with c1:
                st.write("**New Formula**")
                f_name = st.text_input("Name")
                if "builder" not in st.session_state: st.session_state.builder = pd.DataFrame([{"Ingredient": None, "%": 0.0}])
                edit_df = st.data_editor(st.session_state.builder, num_rows="dynamic")
                if st.button("Save New Formula") and f_name and edit_df["%"].sum() == 100.0:
                    fr_c = f"FR{len(formulas_df)+1:05d}"
                    supabase.table("formulas").insert({"fr_code": fr_c, "formula_name": f_name, "recipe": dict(zip(edit_df["Ingredient"], edit_df["%"]))}).execute()
                    st.rerun()
            with c2:
                st.write("**Delete Formula**")
                f_del_tab = formulas_df.copy()
                f_del_tab['❌'] = False
                e_f = st.data_editor(f_del_tab[['❌', 'formula_name']], hide_index=True)
                f_pass = st.text_input("Passcode", type="password", key="f_p")
                if st.button("Confirm Wipe") and f_pass == "lab2026":
                    for fc in e_f[e_f['❌'] == True]['formula_name'].tolist():
                        supabase.table('formulas').delete().eq('formula_name', fc).execute()
                    st.rerun()

    # --- PAGE 3: PRODUCTION LOGS ---
    elif menu == "Production Logs":
        st.header("📋 Production Records")
        logs = supabase.table('production_records').select("*").order("created_at", desc=True).execute()
        if logs.data:
            df = pd.DataFrame(logs.data)
            df['Date'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(df[['Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g', 'total_cost']], use_container_width=True, hide_index=True)
            
            with st.expander("🛠️ Admin: Delete Records"):
                df['❌'] = False
                e_l = st.data_editor(df[['❌', 'Date', 'lot_number']], hide_index=True)
                l_p = st.text_input("Passcode", type="password", key="l_p")
                if st.button("Wipe Selected Records") and l_p == "lab2026":
                    for ln in e_l[e_l['❌'] == True]['lot_number'].tolist():
                        supabase.table('production_records').delete().eq('lot_number', ln).execute()
                    st.rerun()
