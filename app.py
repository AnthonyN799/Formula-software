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

    # Fetch LIVE data
    inv_resp = supabase.table('inventory').select("*").execute()
    inventory = pd.DataFrame(inv_resp.data).sort_values('rm_code') if inv_resp.data else pd.DataFrame()

    # --- PAGE 1: RAW MATERIAL LIBRARY ---
    if menu == "Raw Material Library":
        st.header("Raw Material Library")
        
        # Prepare table with the extra "X" column
        display_inv = inventory.copy()
        display_inv['Cost/g ($)'] = (display_inv['price_per_kg'] / 1000).map('${:,.4f}'.format)
        display_inv['X'] = False # This is your red X column

        # Professional Instructions
        st.write("To delete: Enter passcode at bottom, check 'X', and click 'Confirm Deletions'.")
        
        # The Main Table
        edited_inv = st.data_editor(
            display_inv[['X', 'rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/g ($)', 'quantity_kg']],
            use_container_width=True,
            hide_index=True,
            disabled=['rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/g ($)', 'quantity_kg']
        )
        
        # Deletion Security
        c_p, c_b = st.columns([3, 1])
        with c_p:
            del_pass = st.text_input("Enter Passcode to enable 'X' actions", type="password")
        with c_b:
            st.write("##")
            if st.button("Confirm Deletions", type="primary"):
                if del_pass == "lab2026":
                    to_del = edited_inv[edited_inv['X'] == True]['trade_name'].tolist()
                    for item in to_del:
                        supabase.table('inventory').delete().eq('trade_name', item).execute()
                    st.rerun()
                else:
                    st.error("Passcode Required")

        st.divider()
        st.subheader("➕ Add New Raw Material")
        with st.form("add_material_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                new_t = st.text_input("Trade Name")
                new_i = st.text_input("INCI Name")
            with c2:
                new_p = st.number_input("Price/Kg ($)", min_value=0.0)
                new_q = st.number_input("Initial Qty (Kg)", min_value=0.0)
            if st.form_submit_button("Save Material") and new_t != "":
                next_id = 1 if inventory.empty else int(inventory['id'].max()) + 1
                rm_code = f"RM{next_id:05d}"
                supabase.table('inventory').insert({"rm_code": rm_code, "trade_name": new_t, "inci_name": new_i, "price_per_kg": new_p, "quantity_kg": new_q}).execute()
                st.rerun()

    # --- PAGE 2: FORMULA HUB ---
    elif menu == "Formula Hub":
        st.header("🧪 The Formula Hub")
        f_resp = supabase.table('formulas').select('*').execute()
        formulas_df = pd.DataFrame(f_resp.data) if f_resp.data else pd.DataFrame()

        # 1. Formula List with Delete X
        if not formulas_df.empty:
            st.subheader("Saved Formulas")
            display_f = formulas_df.copy()
            display_f['X'] = False
            edited_f = st.data_editor(display_f[['X', 'fr_code', 'formula_name']], use_container_width=True, hide_index=True, disabled=['fr_code', 'formula_name'])
            
            c_fp, c_fb = st.columns([3, 1])
            with c_fp:
                f_pass = st.text_input("Passcode to delete formulas", type="password")
            with c_fb:
                st.write("##")
                if st.button("Wipe Selected Formulas", type="primary"):
                    if f_pass == "lab2026":
                        for fc in edited_f[edited_f['X'] == True]['fr_code'].tolist():
                            supabase.table('formulas').delete().eq('fr_code', fc).execute()
                        st.rerun()

            st.divider()
            # Production Logic
            f_list = [f"[{r['fr_code']}] {r['formula_name']}" for _, r in formulas_df.iterrows()]
            sel_f = st.selectbox("Select Formula to Produce", f_list)
            b_size = st.number_input("Batch Size (g)", min_value=1, value=1000)
            
            name_only = sel_f.split("] ")[1]; code_only = sel_f.split("]")[0].replace("[", "")
            recipe = formulas_df[formulas_df['formula_name'] == name_only].iloc[0]['recipe']
            
            calc_data = []; stock_ok = True
            for ing, p in recipe.items():
                req_g = (p/100) * b_size; m = inventory[inventory['trade_name'] == ing]
                s_kg = float(m['quantity_kg'].values[0]); p_kg = float(m['price_per_kg'].values[0])
                if s_kg < (req_g/1000): stock_ok = False
                calc_data.append({"RM": m['rm_code'].values[0], "Ingredient": ing, "Needed": f"{req_g:.2f}g", "Stock": f"{s_kg:.4f}Kg", "Status": "✅" if s_kg >= (req_g/1000) else "❌", "cost": (req_g/1000)*p_kg, "req_kg": req_g/1000, "stock_kg": s_kg})
            
            st.table(pd.DataFrame(calc_data)[['RM', 'Ingredient', 'Needed', 'Stock', 'Status']])
            if st.button("🚀 Produce Batch", type="primary", use_container_width=True):
                if stock_ok:
                    l_r = supabase.table('production_records').select("id").order("id", desc=True).limit(1).execute()
                    n_id = 1 if not l_r.data else l_r.data[0]['id'] + 1
                    b_no = f"B-{n_id:05d}"; l_no = f"LOT-{datetime.now().strftime('%Y%m%d')}-{n_id:02d}"
                    for d in calc_data: supabase.table('inventory').update({'quantity_kg': d['stock_kg'] - d['req_kg']}).eq('trade_name', d['Ingredient']).execute()
                    supabase.table('production_records').insert({"fr_code": code_only, "formula_name": name_only, "batch_number": b_no, "lot_number": l_no, "batch_size_g": b_size, "total_cost": sum([d['cost'] for d in calc_data])}).execute()
                    st.balloons(); st.rerun()

    # --- PAGE 3: PRODUCTION LOGS ---
    elif menu == "Production Logs":
        st.header("📋 Production Records")
        logs = supabase.table('production_records').select("*").order("created_at", desc=True).execute()
        if logs.data:
            df = pd.DataFrame(logs.data)
            df['Date'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            df['X'] = False
            
            # The Logs Table with Delete X
            edited_log = st.data_editor(df[['X', 'Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g']], use_container_width=True, hide_index=True, disabled=['Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g'])
            
            c_lp, c_lb = st.columns([3, 1])
            with c_lp:
                l_pass = st.text_input("Passcode to wipe records", type="password")
            with c_lb:
                st.write("##")
                if st.button("Confirm Wipe Records", type="primary"):
                    if l_pass == "lab2026":
                        for ln in edited_log[edited_log['X'] == True]['lot_number'].tolist():
                            supabase.table('production_records').delete().eq('lot_number', ln).execute()
                        st.rerun()
