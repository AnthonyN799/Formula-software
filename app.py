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

    # Added the new Financial Overview page to the navigation
    menu = st.sidebar.radio("Navigation", ["Financial Overview", "Raw Material Library", "Packaging Library", "Formula Hub", "Production Logs"])

    # Global Data Fetching for the Dashboard
    inv_resp = supabase.table('inventory').select("*").execute()
    inventory = pd.DataFrame(inv_resp.data).sort_values('rm_code') if inv_resp.data else pd.DataFrame()
    
    pk_resp = supabase.table('packaging').select("*").execute()
    packaging = pd.DataFrame(pk_resp.data).sort_values('pm_code') if pk_resp.data else pd.DataFrame()

    # --- 1. FINANCIAL OVERVIEW (NEW DASHBOARD) ---
    if menu == "Financial Overview":
        st.header("📊 Financial Overview")
        st.write("Live tracking of all Therapeutic Oils physical assets.")
        
        # Calculations
        rm_total = 0.0
        if not inventory.empty:
            rm_total = (inventory['price_per_kg'] * inventory['quantity_kg']).sum()
            
        pm_total = 0.0
        if not packaging.empty:
            pm_total = (packaging['cost_per_unit'] * packaging['remaining_quantity']).sum()
            
        grand_total = rm_total + pm_total
        
        # Display Top Metrics
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Raw Materials Value", f"${rm_total:,.2f}")
        with col2:
            st.metric("Packaging Value", f"${pm_total:,.2f}")
        with col3:
            st.metric("Total Lab Assets", f"${grand_total:,.2f}")
        st.divider()
        
        # Quick Breakdown Tables
        c_left, c_right = st.columns(2)
        with c_left:
            st.subheader("Top Raw Materials by Value")
            if not inventory.empty:
                inv_chart = inventory.copy()
                inv_chart['Total Value'] = inv_chart['price_per_kg'] * inv_chart['quantity_kg']
                inv_chart = inv_chart.sort_values(by="Total Value", ascending=False).head(5)
                inv_chart['Total Value'] = inv_chart['Total Value'].map('${:,.2f}'.format)
                st.dataframe(inv_chart[['trade_name', 'Total Value']], use_container_width=True, hide_index=True)
            else:
                st.info("No raw materials logged.")
                
        with c_right:
            st.subheader("Top Packaging by Value")
            if not packaging.empty:
                pk_chart = packaging.copy()
                pk_chart['Total Value'] = pk_chart['cost_per_unit'] * pk_chart['remaining_quantity']
                pk_chart = pk_chart.sort_values(by="Total Value", ascending=False).head(5)
                pk_chart['Total Value'] = pk_chart['Total Value'].map('${:,.2f}'.format)
                st.dataframe(pk_chart[['material_name', 'Total Value']], use_container_width=True, hide_index=True)
            else:
                st.info("No packaging logged.")

    # --- 2. RAW MATERIAL LIBRARY (EDIT + SELECT TO INSPECT) ---
    elif menu == "Raw Material Library":
        st.header("Raw Material Library")
        
        if not inventory.empty:
            st.write("💡 *Click any text/number to edit it. Check the 🔍 box to inspect or delete a material.*")
            
            display_inv = inventory.copy()
            display_inv['Cost/g ($)'] = (display_inv['price_per_kg'] / 1000).map('${:,.4f}'.format)
            display_inv.insert(0, '🔍 Select', False) 
            
            edited_inv = st.data_editor(
                display_inv[['🔍 Select', 'rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/g ($)', 'quantity_kg']],
                use_container_width=True, hide_index=True, disabled=['rm_code', 'Cost/g ($)']
            )
            
            if st.button("💾 Save Inline Edits", type="primary"):
                for index, row in edited_inv.iterrows():
                    orig = inventory.loc[index]
                    if (row['trade_name'] != orig['trade_name'] or row['inci_name'] != orig['inci_name'] or 
                        row['price_per_kg'] != orig['price_per_kg'] or row['quantity_kg'] != orig['quantity_kg']):
                        supabase.table('inventory').update({
                            "trade_name": row['trade_name'], "inci_name": row['inci_name'],
                            "price_per_kg": row['price_per_kg'], "quantity_kg": row['quantity_kg']
                        }).eq('id', int(orig['id'])).execute()
                st.success("Vault updated successfully!")
                st.rerun()

            selected_mats = edited_inv[edited_inv['🔍 Select'] == True]
            if not selected_mats.empty:
                mat_idx = selected_mats.index[0]
                mat = inventory.loc[mat_idx]
                
                st.divider()
                st.subheader(f"🔍 Inspecting: {mat['trade_name']}")
                with st.container(border=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Code:** {mat['rm_code']}")
                        st.write(f"**INCI:** {mat['inci_name']}")
                    with c2:
                        st.write(f"**Price/Kg:** ${mat['price_per_kg']:.2f}")
                        st.write(f"**Current Stock:** {mat['quantity_kg']} Kg")
                        st.write(f"**Value on Shelf:** ${(mat['price_per_kg'] * mat['quantity_kg']):.2f}")
                    
                    st.divider()
                    with st.expander("🗑️ Delete this Material"):
                        st.warning(f"This will permanently erase {mat['trade_name']}.")
                        del_pass = st.text_input("Enter passcode", type="password", key="del_mat_p")
                        if st.button(f"Permanently Delete {mat['rm_code']}"):
                            if del_pass == "lab2026":
                                supabase.table('inventory').delete().eq('id', int(mat['id'])).execute()
                                st.rerun()
                            else:
                                st.error("Incorrect passcode.")
        else:
            st.info("No materials in stock.")

        st.divider()
        st.subheader("➕ Add New Raw Material")
        with st.form("add_material", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_t = st.text_input("Trade Name")
                new_i = st.text_input("INCI Name")
            with col2:
                new_p = st.number_input("Price/Kg ($)", min_value=0.0)
                new_q = st.number_input("Initial Qty (Kg)", min_value=0.0)
            if st.form_submit_button("Save Material") and new_t != "":
                next_id = 1 if inventory.empty else int(inventory['id'].max()) + 1
                rm_code = f"RM{next_id:05d}"
                supabase.table('inventory').insert({"rm_code": rm_code, "trade_name": new_t, "inci_name": new_i, "price_per_kg": new_p, "quantity_kg": new_q}).execute()
                st.rerun()

    # --- 3. PACKAGING LIBRARY (EDIT + SELECT TO INSPECT) ---
    elif menu == "Packaging Library":
        st.header("📦 Packaging Material Library")
        
        if not packaging.empty:
            st.write("💡 *Click to edit details, or check the 🔍 box to inspect/delete.*")
            
            display_pk = packaging.copy()
            display_pk.insert(0, '🔍 Select', False)
            
            edited_pk = st.data_editor(
                display_pk[['🔍 Select', 'pm_code', 'material_name', 'supplier', 'cost_per_unit', 'remaining_quantity']],
                use_container_width=True, hide_index=True, disabled=['pm_code']
            )
            
            if st.button("💾 Save Inline Edits", type="primary"):
                for index, row in edited_pk.iterrows():
                    orig = packaging.loc[index]
                    if (row['material_name'] != orig['material_name'] or row['supplier'] != orig['supplier'] or 
                        row['cost_per_unit'] != orig['cost_per_unit'] or row['remaining_quantity'] != orig['remaining_quantity']):
                        supabase.table('packaging').update({
                            "material_name": row['material_name'], "supplier": row['supplier'],
                            "cost_per_unit": row['cost_per_unit'], "remaining_quantity": row['remaining_quantity']
                        }).eq('id', int(orig['id'])).execute()
                st.success("Packaging records synced!")
                st.rerun()

            selected_pk = edited_pk[edited_pk['🔍 Select'] == True]
            if not selected_pk.empty:
                p_idx = selected_pk.index[0]
                p_mat = packaging.loc[p_idx]
                
                st.divider()
                st.subheader(f"🔍 Inspecting: {p_mat['material_name']}")
                with st.container(border=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Code:** {p_mat['pm_code']}")
                        st.write(f"**Supplier:** {p_mat['supplier']}")
                    with c2:
                        st.write(f"**Cost per Unit:** ${p_mat['cost_per_unit']:.2f}")
                        st.write(f"**Current Stock:** {p_mat['remaining_quantity']} Units")
                        st.write(f"**Value on Shelf:** ${(p_mat['cost_per_unit'] * p_mat['remaining_quantity']):.2f}")
                    
                    st.divider()
                    with st.expander("🗑️ Delete Packaging"):
                        st.warning(f"This will permanently erase {p_mat['material_name']}.")
                        p_pass = st.text_input("Confirm with Passcode", type="password", key="del_pkg_p")
                        if st.button("Delete Item"):
                            if p_pass == "lab2026":
                                supabase.table('packaging').delete().eq('id', int(p_mat['id'])).execute()
                                st.rerun()
                            else:
                                st.error("Incorrect passcode.")
        else:
            st.info("No packaging materials logged.")
        
        st.divider()
        st.subheader("➕ Add New Packaging Item")
        with st.form("add_packaging", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                p_n = st.text_input("Material Name")
                p_s = st.text_input("Supplier")
            with c2:
                p_c = st.number_input("Cost per Unit ($)", min_value=0.0)
                p_q = st.number_input("Initial Qty", min_value=0.0)
            if st.form_submit_button("Save Packaging") and p_n != "":
                n_pm_id = 1 if packaging.empty else int(packaging['id'].max()) + 1
                pm_c = f"PM{n_pm_id:05d}"
                supabase.table('packaging').insert({"pm_code": pm_c, "material_name": p_n, "supplier": p_s, "cost_per_unit": p_c, "remaining_quantity": p_q}).execute()
                st.rerun()

    # --- 4. FORMULA HUB ---
    elif menu == "Formula Hub":
        st.header("🧪 The Formula Hub")
        f_resp = supabase.table('formulas').select('*').execute()
        formulas_df = pd.DataFrame(f_resp.data) if f_resp.data else pd.DataFrame()

        with st.expander("Build New Formula"):
            f_name = st.text_input("Formula Name")
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
            f_options = [f"[{r['fr_code']}] {r['formula_name']}" for _, r in formulas_df.iterrows()]
            sel_f = st.selectbox("Select Formula", f_options)
            b_size = st.number_input("Batch Size (g)", min_value=1, value=1000)
            
            name_only = sel_f.split("] ")[1]
            code_only = sel_f.split("]")[0].replace("[", "")
            recipe_data = formulas_df[formulas_df['formula_name'] == name_only].iloc[0]['recipe']
            
            calc_data = []; stock_ok = True
            for ing, p in recipe_data.items():
                req_g = (p/100) * b_size
                m = inventory[inventory['trade_name'] == ing]
                s_kg = float(m['quantity_kg'].values[0]); p_kg = float(m['price_per_kg'].values[0])
                if s_kg < (req_g/1000): stock_ok = False
                calc_data.append({
                    "RM": m['rm_code'].values[0], "Ingredient": ing, "Needed (g)": f"{req_g:.2f}g", 
                    "Stock (Kg)": f"{s_kg:.4f}Kg", "Status": "✅" if s_kg >= (req_g/1000) else "❌", 
                    "cost": (req_g/1000)*p_kg, "req_kg": req_g/1000, "stock_kg": s_kg
                })
            
            st.table(pd.DataFrame(calc_data)[['RM', 'Ingredient', 'Needed (g)', 'Stock (Kg)', 'Status']])
            st.info(f"**Total Batch Cost: ${sum([d['cost'] for d in calc_data]):.2f}**")

            if st.button("🚀 Produce Batch", type="primary", use_container_width=True):
                if stock_ok:
                    l_r = supabase.table('production_records').select("id").order("id", desc=True).limit(1).execute()
                    n_id = 1 if not l_r.data else l_r.data[0]['id'] + 1
                    b_no, l_no = f"B-{n_id:05d}", f"LOT-{datetime.now().strftime('%Y%m%d')}-{n_id:02d}"
                    for d in calc_data:
                        supabase.table('inventory').update({'quantity_kg': d['stock_kg'] - d['req_kg']}).eq('trade_name', d['Ingredient']).execute()
                    supabase.table('production_records').insert({
                        "fr_code": code_only, "formula_name": name_only, "batch_number": b_no, 
                        "lot_number": l_no, "batch_size_g": b_size, "total_cost": sum([d['cost'] for d in calc_data])
                    }).execute()
                    st.balloons(); st.rerun()
                else: st.error("Shortage detected.")

    # --- 5. PRODUCTION LOGS ---
    elif menu == "Production Logs":
        st.header("📋 Production Records")
        logs = supabase.table('production_records').select("*").order("created_at", desc=True).execute()
        if logs.data:
            df = pd.DataFrame(logs.data)
            df['Date'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(df[['Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g', 'total_cost']], use_container_width=True, hide_index=True)
        else:
            st.info("No records found.")
