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
    
    menu = st.sidebar.radio("Navigation", ["Raw Material Library", "Formula Calculator"])

    # --- MASTER DATABASE ---
    # Upgraded to professional Kg and INCI standards
    materials_data = {
        'Trade Name': ['Rosemary Oil', 'Sweet Almond Oil', 'Cypress Oil', 'Peppermint Oil'],
        'INCI Name': [
            'Rosmarinus Officinalis Leaf Oil', 
            'Prunus Amygdalus Dulcis Oil', 
            'Cupressus Sempervirens Leaf Oil',
            'Mentha Piperita Oil'
        ],
        'Price/Kg ($)': [150.00, 50.00, 200.00, 120.00],
        'Remaining Quantity (Kg)': [0.5, 2.0, 0.3, 0.4],
        'Function': ['Active / Hair Stimulant', 'Carrier / Emollient', 'Active / Astringent', 'Active / Cooling'],
        'Recommended Use': ['1% - 2%', 'Up to 100%', '0.5% - 1%', '0.5% - 2%'],
        'TDS_File': ['Attached', 'Attached', 'Attached', 'Attached'],
        'MSDS_File': ['Attached', 'Attached', 'Attached', 'Attached']
    }
    inventory = pd.DataFrame(materials_data)

    # --- PAGE 1: RAW MATERIAL LIBRARY ---
    if menu == "Raw Material Library":
        st.header("Raw Material Library")
        
        # 1. The Clean Overview Table (Only shows the 4 requested columns)
        overview_df = inventory[['Trade Name', 'INCI Name', 'Price/Kg ($)', 'Remaining Quantity (Kg)']]
        st.dataframe(overview_df, use_container_width=True, hide_index=True)
        
        st.divider() # Draws a clean visual line
        
        # 2. The Detailed Dossier
        st.subheader("Raw Material Dossier")
        st.write("Select a material to view its full technical profile and documents.")
        
        # Dropdown to select a material
        selected_material = st.selectbox("Select Raw Material", inventory['Trade Name'].tolist())
        
        # Extract the specific row of data for the chosen material
        material_info = inventory[inventory['Trade Name'] == selected_material].iloc[0]
        
        # Display the info in two clean columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**INCI Name:** {material_info['INCI Name']}")
            st.markdown(f"**Function:** {material_info['Function']}")
            st.markdown(f"**Recommended Use:** {material_info['Recommended Use']}")
            
        with col2:
            st.markdown(f"**Current Stock:** {material_info['Remaining Quantity (Kg)']} Kg")
            st.markdown(f"**Price:** ${material_info['Price/Kg ($)']} / Kg")
            # Mock buttons for document downloads
            st.button(f"📄 Download TDS for {selected_material}")
            st.button(f"⚠️ Download MSDS for {selected_material}")


    # --- PAGE 2: FORMULA CALCULATOR ---
    elif menu == "Formula Calculator":
        st.header("Production Costs: Hair Growth Oil")
        
        st.subheader("Standard 100g Recipe")
        # Recipes usually use grams in professional formulations
        recipe = {
            'Rosemary Oil': 5,
            'Peppermint Oil': 2,
            'Cypress Oil': 3,
            'Sweet Almond Oil': 90
        }
        
        recipe_df = pd.DataFrame(list(recipe.items()), columns=['Ingredient', 'Amount (grams)'])
        st.table(recipe_df)

        st.markdown("---")
        st.subheader("Batch Calculator")
        batch_size = st.number_input("How many 100g bottles are you making?", min_value=1, value=10)
        
        total_batch_cost = 0
        
        for ingredient, amount_per_bottle in recipe.items():
            total_amount_needed_grams = amount_per_bottle * batch_size
            
            # Find the Kg price and divide by 1000 to get the price per gram
            price_per_kg = inventory.loc[inventory['Trade Name'] == ingredient, 'Price/Kg ($)'].values[0]
            price_per_gram = price_per_kg / 1000
            
            ingredient_cost = total_amount_needed_grams * price_per_gram
            total_batch_cost += ingredient_cost
            
        st.success(f"**Total Cost to produce {batch_size} bottles: ${total_batch_cost:.2f}**")
        st.info(f"Cost per individual bottle: ${(total_batch_cost / batch_size):.2f}")
