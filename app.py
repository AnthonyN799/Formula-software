import streamlit as st
import pandas as pd

# --- Security ---
def check_password():
    st.title("Therapeutic Oils")
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

    if menu == "Inventory":
        st.header("Raw Material Stock")
        
        # Your custom library
        materials = pd.DataFrame({
            'Material': ['Rosemary Oil', 'Sweet Almond Oil', 'Cypress Oil', 'Peppermint Oil'],
            'Stock_ml': [500, 2000, 300, 400],
            'Cost_per_ml': [0.15, 0.05, 0.20, 0.12]
        })
        
        st.dataframe(materials, use_container_width=True)
        
        if st.button("Log New Delivery"):
            st.info("Inventory update feature coming next!")

    elif menu == "Formula Calculator":
        st.header("Production Costs")
        st.write("Select a formula to calculate batch costs.")
        # Math logic goes here later!
