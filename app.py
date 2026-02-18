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
    menu = st.sidebar.radio("Navigation", ["Raw Material Library", "Formula Calculator"])

    # 1. Fetch live data from Supabase
    response = supabase.table('inventory').select("*").execute()
    
    if response.data:
        inventory = pd.DataFrame(response.data)
    else:
        inventory = pd.DataFrame(columns=['id', 'trade_name', 'inci_name', 'price_per_kg', 'quantity_kg', 'function', 'recommended_use', 'tds_url', 'msds_url'])

    # --- PAGE 1: RAW MATERIAL LIBRARY ---
    if menu == "Raw Material Library":
        st.header("Raw Material Library")
        
        # 1. The Clean Overview Table
        st.dataframe(
            inventory[['trade_name', 'inci_name', 'price_per_kg', 'quantity_kg', 'function']], 
            use_container_width=True, 
            hide_index=True
        )
        
        st.divider()
        
        # 2. The Document Vault (View and Download)
        st.subheader("📁 Document Vault")
        st.write("Select a material to access its safety and technical documents.")
        
        if not inventory.empty:
            selected_material = st.selectbox("Select Material", inventory['trade_name'].tolist())
            material_info = inventory[inventory['trade_name'] == selected_material].iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                if pd.notna(material_info.get('tds_url')) and material_info['tds_url'] != "":
                    st.link_button(f"📄 Download TDS for {selected_material}", material_info['tds_url'])
                else:
                    st.warning("No TDS on file.")
                    
            with col2:
                if pd.notna(material_info.get('msds_url')) and material_info['msds_url'] != "":
                    st.link_button(f"⚠️ Download MSDS for {selected_material}", material_info['msds_url'])
                else:
                    st.warning("No MSDS on file.")
                    
        st.divider()
        
        # 3. Add New Material (Now with File Uploaders!)
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
            
            if submitted:
                if new_trade != "":
                    tds_url = ""
                    msds_url = ""
                    
                    # Upload TDS to Supabase Storage if attached
                    if tds_file is not None:
                        file_name = f"{new_trade.replace(' ', '_')}_TDS.pdf"
                        supabase.storage.from_("documents").upload(file_name, tds_file.getvalue(), {"content-type": "application/pdf"})
                        tds_url = supabase.storage.from_("documents").get_public_url(file_name)
                        
                    # Upload MSDS to Supabase Storage if attached
                    if msds_file is not None:
                        file_name = f"{new_trade.replace(' ', '_')}_MSDS.pdf"
                        supabase.storage.from_("documents").upload(file_name, msds_file.getvalue(), {"content-type": "application/pdf"})
                        msds_url = supabase.storage.from_("documents").get_public_url(file_name)

                    # Package the data
                    new_data = {
                        "trade_name": new_trade,
                        "inci_name": new_inci,
                        "price_per_kg": new_price,
                        "quantity_kg": new_qty,
                        "function": new_func,
                        "recommended_use": new_use,
                        "tds_url": tds_url,
                        "msds_url": msds_url
                    }
                    # Send it permanently to the database
                    supabase.table('inventory').insert(new_data).execute()
                    
                    st.success(f"{new_trade} and documents saved to the vault!")
                    st.rerun() 
                else:
                    st.error("Please enter a Trade Name.")

    # --- PAGE 2: FORMULA CALCULATOR ---
    elif menu == "Formula Calculator":
        st.header("Production Costs: Hair Growth Oil")
        recipe = {'Rosemary Oil': 5, 'Peppermint Oil': 2, 'Cypress Oil': 3, 'Sweet Almond Oil': 90}
        st.table(pd.DataFrame(list(recipe.items()), columns=['Ingredient', 'Amount (grams)']))

        st.markdown("---")
        batch_size = st.number_input("How many 100g bottles are you making?", min_value=1, value=10)
        
        total_batch_cost = 0
        missing_ingredients = []
        
        for ingredient, amount_per_bottle in recipe.items():
            total_amount_needed_grams = amount_per_bottle * batch_size
            match = inventory[inventory['trade_name'] == ingredient]
            
            if not match.empty:
                price_per_kg = float(match['price_per_kg'].values[0])
                price_per_gram = price_per_kg / 1000
                total_batch_cost += (total_amount_needed_grams * price_per_gram)
            else:
                missing_ingredients.append(ingredient)
                
        if missing_ingredients:
            st.error(f"Missing price data in database for: {', '.join(missing_ingredients)}")
        else:
            st.success(f"**Total Cost to produce {batch_size} bottles: ${total_batch_cost:.2f}**")
