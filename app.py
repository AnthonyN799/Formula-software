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

    # 1. Fetch LIVE data from Supabase Inventory
    response = supabase.table('inventory').select("*").execute()
    if response.data:
        inventory = pd.DataFrame(response.data)
        ingredient_list = inventory['trade_name'].tolist()
    else:
        inventory = pd.DataFrame(columns=['id', 'trade_name', 'inci_name', 'price_per_kg', 'quantity_kg', 'function', 'recommended_use', 'tds_url', 'msds_url'])
        ingredient_list = []

    # --- PAGE 1: RAW MATERIAL LIBRARY ---
    if menu == "Raw Material Library":
        st.header("Raw Material Library")
        
        st.dataframe(
            inventory[['trade_name', 'inci_name', 'price_per_kg', 'quantity_kg', 'function']], 
            use_container_width=True, 
            hide_index=True
        )
        st.divider()
        
        # Document Vault
        st.subheader("📁 Document Vault")
        if not inventory.empty:
            selected_material = st.selectbox("Select Material", inventory['trade_name'].tolist())
            material_info = inventory[inventory['trade_name'] == selected_material].iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                if pd.notna(material_info.get('tds_url')) and material_info['tds_url'] != "":
                    st.link_button(f"📄 Download TDS", material_info['tds_url'])
                else:
                    st.warning("No TDS on file.")
            with col2:
                if pd.notna(material_info.get('msds_url')) and material_info['msds_url'] != "":
                    st.link_button(f"⚠️ Download MSDS", material_info['msds_url'])
                else:
                    st.warning("No MSDS on file.")
        st.divider()
        
        # Add New Material
        st.subheader("➕ Add New Raw Material")
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
                tds_url = ""
                msds_url = ""
                if tds_file is not None:
                    file_name = f"{new_trade.replace(' ', '_')}_TDS.pdf"
                    supabase.storage.from_("documents").upload(file_name, tds_file.getvalue(), {"content-type": "application/pdf"})
                    tds_url = supabase.storage.from_("documents").get_public_url(file_name)
                if msds_file is not None:
                    file_name = f"{new_trade.replace(' ', '_')}_MSDS.pdf"
                    supabase.storage.from_("documents").upload(file_name, msds_file.getvalue(), {"content-type": "application/pdf"})
                    msds_url = supabase.storage.from_("documents").get_public_url(file_name)

                new_data = {
                    "trade_name": new_trade, "inci_name": new_inci, "price_per_kg": new_price,
                    "quantity_kg": new_qty, "function": new_func, "recommended_use": new_use,
                    "tds_url": tds_url, "msds_url": msds_url
                }
                supabase.table('inventory').insert(new_data).execute()
                st.success(f"{new_trade} saved!")
                st.rerun() 

    # --- PAGE 2: FORMULA HUB ---
    elif menu == "Formula Hub":
        st.header("🧪 The Formula Hub")
        
        # 1. BUILD A NEW FORMULA
        st.subheader("Create New Formula")
        formula_name = st.text_input("Formula Name (e.g., Revitalizing Hair Oil)")
        
        st.write("**Build your formula (Must equal 100%)**")
        
        # Create a blank slate for the interactive table
        if "formula_builder" not in st.session_state:
            st.session_state.formula_builder = pd.DataFrame([{"Ingredient": None, "Percentage (%)": 0.0}])
            
        # The interactive data editor
        edited_df = st.data_editor(
            st.session_state.formula_builder,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Ingredient": st.column_config.SelectboxColumn(
                    "Select Ingredient",
                    options=ingredient_list, # Pulls directly from live database
                    required=True
                ),
                "Percentage (%)": st.column_config.NumberColumn(
                    "Percentage (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.1,
                    required=True
                )
            }
        )
        
        # Live Math Validation
        total_percent = edited_df["Percentage (%)"].sum()
        
        if total_percent == 100.0:
            st.success(f"**Total: {total_percent}% ✅**")
        else:
            st.warning(f"**Total: {total_percent}%** (Must equal exactly 100%)")
            
        if st.button("Save Formula"):
            if formula_name == "":
                st.error("Please enter a formula name.")
            elif total_percent != 100.0:
                st.error("Formula must equal exactly 100% before saving.")
            elif edited_df["Ingredient"].isnull().any():
                st.error("Please select an ingredient for every row.")
            else:
                # Convert the table into a dictionary and save to the vault
                recipe_dict = dict(zip(edited_df["Ingredient"], edited_df["Percentage (%)"]))
                supabase.table("formulas").insert({
                    "formula_name": formula_name,
                    "recipe": recipe_dict
                }).execute()
                
                st.success(f"'{formula_name}' permanently saved to the Hub!")
                st.session_state.formula_builder = pd.DataFrame([{"Ingredient": None, "Percentage (%)": 0.0}])
                st.rerun()

        st.divider()

        # 2. CALCULATE BATCH COSTS
        st.subheader("⚗️ Batch Cost Calculator")
        
        # Fetch saved formulas
        formulas_response = supabase.table('formulas').select('*').execute()
        
        if formulas_response.data:
            formulas_df = pd.DataFrame(formulas_response.data)
            selected_formula = st.selectbox("Select a saved formula", formulas_df['formula_name'].tolist())
            
            batch_size_g = st.number_input("Batch Size (grams)", min_value=1, value=100)
            
            # Extract the recipe for the chosen formula
            selected_recipe = formulas_df[formulas_df['formula_name'] == selected_formula].iloc[0]['recipe']
            
            total_batch_cost = 0
            cost_breakdown = []
            
            # Calculate costs using LIVE inventory prices
            for ingredient, percentage in selected_recipe.items():
                amount_needed_g = (percentage / 100) * batch_size_g
                
                match = inventory[inventory['trade_name'] == ingredient]
                if not match.empty:
                    price_per_kg = float(match['price_per_kg'].values[0])
                    price_per_g = price_per_kg / 1000
                    ing_cost = amount_needed_g * price_per_g
                    total_batch_cost += ing_cost
                    
                    cost_breakdown.append({
                        "Ingredient": ingredient, 
                        "Amount Needed (g)": round(amount_needed_g, 2), 
                        "Cost ($)": f"${ing_cost:.2f}"
                    })
                else:
                    st.error(f"⚠️ Missing live price data for: {ingredient}. Please add it to your library.")
                    
            if cost_breakdown:
                st.table(pd.DataFrame(cost_breakdown))
                st.success(f"**Total Batch Cost: ${total_batch_cost:.2f}**")
        else:
            st.info("No formulas saved yet. Build your first one above!")
