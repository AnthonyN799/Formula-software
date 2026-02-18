import streamlit as st
import pandas as pd

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
    st.success("Welcome to the Lab!")
    
    menu = st.sidebar.radio("Navigation", ["Inventory", "Formula Calculator"])

    # --- INVENTORY DATABASE ---
    # We define this at the top so both pages can use it
    materials_data = {
        'Material': ['Rosemary Oil', 'Peppermint Oil', 'Cypress Oil', 'Sweet Almond Oil', 'Coconut Oil'],
        'Stock_ml': [500, 400, 300, 2000, 1500],
        'Cost_per_ml': [0.15, 0.12, 0.20, 0.05, 0.04]
    }
    inventory = pd.DataFrame(materials_data)

    # --- PAGE 1: INVENTORY ---
    if menu == "Inventory":
        st.header("Raw Material Stock")
        st.dataframe(inventory, use_container_width=True)
        
        if st.button("Log New Delivery"):
            st.info("Inventory update feature coming next!")

    # --- PAGE 2: FORMULA CALCULATOR ---
    elif menu == "Formula Calculator":
        st.header("Production Costs: Hair Growth Oil")
        
        # 1. The Recipe (Per 100ml Bottle)
        st.subheader("Standard 100ml Recipe")
        recipe = {
            'Rosemary Oil': 5,
            'Peppermint Oil': 2,
            'Cypress Oil': 3,
            'Sweet Almond Oil': 90
        }
        
        # Display the recipe clearly
        recipe_df = pd.DataFrame(list(recipe.items()), columns=['Ingredient', 'Amount (ml)'])
        st.table(recipe_df)

        # 2. The Batch Calculator
        st.markdown("---")
        st.subheader("Batch Calculator")
        batch_size = st.number_input("How many 100ml bottles are you making?", min_value=1, value=10)
        
        # 3. The Math Engine
        total_batch_cost = 0
        
        for ingredient, amount_per_bottle in recipe.items():
            total_amount_needed = amount_per_bottle * batch_size
            
            # Find the cost per ml from our inventory database
            cost_per_ml = inventory.loc[inventory['Material'] == ingredient, 'Cost_per_ml'].values[0]
            
            # Calculate total cost for this ingredient
            ingredient_cost = total_amount_needed * cost_per_ml
            total_batch_cost += ingredient_cost
            
        # 4. The Results
        st.success(f"**Total Cost to produce {batch_size} bottles: ${total_batch_cost:.2f}**")
        st.info(f"Cost per individual bottle: ${(total_batch_cost / batch_size):.2f}")
