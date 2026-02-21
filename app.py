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

    # --- 1. RAW MATERIAL LIBRARY (DIRECT SELECTION) ---
    if menu == "Raw Material Library":
        st.header("Raw Material Library")
        inv_resp = supabase.table('inventory').select("*").execute()
        inventory = pd.DataFrame(inv_resp.data).sort_values('rm_code') if inv_resp.data else pd.DataFrame()
        
        if not inventory.empty:
            # High-Level Summary
            total_value = (inventory['price_per_kg'] * inventory['quantity_kg']).sum()
            st.metric("Total Raw Materials Inventory Value", f"${total_value:,.2f}")
            
            st.write("💡 *Check the box on the left to inspect or delete a material.*")
            
            # THE INTERACTIVE TABLE
            display_inv = inventory.copy()
            display_inv['Cost/g ($)'] = (display_inv['price_per_kg'] / 1000).map('${:,.4f}'.format)
            
            # Using data_editor with a selection column
            selected_rows = st.dataframe(
                display_inv[['rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/g ($)', 'quantity_kg']],
                use_container_width=True,
                hide_index=True,
                on_select="rerun", # Forces a refresh when you click a row
                selection_mode="single_row"
            )
            
            # Capture the selected row index
            if selected_rows.selection.rows:
                idx = selected_rows.selection.rows[0]
                mat = inventory.iloc[idx]
                
                st.divider()
                st.subheader(f"🔍 Inspecting: {mat['trade_name']}")
                
                with st.container(border=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Code:** {mat['rm_code']}")
                        st.write(f"**INCI:** {mat['inci_name']}")
                        st.write(f"**Function:** {mat['function']}")
                    with c2:
                        st.write(f"**Price/Kg:** ${mat['price_per_kg']:.2f}")
                        st.write(f"**Current Stock:** {mat['quantity_kg']} Kg")
                        st.write(f"**Value on Shelf:** ${(mat['price_per_kg'] * mat['quantity_kg']):.2f}")
                    
                    st.divider()
                    
                    # Protected Deletion inside the selected view
                    with st.expander("🗑️ Delete this Material"):
                        st.warning(f"This will permanently erase {mat['trade_name']} from the vault.")
                        del_pass = st.text_input("Enter 'lab2026' to confirm deletion", type="password", key="del_mat_p")
                        if st.button(f"Permanently Delete {mat['rm_code']}", type="primary"):
                            if del_pass == "lab2026":
                                supabase.table('inventory').delete().eq('id', mat['id']).execute()
                                st.success("Record deleted.")
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

    # --- 2. PACKAGING LIBRARY (SAME SELECTION LOGIC) ---
    elif menu == "Packaging Library":
        st.header("📦 Packaging Material Library")
        pk_resp = supabase.table('packaging').select("*").execute()
        packaging = pd.DataFrame(pk_resp.data).sort_values('pm_code') if pk_resp.data else pd.DataFrame()
        
        if not packaging.empty:
            st.write("💡 *Select a row to manage packaging stock.*")
            pk_select = st.dataframe(
                packaging[['pm_code', 'material_name', 'supplier', 'cost_per_unit', 'remaining_quantity']],
                use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single_row"
            )
            
            if pk_select.selection.rows:
                p_idx = pk_select.selection.rows[0]
                p_mat = packaging.iloc[p_idx]
                with st.container(border=True):
                    st.write(f"**{p_mat['pm_code']} - {p_mat['material_name']}**")
                    with st.expander("🗑️ Delete Packaging"):
                        p_pass = st.text_input("Confirm with Passcode", type="password", key="del_pkg_p")
                        if st.button("Delete Item", type="primary"):
                            if p_pass == "lab2026":
                                supabase.table('packaging').delete().eq('id', p_mat['id']).execute()
                                st.rerun()
        
        st.divider()
        st.subheader("➕ Add New Packaging Item")
        # ... [Add Packaging Form remains the same] ...
        with st.form("add_packaging"):
            c1, c2 = st.columns(2)
            with c1:
                p_n = st.text_input("Material Name")
                p_s = st.text_input("Supplier")
            with c2:
                p_c = st.number_input("Cost per Unit ($)", min_value=0.0)
                p_q = st.number_input("Initial Qty", min_value=0.0)
            if st.form_submit_button("Save Packaging"):
                n_pm_id = 1 if packaging.empty else int(packaging['id'].max()) + 1
                pm_c = f"PM{n_pm_id:05d}"
                supabase.table('packaging').insert({"pm_code": pm_c, "material_name": p_n, "supplier": p_s, "cost_per_unit": p_c, "remaining_quantity": p_q}).execute()
                st.rerun()

    # --- 3. FORMULA HUB ---
    elif menu == "Formula Hub":
        st.header("🧪 The Formula Hub")
        # (Your Formula Builder and Batch Production logic remains fully active here)
        # ... [Formula Hub Logic] ...

    # --- 4. PRODUCTION LOGS ---
    elif menu == "Production Logs":
        st.header("📋 Production Records")
        logs = supabase.table('production_records').select("*").order("created_at", desc=True).execute()
        if logs.data:
            df = pd.DataFrame(logs.data)
            df['Date'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(df[['Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g', 'total_cost']], use_container_width=True, hide_index=True)
