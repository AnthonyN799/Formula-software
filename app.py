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

if check_password():
    
    # --- APP MEMORY (Session State) ---
    # This gives the software a "brain" to remember your edits while you are logged in
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame({
            'Trade Name': ['Rosemary Oil', 'Sweet Almond Oil', 'Cypress Oil', 'Peppermint Oil'],
            'INCI Name': ['Rosmarinus Officinalis Leaf Oil', 'Prunus Amygdalus Dulcis Oil', 'Cupressus Sempervirens Leaf Oil', 'Mentha Piperita Oil'],
            'Price/Kg ($)': [150.00, 50.00, 200.00, 120.00],
            'Remaining Quantity (Kg)': [0.5, 2.0, 0.3, 0.4],
            'Function': ['Active / Hair Stimulant', 'Carrier / Emollient', 'Active / Astringent', 'Active / Cooling'],
            'Recommended Use': ['1% - 2%', 'Up to 100%', '0.5% - 1%', '0.5% - 2%']
        })

    menu = st.sidebar.radio("Navigation", ["Raw Material Library", "Formula Calculator"])

    # --- PAGE 1: RAW MATERIAL LIBRARY ---
    if menu == "Raw Material Library":
        st.header("Raw Material Library")
        st.write("✏️ **Double-click any cell below to edit prices or stock.**")
        
        # 1. The Editable Table
        st.session_state.inventory = st.data_editor(
            st.session_state.inventory, 
            use_container_width=True,
            num_rows="dynamic", # This even lets you delete rows!
            hide_index=True
        )
        
        st.divider()
        
        # 2. Add New Material Form
        st.subheader("➕ Add New Raw Material")
        with st.form("add_material_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_trade = st.text_input("Trade Name (e.g., Lavender Oil)")
                new_inci = st.text_input("INCI Name")
                new_func = st.text_input("Function (e.g., Active / Calming)")
                
            with col2:
                new_price = st.number_input("Price/Kg ($)", min_value=0.0, format="%.2f")
                new_qty = st.number_input("Starting Quantity (Kg)", min_value=0.0, format="%.3f")
                new_use = st.text_input("Recommended Use (e.g., 1% - 5%)")
            
            submitted = st.form_submit_button("Save to Library")
            
            if submitted:
                if new_trade != "":
                    # Create the new row
                    new_row = pd.DataFrame({
                        'Trade Name': [new_trade],
                        'INCI Name': [new_inci],
                        'Price/Kg ($)': [new_price],
                        'Remaining Quantity (Kg)': [new_qty],
                        'Function': [new_func],
                        'Recommended Use': [new_use]
                    })
                    # Add it to the memory
                    st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True)
                    st.success(f"{new_trade} added successfully!")
                    st.rerun() # Refreshes the screen instantly to show the new item
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
        
        for ingredient, amount_per_bottle in recipe.items():
            total_amount_needed_grams = amount_per_bottle * batch_size
            
            # Look up the price in our interactive memory
            try:
                price_per_kg = st.session_state.inventory.loc[st.session_state.inventory['Trade Name'] == ingredient, 'Price/Kg ($)'].values[0]
                price_per_gram = float(price_per_kg) / 1000
                total_batch_cost += (total_amount_needed_grams * price_per_gram)
            except IndexError:
                missing_ingredients.append(ingredient)
                
        if missing_ingredients:
            st.error(f"Missing price data for: {', '.join(missing_ingredients)}. Please add them to your library.")
        else:
            st.success(f"**Total Cost to produce {batch_size} bottles: ${total_batch_cost:.2f}**")
            st.info(f"Cost per individual bottle: ${(total_batch_cost / batch_size):.2f}")
