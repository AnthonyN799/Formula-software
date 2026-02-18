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
        
        # Clean Professional View
        display_inv = inventory.copy()
        display_inv['Cost/g ($)'] = (display_inv['price_per_kg'] / 1000).map('${:,.4f}'.format)
        
        st.dataframe(
            display_inv[['rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/g ($)', 'quantity_kg']], 
            use_container_width=True, 
            hide_index=True
        )

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
                supabase.table('inventory').insert({
                    "rm_code": rm_code, "trade_name": new_t, "inci_name": new_i, 
                    "price_per_kg": new_p, "quantity_kg": new_q
                }).execute()
                st.rerun()

    # --- PAGE 2: FORMULA HUB ---
    elif menu == "Formula Hub":
        st.header("🧪 The Formula Hub")
        f_resp = supabase.table('formulas').select('*').execute()
        formulas_df = pd.DataFrame(f_resp.data) if f_resp.data else pd.DataFrame()

        # 1. New Formula Builder
        with st.expander("Build New Formula"):
            f_name = st.text_input("Formula Name")
            if "builder" not in st.session_state: 
                st.session_state.builder = pd.DataFrame([{"Ingredient": None, "%": 0.0}])
            edit_df = st.data_editor(st.session_state.builder, num_rows="dynamic", use_container_width=True)
            if st.button("Save Formula") and f_name and edit_df["%"].sum() == 100.0:
                fr_c = f"FR{len(formulas_df)+1:05d}"
                supabase.table("formulas").insert({
                    "fr_code": fr_c, "formula_name": f_name, 
                    "recipe": dict(zip(edit_df["Ingredient"], edit_df["%"]))
                }).execute()
                st.rerun()

        st.divider()

        # 2. Production Logic
        if not formulas_df.empty:
            st.subheader("⚗️ Batch Production")
            f_list = [f"[{r['fr_code']}] {r['formula_name']}" for _, r in formulas_df.iterrows()]
            sel_f = st.selectbox("Select Formula to Produce", f_list)
            b_size = st.number_input("Batch Size (g)", min_value=1, value=1000)
            
            name_only = sel_f.split("] ")[1]
            code_only = sel_f.split("]")[0].replace("[", "")
            recipe = formulas_df[formulas_df['formula_name'] == name_only].iloc[0]['recipe']
            
            calc_data = []; stock_ok = True
            for ing, p in recipe.items():
                req_g = (p/100) * b_size
                m = inventory[inventory['trade_name'] == ing]
                s_kg = float(m['quantity_kg'].values[0])
                p_kg = float(m['price_per_kg'].values[0])
                if s_kg < (req_g/1000): stock_ok = False
                calc_data.append({
                    "RM": m['rm_code'].values[0], "Ingredient": ing, 
                    "Needed": f"{req_g:.2f}g", "Stock": f"{s_kg:.4f}Kg", 
                    "Status": "✅" if s_kg >= (req_g/1000) else "❌", 
                    "cost": (req_g/1000)*p_kg, "req_kg": req_g/1000, "stock_kg": s_kg
                })
            
            st.table(pd.DataFrame(calc_data)[['RM', 'Ingredient', 'Needed', 'Stock', 'Status']])
            st.info(f"**Total Batch Cost: ${sum([d['cost'] for d in calc_data]):.2f}**")

            if st.button("🚀 Produce Batch", type="primary", use_container_width=True):
                if stock_ok:
                    l_r = supabase.table('production_records').select("id").order("id", desc=True).limit(1).execute()
                    n_id = 1 if not l_r.data else l_r.data[0]['id'] + 1
                    b_no = f"B-{n_id:05d}"; l_no = f"LOT-{datetime.now().strftime('%Y%m%d')}-{n_id:02d}"
                    for d in calc_data: 
                        supabase.table('inventory').update({'quantity_kg': d['stock_kg'] - d['req_kg']}).eq('trade_name', d['Ingredient']).execute()
                    supabase.table('production_records').insert({
                        "fr_code": code_only, "formula_name": name_only, "batch_number": b_no, 
                        "lot_number": l_no, "batch_size_g": b_size, "total_cost": sum([d['cost'] for d in calc_data])
                    }).execute()
                    st.balloons(); st.rerun()

    # --- PAGE 3: PRODUCTION LOGS ---
    elif menu == "Production Logs":
        st.header("📋 Production Records")
        logs = supabase.table('production_records').select("*").order("created_at", desc=True).execute()
        if logs.data:
            df = pd.DataFrame(logs.data)
            df['Date'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(df[['Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g', 'total_cost']], use_container_width=True, hide_index=True)
        else:
            st.info("No production history found.")
