import streamlit as st
import pandas as pd
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
    menu = st.sidebar.radio("Navigation", ["Raw Material Library", "Formula Hub"])

    # Fetch LIVE data
    response = supabase.table('inventory').select("*").execute()
    inventory = pd.DataFrame(response.data) if response.data else pd.DataFrame()
    ingredient_list = inventory['trade_name'].tolist() if not inventory.empty else []

    # --- PAGE 1: RAW MATERIAL LIBRARY (No changes needed here) ---
    if menu == "Raw Material Library":
        st.header("Raw Material Library")
        st.dataframe(inventory[['rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'quantity_kg', 'function']], use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("➕ Add New Raw Material")
        # ... (Keeping your existing form logic) ...
        with st.form("add_material_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_trade = st.text_input("Trade Name")
                new_inci = st.text_input("INCI Name")
                new_func = st.text_input("Function")
                tds_file = st.file_uploader("Upload TDS (PDF)", type=["pdf"])
            with col2:
                new_price = st.number_input("Price/Kg ($)", min_value=0.0, format="%.2f")
                new_qty = st.number_input("Starting Quantity (Kg)", min_value=0.0, format="%.3f")
                new_use = st.text_input("Recommended Use")
                msds_file = st.file_uploader("Upload MSDS (PDF)", type=["pdf"])
            submitted = st.form_submit_button("Save to Database")
            if submitted and new_trade != "":
                next_id = 1 if inventory.empty else int(inventory['id'].max()) + 1
                new_rm_code = f"RM{next_id:05d}"
                new_data = {"rm_code": new_rm_code, "trade_name": new_trade, "inci_name": new_inci, "price_per_kg": new_price, "quantity_kg": new_qty, "function": new_func, "recommended_use": new_use}
                supabase.table('inventory').insert(new_data).execute()
                st.success(f"{new_rm_code} saved!")
                st.rerun()

    # --- PAGE 2: FORMULA HUB (The Big Upgrade) ---
    elif menu == "Formula Hub":
        st.header("🧪 The Formula Hub")
        formulas_response = supabase.table('formulas').select('*').execute()
        formulas_df = pd.DataFrame(formulas_response.data) if formulas_response.data else pd.DataFrame()

        # ... (Keeping your Formula Creation logic) ...
        st.subheader("Create New Formula")
        formula_name = st.text_input("Formula Name")
        if "formula_builder" not in st.session_state:
            st.session_state.formula_builder = pd.DataFrame([{"Ingredient": None, "Percentage (%)": 0.0}])
        edited_df = st.data_editor(st.session_state.formula_builder, num_rows="dynamic", use_container_width=True, column_config={"Ingredient": st.column_config.SelectboxColumn("Select Ingredient", options=ingredient_list, required=True), "Percentage (%)": st.column_config.NumberColumn("Percentage (%)", min_value=0.0, max_value=100.0, step=0.1, required=True)})
        if st.button("Save Formula"):
            if formula_name and edited_df["Percentage (%)"].sum() == 100.0:
                next_fr_id = 1 if formulas_df.empty else int(formulas_df['id'].max()) + 1
                new_fr_code = f"FR{next_fr_id:05d}"
                recipe_dict = dict(zip(edited_df["Ingredient"], edited_df["Percentage (%)"]))
                supabase.table("formulas").insert({"fr_code": new_fr_code, "formula_name": formula_name, "recipe": recipe_dict}).execute()
                st.success("Formula saved!")
                st.rerun()
        st.divider()

        # --- BATCH PRODUCTION SECTION ---
        st.subheader("⚗️ Production Management")
        if not formulas_df.empty:
            display_formulas = [f"[{row['fr_code']}] {row['formula_name']}" for _, row in formulas_df.iterrows()]
            selected_display_formula = st.selectbox("Select Formula to Produce", display_formulas)
            selected_formula_name = selected_display_formula.split("] ")[1]
            batch_size_g = st.number_input("Target Batch Size (grams)", min_value=1, value=1000)
            
            selected_recipe = formulas_df[formulas_df['formula_name'] == selected_formula_name].iloc[0]['recipe']
            
            # --- STOCK CHECKING LOGIC ---
            stock_ok = True
            check_results = []
            
            for ingredient, percentage in selected_recipe.items():
                needed_kg = (percentage / 100 * batch_size_g) / 1000
                current_stock_kg = float(inventory[inventory['trade_name'] == ingredient]['quantity_kg'].values[0])
                
                status = "✅ Sufficient" if current_stock_kg >= needed_kg else "❌ Shortage"
                if current_stock_kg < needed_kg: stock_ok = False
                
                check_results.append({
                    "Ingredient": ingredient,
                    "Required (Kg)": f"{needed_kg:.4f}",
                    "In Stock (Kg)": f"{current_stock_kg:.4f}",
                    "Status": status
                })

            # --- THE ACTION BUTTONS ---
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("🔍 Check Stock Status", use_container_width=True):
                    st.table(pd.DataFrame(check_results))
                    if stock_ok:
                        st.success("Inventory levels are sufficient for this batch.")
                    else:
                        st.error("Insufficient stock to produce this batch size.")

            with col_b:
                if st.button("🚀 Produce & Deduct", use_container_width=True, type="primary"):
                    if not stock_ok:
                        st.error("Deduction blocked: Insufficient stock. Run 'Check Stock' for details.")
                    else:
                        # Perform the actual deductions
                        for row in check_results:
                            ing = row["Ingredient"]
                            needed = float(row["Required (Kg)"])
                            new_stock = float(inventory[inventory['trade_name'] == ing]['quantity_kg'].values[0]) - needed
                            supabase.table('inventory').update({'quantity_kg': new_stock}).eq('trade_name', ing).execute()
                        
                        st.balloons()
                        st.success(f"Produced {batch_size_g}g of {selected_formula_name}!")
                        st.rerun()
