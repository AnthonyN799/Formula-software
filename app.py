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

    # 1. Fetch live data from Supabase!
    response = supabase.table('inventory').select("*").execute()
    
    # 2. Convert it to a Pandas Table for Streamlit
    if response.data:
        inventory = pd.DataFrame(response.data)
    else:
        # Failsafe empty table if database is completely wiped
        inventory = pd.DataFrame(columns=['id', 'trade_name', 'inci_name', 'price_per_kg', 'quantity_kg', 'function', 'recommended_use'])

    # --- PAGE 1: RAW MATERIAL LIBRARY ---
    if menu == "Raw Material Library":
        st.header("Raw Material Library")
        
        # Display the live database table securely
        st.dataframe(
            inventory[['trade_name', 'inci_name', 'price_per_kg', 'quantity_kg', 'function', 'recommended_use']], 
            use_container_width=True, 
            hide_index=True
        )
        
        st.divider()
        
        st.subheader("➕ Add New Raw Material")
        with st.form("add_material_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                new_trade = st.text_input("Trade Name")
                new_inci = st.text_input("INCI Name")
                new_func = st.text_input("Function")
                
            with col2:
                new_price = st.number_input("Price/Kg ($)", min_value=0.0, format="%.2f")
                new_qty = st.number_input("Starting Quantity (Kg)", min_value=0.0, format="%.3f")
                new_use = st.text_input("Recommended Use")
            
            submitted = st.form_submit_button("Save to Database")
            
            if submitted:
                if new_trade != "":
                    # Package the data exactly how Supabase expects it
                    new_data = {
                        "trade_name": new_trade,
                        "inci_name": new_inci,
                        "price_per_kg": new_price,
                        "quantity_kg": new_qty,
                        "function": new_func,
                        "recommended_use": new_use
                    }
                    # Send it permanently to the database
                    supabase.table('inventory').insert(new_data).execute()
                    
                    st.success(f"{new_trade} permanently saved to the vault!")
                    st.rerun() # Refresh to show the new item
                else:
                    st.error("Please enter a Trade Name.")

    # --- PAGE 2: FORMULA CALCULATOR ---
    elif menu == "Formula Calculator":
        st.header("Production Costs: Hair Growth Oil")
        
        recipe = {
            'Rosemary Oil': 5,
            'Peppermint Oil': 2,
            'Cypress Oil': 3,
            'Sweet Almond Oil': 90
        }
        
        recipe_df = pd.DataFrame(list(recipe.items()), columns=['Ingredient', 'Amount (grams)'])
        st.table(recipe_df)

        st.markdown("---")
        batch_size = st.number_input("How many 100g bottles are you making?", min_value=1, value=10)
        
        total_batch_cost = 0
        missing_ingredients = []
        
        # Calculate costs using the live Supabase data
        for ingredient, amount_per_bottle in recipe.items():
            total_amount_needed_grams = amount_per_bottle * batch_size
            
            # Find the ingredient in our live database pull
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
            st.info(f"Cost per individual bottle: ${(total_batch_cost / batch_size):.2f}")
