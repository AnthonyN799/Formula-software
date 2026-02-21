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

    # --- 1. RAW MATERIAL LIBRARY (WITH INFO & DELETE WINDOW) ---
    if menu == "Raw Material Library":
        st.header("Raw Material Library")
        inv_resp = supabase.table('inventory').select("*").execute()
        inventory = pd.DataFrame(inv_resp.data).sort_values('rm_code') if inv_resp.data else pd.DataFrame()
        
        if not inventory.empty:
            # 1. High-Level Summary
            total_value = (inventory['price_per_kg'] * inventory['quantity_kg']).sum()
            st.metric("Total Raw Materials Inventory Value", f"${total_value:,.2f}")
            
            # 2. Main View Table (Clean)
            display_inv = inventory.copy()
            display_inv['Cost/g ($)'] = (display_inv['price_per_kg'] / 1000).map('${:,.4f}'.format)
            st.dataframe(
                display_inv[['rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/g ($)', 'quantity_kg']], 
                use_container_width=True, hide_index=True
            )
            
            st.divider()
            
            # 3. Info & Action Window (The "Pop-up" Style Card)
            st.subheader("🔍 Material Details & Actions")
            selected_name = st.selectbox("Select a material to inspect or remove", ["--- Select ---"] + inventory['trade_name'].tolist())
            
            if selected_name != "--- Select ---":
                mat = inventory[inventory['trade_name'] == selected_name].iloc[0]
                
                with st.container(border=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Code:** {mat['rm_code']}")
                        st.write(f"**INCI:** {mat['inci_name']}")
                        st.write(f"**Function:** {mat['function']}")
                    with c2:
                        st.write(f"**Price/Kg:** ${mat['price_per_kg']:.2f}")
                        st.write(f"**Stock:** {mat['quantity_kg']} Kg")
                        st.write(f"**Total Value:** ${(mat['price_per_kg'] * mat['quantity_kg']):.2f}")
                    
                    st.divider()
                    
                    # Delete Section inside the Info Window
                    with st.expander("🗑️ Delete this Material"):
                        st.warning(f"Are you sure you want to permanently delete {selected_name}?")
                        del_pass = st.text_input("Enter 'lab2026' to confirm deletion", type="password")
                        if st.button(f"Confirm Permanent Deletion of {mat['rm_code']}", type="primary"):
                            if del_pass == "lab2026":
                                supabase.table('inventory').delete().eq('id', mat['id']).execute()
                                st.success("Material removed from vault.")
                                st.rerun()
                            else:
                                st.error("Incorrect passcode.")

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

    # --- 2. PACKAGING LIBRARY (REMAINS CLEAN) ---
    elif menu == "Packaging Library":
        st.header("📦 Packaging Material Library")
        pk_resp = supabase.table('packaging').select("*").execute()
        packaging = pd.DataFrame(pk_resp.data).sort_values('pm_code') if pk_resp.data else pd.DataFrame()
        
        if not packaging.empty:
            st.dataframe(packaging[['pm_code', 'material_name', 'supplier', 'cost_per_unit', 'remaining_quantity']], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("🔍 Packaging Details & Actions")
            sel_p = st.selectbox("Inspect Packaging", ["--- Select ---"] + packaging['material_name'].tolist())
            if sel_p != "--- Select ---":
                p_mat = packaging[packaging['material_name'] == sel_p].iloc[0]
                with st.container(border=True):
                    st.write(f"**Code:** {p_mat['pm_code']} | **Supplier:** {p_mat['supplier']}")
                    if st.button("Delete Packaging Item", type="primary"):
                        # Logic for simple delete can go here
                        pass

    # --- 3. FORMULA HUB ---
    elif menu == "Formula Hub":
        st.header("🧪 The Formula Hub")
        # (Your existing high-quality formula logic remains here)
        # ... [Formula hub logic] ...

    # --- 4. PRODUCTION LOGS ---
    elif menu == "Production Logs":
        st.header("📋 Production Records")
        logs = supabase.table('production_records').select("*").order("created_at", desc=True).execute()
        if logs.data:
            df = pd.DataFrame(logs.data)
            df['Date'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(df[['Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g', 'total_cost']], use_container_width=True, hide_index=True)
