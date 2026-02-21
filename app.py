import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from PIL import Image
import re

# --- 1. PAGE CONFIGURATION ---
try:
    logo_img = Image.open("logo.jpg")
    st.set_page_config(page_title="Therapeutic Oils | Lab Portal", page_icon=logo_img, layout="wide", initial_sidebar_state="expanded")
except FileNotFoundError:
    st.set_page_config(page_title="Therapeutic Oils | Lab Portal", layout="wide", initial_sidebar_state="expanded")

# --- 2. CUSTOM CSS FOR PREMIUM UI ---
def inject_custom_css():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} 
        header {background-color: transparent !important;}
        .stApp { background-color: #FAFAFA; font-family: 'Inter', -apple-system, sans-serif; }
        [data-testid="stMetricValue"] { font-size: 2.2rem; font-weight: 300; color: #1E293B; letter-spacing: -0.02em; }
        [data-testid="stMetricLabel"] { font-size: 0.85rem; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; }
        [data-testid="metric-container"] { background-color: #FFFFFF; border: 1px solid #E2E8F0; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
        .stButton>button { border-radius: 4px; font-weight: 500; border: 1px solid #CBD5E1; background-color: #FFFFFF; color: #334155; transition: all 0.2s ease; }
        .stButton>button:hover { border-color: #94A3B8; color: #0F172A; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .stButton>button[kind="primary"] { background-color: #0F172A; color: #FFFFFF; border: none; }
        .stButton>button[kind="primary"]:hover { background-color: #1E293B; }
        h1, h2, h3 { color: #0F172A; font-weight: 400; letter-spacing: -0.01em; }
        </style>
    """, unsafe_allow_html=True)

# --- Connect to the Database ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_connection()

# --- Authentication Logic ---
def check_password():
    if "authenticated" not in st.session_state: st.session_state["authenticated"] = False
    if st.session_state["authenticated"]: return True
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("<br><br><br>", unsafe_allow_html=True)
        try: st.image("logo.jpg", use_container_width=True)
        except: st.markdown("<h1 style='text-align: center; font-weight: 300;'>Therapeutic Oils</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748B;'>Secure Laboratory Portal</p>", unsafe_allow_html=True)
        password = st.text_input("Passcode", type="password", placeholder="Enter team passcode...")
        if st.button("Authenticate", use_container_width=True, type="primary"):
            if password == "lab2026":
                st.session_state["authenticated"] = True; st.rerun()
            else: st.error("Incorrect passcode.")
    return False

# --- Main App Execution ---
if check_password():
    inject_custom_css()
    
    with st.sidebar:
        try: st.image("logo.jpg", use_container_width=True)
        except: st.markdown("<h3 style='text-align: center; padding-bottom: 20px;'>T / O</h3>", unsafe_allow_html=True)
        st.write("##")
        menu = st.radio("System Menu", [
            "Financial Overview", 
            "Raw Material Library", 
            "Packaging Library", 
            "Finished Products", 
            "Formula Hub", 
            "COGS Calculator", 
            "Production Logs"
        ])
        st.write("<br><br>", unsafe_allow_html=True)
        if st.button("Log Out", use_container_width=True): st.session_state["authenticated"] = False; st.rerun()

    # --- Fetch Global Data ---
    inv_resp = supabase.table('inventory').select("*").execute()
    inventory = pd.DataFrame(inv_resp.data).sort_values('rm_code') if inv_resp.data else pd.DataFrame()
    
    pk_resp = supabase.table('packaging').select("*").execute()
    packaging = pd.DataFrame(pk_resp.data).sort_values('pm_code') if pk_resp.data else pd.DataFrame()
    
    fp_resp = supabase.table('finished_products').select("*").execute()
    finished_goods = pd.DataFrame(fp_resp.data).sort_values('fp_code') if fp_resp.data else pd.DataFrame()

    formulas_resp = supabase.table('formulas').select('*').execute()
    formulas_df = pd.DataFrame(formulas_resp.data) if formulas_resp.data else pd.DataFrame()
    
    cogs_resp = supabase.table('cogs_records').select('*').execute()
    cogs_records_df = pd.DataFrame(cogs_resp.data).sort_values('product_name') if cogs_resp.data else pd.DataFrame()

    # --- 1. FINANCIAL OVERVIEW ---
    if menu == "Financial Overview":
        st.title("Financial Overview")
        st.markdown("<p style='color: #64748B;'>Live tracking of physical assets, inventory valuation, and retail projections.</p>", unsafe_allow_html=True)
        st.write("##")
        
        rm_total = (inventory['price_per_kg'] * inventory['quantity_kg']).sum() if not inventory.empty else 0.0
        pm_total = (packaging['cost_per_unit'] * packaging['remaining_quantity']).sum() if not packaging.empty else 0.0
        fp_cogs_total = (finished_goods['unit_cogs'] * finished_goods['stock_quantity']).sum() if not finished_goods.empty else 0.0
        fp_retail_total = (finished_goods['retail_price'] * finished_goods['stock_quantity']).sum() if not finished_goods.empty else 0.0
        
        vault_assets = rm_total + pm_total + fp_cogs_total
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Raw Materials", f"${rm_total:,.2f}")
        with c2: st.metric("Packaging", f"${pm_total:,.2f}")
        with c3: st.metric("Finished Goods (COGS)", f"${fp_cogs_total:,.2f}")
        with c4: st.metric("Total Vault Assets", f"${vault_assets:,.2f}")
        
        st.write("---")
        st.markdown("#### Projected Revenue")
        st.metric("Potential Retail Value on Shelf", f"${fp_retail_total:,.2f}", f"Est. Gross Profit: ${(fp_retail_total - fp_cogs_total):,.2f}")
        
        st.write("---")
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("#### Top Raw Materials")
            if not inventory.empty:
                inv_chart = inventory.copy(); inv_chart['Total Value ($)'] = inv_chart['price_per_kg'] * inv_chart['quantity_kg']
                st.dataframe(inv_chart.sort_values(by="Total Value ($)", ascending=False).head(5)[['trade_name', 'Total Value ($)']], use_container_width=True, hide_index=True)
        with c_right:
            st.markdown("#### Top Finished Products")
            if not finished_goods.empty:
                fg_chart = finished_goods.copy(); fg_chart['Retail Value ($)'] = fg_chart['retail_price'] * fg_chart['stock_quantity']
                st.dataframe(fg_chart.sort_values(by="Retail Value ($)", ascending=False).head(5)[['product_name', 'Retail Value ($)']], use_container_width=True, hide_index=True)

    # --- 2. RAW MATERIAL LIBRARY ---
    elif menu == "Raw Material Library":
        st.title("Raw Material Library")
        st.markdown("<p style='color: #64748B;'>Manage essential oils, carriers, and active ingredients.</p>", unsafe_allow_html=True)
        if not inventory.empty:
            display_inv = inventory.copy(); display_inv['Cost/g ($)'] = (display_inv['price_per_kg'] / 1000).map('${:,.4f}'.format); display_inv.insert(0, '🔍', False) 
            with st.container(border=True):
                edited_inv = st.data_editor(display_inv[['🔍', 'rm_code', 'trade_name', 'inci_name', 'price_per_kg', 'Cost/g ($)', 'quantity_kg']], use_container_width=True, hide_index=True, disabled=['rm_code', 'Cost/g ($)'])
                if st.button("💾 Synchronize Vault"):
                    for idx, row in edited_inv.iterrows():
                        orig = inventory.loc[idx]
                        if row['trade_name'] != orig['trade_name'] or row['inci_name'] != orig['inci_name'] or row['price_per_kg'] != orig['price_per_kg'] or row['quantity_kg'] != orig['quantity_kg']:
                            supabase.table('inventory').update({"trade_name": row['trade_name'], "inci_name": row['inci_name'], "price_per_kg": row['price_per_kg'], "quantity_kg": row['quantity_kg']}).eq('id', int(orig['id'])).execute()
                    st.rerun()
            selected_mats = edited_inv[edited_inv['🔍'] == True]
            if not selected_mats.empty:
                mat = inventory.loc[selected_mats.index[0]]; st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### {mat['trade_name']}")
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Code:** {mat['rm_code']}<br>**INCI:** {mat['inci_name']}", unsafe_allow_html=True)
                    c2.write(f"**Stock:** {mat['quantity_kg']} Kg<br>**Price:** ${mat['price_per_kg']}/Kg", unsafe_allow_html=True)
                    c3.write(f"**Shelf Value:** ${(mat['price_per_kg'] * mat['quantity_kg']):.2f}")
                    with st.expander("System Actions"):
                        del_pass = st.text_input("Authorization Passcode", type="password", key="dmp")
                        if st.button("Erase Record") and del_pass == "lab2026":
                            supabase.table('inventory').delete().eq('id', int(mat['id'])).execute(); st.rerun()
        st.write("---")
        with st.expander("➕ Register New Material"):
            with st.form("add_material", clear_on_submit=True):
                c1, c2 = st.columns(2); new_t = c1.text_input("Trade Name"); new_i = c1.text_input("INCI Name"); new_p = c2.number_input("Price/Kg ($)", min_value=0.0); new_q = c2.number_input("Initial Qty (Kg)", min_value=0.0)
                if st.form_submit_button("Register") and new_t != "":
                    next_id = 1 if inventory.empty else int(inventory['id'].max()) + 1
                    supabase.table('inventory').insert({"rm_code": f"RM{next_id:05d}", "trade_name": new_t, "inci_name": new_i, "price_per_kg": new_p, "quantity_kg": new_q}).execute(); st.rerun()

    # --- 3. PACKAGING LIBRARY ---
    elif menu == "Packaging Library":
        st.title("Packaging Library")
        st.markdown("<p style='color: #64748B;'>Track bottles, droppers, caps, and labels.</p>", unsafe_allow_html=True)
        if not packaging.empty:
            display_pk = packaging.copy(); display_pk.insert(0, '🔍', False)
            with st.container(border=True):
                edited_pk = st.data_editor(display_pk[['🔍', 'pm_code', 'material_name', 'supplier', 'cost_per_unit', 'remaining_quantity']], use_container_width=True, hide_index=True, disabled=['pm_code'])
                if st.button("💾 Synchronize Vault"):
                    for idx, row in edited_pk.iterrows():
                        orig = packaging.loc[idx]
                        if row['material_name'] != orig['material_name'] or row['supplier'] != orig['supplier'] or row['cost_per_unit'] != orig['cost_per_unit'] or row['remaining_quantity'] != orig['remaining_quantity']:
                            supabase.table('packaging').update({"material_name": row['material_name'], "supplier": row['supplier'], "cost_per_unit": row['cost_per_unit'], "remaining_quantity": row['remaining_quantity']}).eq('id', int(orig['id'])).execute()
                    st.rerun()
            selected_pk = edited_pk[edited_pk['🔍'] == True]
            if not selected_pk.empty:
                p_mat = packaging.loc[selected_pk.index[0]]; st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### {p_mat['material_name']}")
                    st.write(f"**Code:** {p_mat['pm_code']} | **Supplier:** {p_mat['supplier']} | **Stock:** {p_mat['remaining_quantity']} Units")
                    with st.expander("System Actions"):
                        if st.button("Erase Record") and st.text_input("Authorization", type="password", key="dpp") == "lab2026":
                            supabase.table('packaging').delete().eq('id', int(p_mat['id'])).execute(); st.rerun()
        st.write("---")
        with st.expander("➕ Register New Packaging"):
            with st.form("add_packaging", clear_on_submit=True):
                c1, c2 = st.columns(2); p_n = c1.text_input("Material Name"); p_s = c1.text_input("Supplier"); p_c = c2.number_input("Cost/Unit ($)", min_value=0.0); p_q = c2.number_input("Initial Qty", min_value=0.0)
                if st.form_submit_button("Register") and p_n != "":
                    next_pm = 1 if packaging.empty else int(packaging['id'].max()) + 1
                    supabase.table('packaging').insert({"pm_code": f"PM{next_pm:05d}", "material_name": p_n, "supplier": p_s, "cost_per_unit": p_c, "remaining_quantity": p_q}).execute(); st.rerun()

    # --- 4. FINISHED PRODUCTS LIBRARY ---
    elif menu == "Finished Products":
        st.title("Finished Products")
        st.markdown("<p style='color: #64748B;'>Manage retail-ready inventory directly from your saved COGS profiles.</p>", unsafe_allow_html=True)
        
        if not finished_goods.empty:
            display_fp = finished_goods.copy()
            display_fp.insert(0, '🔍', False)
            
            st.write("💡 *Edit stock quantities directly in the table below.*")
            with st.container(border=True):
                edited_fp = st.data_editor(
                    display_fp[['🔍', 'fp_code', 'product_name', 'stock_quantity', 'unit_cogs', 'retail_price']],
                    use_container_width=True, hide_index=True, disabled=['fp_code', 'unit_cogs', 'retail_price'],
                    column_config={
                        "unit_cogs": st.column_config.NumberColumn("Unit COGS", format="$%.2f"),
                        "retail_price": st.column_config.NumberColumn("Retail Price", format="$%.2f")
                    }
                )
                
                if st.button("💾 Synchronize Vault", type="primary"):
                    for idx, row in edited_fp.iterrows():
                        orig = finished_goods.loc[idx]
                        if row['stock_quantity'] != orig['stock_quantity']:
                            supabase.table('finished_products').update({
                                "stock_quantity": row['stock_quantity']
                            }).eq('id', int(orig['id'])).execute()
                    st.success("Finished goods synced!")
                    st.rerun()

            selected_fp = edited_fp[edited_fp['🔍'] == True]
            if not selected_fp.empty:
                fp_item = finished_goods.loc[selected_fp.index[0]]
                st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### {fp_item['product_name']}")
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Code:** {fp_item['fp_code']}")
                    c2.write(f"**In Stock:** {fp_item['stock_quantity']} Units")
                    
                    margin = ((fp_item['retail_price'] - fp_item['unit_cogs']) / fp_item['retail_price'] * 100) if fp_item['retail_price'] > 0 else 0
                    c3.write(f"**Profit Margin:** {margin:.1f}%")
                    
                    with st.expander("System Actions"):
                        if st.button("Erase Record") and st.text_input("Authorization Passcode", type="password", key="dfpp") == "lab2026":
                            supabase.table('finished_products').delete().eq('id', int(fp_item['id'])).execute(); st.rerun()
        else:
            st.info("No finished products currently in stock.")

        st.write("---")
        with st.expander("➕ Log New Finished Product Batch"):
            if not cogs_records_df.empty:
                with st.form("add_fp", clear_on_submit=True):
                    c1, c2 = st.columns([2, 1])
                    cogs_opts = [f"[{r['id']}] {r['product_name']}" for _, r in cogs_records_df.iterrows()]
                    sel_cogs = c1.selectbox("Select Target Product (From COGS Vault)", cogs_opts)
                    fp_q = c2.number_input("Bottles Produced (Qty)", min_value=1, value=10, step=1)
                    
                    if st.form_submit_button("Add to Stock"):
                        cogs_id = int(sel_cogs.split("]")[0].replace("[", ""))
                        matched_cogs = cogs_records_df[cogs_records_df['id'] == cogs_id].iloc[0]
                        target_name = matched_cogs['product_name']
                        target_cogs = float(matched_cogs['total_cogs'])
                        target_retail = float(matched_cogs['target_retail'])
                        
                        if not finished_goods.empty and target_name in finished_goods['product_name'].values:
                            existing_product = finished_goods[finished_goods['product_name'] == target_name]
                            existing_id = int(existing_product.iloc[0]['id'])
                            new_qty = int(existing_product.iloc[0]['stock_quantity']) + fp_q
                            supabase.table('finished_products').update({"stock_quantity": new_qty, "unit_cogs": target_cogs, "retail_price": target_retail}).eq('id', existing_id).execute()
                        else:
                            next_fp = 1 if finished_goods.empty else int(finished_goods['id'].max()) + 1
                            supabase.table('finished_products').insert({"fp_code": f"FP{next_fp:05d}", "product_name": target_name, "stock_quantity": fp_q, "unit_cogs": target_cogs, "retail_price": target_retail}).execute()
                        st.rerun()
            else:
                st.warning("⚠️ You need to architect and save a product profile in the **COGS Calculator** before you can log it to your finished inventory.")

    # --- 5. FORMULA HUB (UPGRADED WITH VERSIONING) ---
    elif menu == "Formula Hub":
        st.title("The Formula Hub")
        st.markdown("<p style='color: #64748B;'>Design, calculate, execute, and version control batch productions.</p>", unsafe_allow_html=True)
        
        if not formulas_df.empty:
            st.write("💡 *Click on any formula row below to inspect its recipe and execute a production batch.*")
            f_select = st.dataframe(formulas_df[['fr_code', 'formula_name']], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

            if f_select.selection.rows:
                f_idx = f_select.selection.rows[0]
                sel_f = formulas_df.iloc[f_idx]
                recipe_data = sel_f['recipe']
                
                st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### ⚗️ {sel_f['fr_code']} - {sel_f['formula_name']}")
                    b_size = st.number_input("Target Batch Size (grams)", min_value=1.0, value=1000.0, step=100.0)
                    st.write("---")
                    
                    calc_data = []; stock_ok = True; total_cost = 0.0
                    for ing, p in recipe_data.items():
                        req_g = (p/100) * b_size
                        m = inventory[inventory['trade_name'] == ing]
                        if not m.empty:
                            s_kg = float(m['quantity_kg'].values[0]); p_kg = float(m['price_per_kg'].values[0])
                            if s_kg < (req_g/1000): stock_ok = False
                            cost = (req_g/1000)*p_kg
                            total_cost += cost
                            calc_data.append({"Material": ing, "Formula %": f"{p}%", "Needed (g)": f"{req_g:.2f}", "Stock Status": "✅ Available" if s_kg >= (req_g/1000) else "❌ Shortage", "Est. Cost": f"${cost:.4f}", "req_kg": req_g/1000, "stock_kg": s_kg})
                        else:
                            stock_ok = False
                            calc_data.append({"Material": ing, "Formula %": f"{p}%", "Needed (g)": f"{req_g:.2f}", "Stock Status": "⚠️ Not in Vault", "Est. Cost": "$0.00", "req_kg": 0, "stock_kg": 0})
                    
                    st.dataframe(pd.DataFrame(calc_data)[['Material', 'Formula %', 'Needed (g)', 'Stock Status', 'Est. Cost']], use_container_width=True, hide_index=True)
                    
                    col_cost, col_btn = st.columns([1, 1])
                    col_cost.metric("Projected Batch Cost", f"${total_cost:.2f}")
                    with col_btn:
                        st.write("<br>", unsafe_allow_html=True)
                        if st.button("🚀 Execute Production", type="primary", use_container_width=True):
                            if stock_ok:
                                l_r = supabase.table('production_records').select("id").order("id", desc=True).limit(1).execute()
                                n_id = 1 if not l_r.data else l_r.data[0]['id'] + 1
                                b_no, l_no = f"B-{n_id:05d}", f"LOT-{datetime.now().strftime('%Y%m%d')}-{n_id:02d}"
                                for d in calc_data:
                                    supabase.table('inventory').update({'quantity_kg': d['stock_kg'] - d['req_kg']}).eq('trade_name', d['Material']).execute()
                                supabase.table('production_records').insert({"fr_code": sel_f['fr_code'], "formula_name": sel_f['formula_name'], "batch_number": b_no, "lot_number": l_no, "batch_size_g": b_size, "total_cost": total_cost}).execute()
                                st.balloons(); st.rerun()
                            else: st.error("Cannot produce: Material Shortage detected.")
                    
                    # VERSIONING AND DELETION
                    st.divider()
                    c_act1, c_act2 = st.columns(2)
                    with c_act1:
                        with st.expander("🔄 Create New Edition (Version)"):
                            st.info("Loads this recipe into the Architect below to create a new GMP-compliant version with a fresh FR code.")
                            if st.button("Load into Architect", use_container_width=True):
                                df_data = [{"Ingredient": k, "%": v} for k, v in recipe_data.items()]
                                st.session_state.builder = pd.DataFrame(df_data)
                                
                                # Auto-bump version number
                                match = re.search(r' V(\d+)$', sel_f['formula_name'])
                                if match:
                                    new_v = int(match.group(1)) + 1
                                    new_name = re.sub(r' V\d+$', f' V{new_v}', sel_f['formula_name'])
                                else:
                                    new_name = f"{sel_f['formula_name']} V2"
                                st.session_state.draft_name = new_name
                                st.rerun()
                                
                    with c_act2:
                        with st.expander("System Actions: Erase Formula"):
                            del_f_pass = st.text_input("Authorization Passcode", type="password", key="dfp")
                            if st.button("Permanently Delete Formula") and del_f_pass == "lab2026":
                                supabase.table('formulas').delete().eq('id', int(sel_f['id'])).execute(); st.rerun()
        else:
            st.info("No formulas architected yet.")

        st.write("---")
        with st.expander("⚙️ Architect New Formula", expanded=True):
            c_build, c_metrics = st.columns([3, 2])
            with c_build:
                # Pre-fill name if coming from "Create New Edition"
                f_name = st.text_input("Formula Moniker", value=st.session_state.get("draft_name", ""), placeholder="e.g., Actiflam Hair Growth Oil V2")
                if "builder" not in st.session_state: st.session_state.builder = pd.DataFrame([{"Ingredient": None, "%": 0.0}])
                ing_options = inventory['trade_name'].tolist() if not inventory.empty else ["No materials registered"]
                edit_df = st.data_editor(st.session_state.builder, num_rows="dynamic", use_container_width=True, column_config={"Ingredient": st.column_config.SelectboxColumn("Ingredient", options=ing_options)})
            with c_metrics:
                st.write("<div style='margin-top: 2.2rem;'></div>", unsafe_allow_html=True)
                st.markdown("<p style='color: #64748B; font-weight: 600; font-size: 0.85rem; text-transform: uppercase;'>Live Cost Analysis (1 Kg Batch)</p>", unsafe_allow_html=True)
                total_cost_kg = 0.0; live_data = []
                for _, row in edit_df.iterrows():
                    ing = row['Ingredient']; perc = row['%']
                    if ing and pd.notna(ing) and ing in inventory['trade_name'].values:
                        price = float(inventory[inventory['trade_name'] == ing]['price_per_kg'].values[0])
                        cost_contrib = (perc / 100.0) * price; total_cost_kg += cost_contrib
                        live_data.append({"Material": ing, "RM Base Price": f"${price:,.2f}/Kg", "Cost Contrib.": f"${cost_contrib:,.2f}"})
                if live_data: st.dataframe(pd.DataFrame(live_data), use_container_width=True, hide_index=True)
                else: st.info("Select ingredients to see live costs.")
                st.metric("Total Formula Cost / Kg", f"${total_cost_kg:,.2f}")
                
                total_perc = edit_df["%"].sum()
                if round(total_perc, 2) == 100.0:
                    st.success("✅ Formula is balanced (100%)")
                    if st.button("Commit Formula to Vault", type="primary", use_container_width=True) and f_name:
                        fr_c = f"FR{len(formulas_df)+1:05d}"
                        supabase.table("formulas").insert({"fr_code": fr_c, "formula_name": f_name, "recipe": dict(zip(edit_df["Ingredient"], edit_df["%"]))}).execute()
                        
                        # Clear builder and draft name after saving
                        st.session_state.builder = pd.DataFrame([{"Ingredient": None, "%": 0.0}])
                        if "draft_name" in st.session_state:
                            del st.session_state["draft_name"]
                        st.rerun()
                else: st.warning(f"⚠️ Total: {total_perc}% (Must equal 100%)")

    # --- 6. COGS CALCULATOR ---
    elif menu == "COGS Calculator":
        st.title("Cost of Goods Sold (COGS)")
        st.markdown("<p style='color: #64748B;'>Calculate unit economics and profile profit margins.</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("#### Step 1: Physical Product Specs")
            c1, c2, c3 = st.columns(3)
            
            if not formulas_df.empty:
                f_opts = [f"[{r['fr_code']}] {r['formula_name']}" for _, r in formulas_df.iterrows()]
                sel_form = c1.selectbox("Base Formula", f_opts)
            else:
                sel_form = None; c1.warning("No formulas in vault.")
                
            fill_wt = c2.number_input("Fill Weight per Unit (grams)", min_value=1.0, value=30.0, step=5.0)
            
            if not packaging.empty:
                p_opts = [f"[{r['pm_code']}] {r['material_name']}" for _, r in packaging.iterrows()]
                p_opts.insert(0, "None / Custom")
                sel_pack = c3.selectbox("Primary Packaging", p_opts)
            else:
                sel_pack = "None / Custom"; c3.warning("No packaging in vault.")

        with st.container(border=True):
            st.markdown("#### Step 2: Component & Variable Costs (per unit)")
            cm1, cm2, cm3, cm4 = st.columns(4)
            cost_mfg = cm1.number_input("Labor / Mfg ($)", min_value=0.0, value=0.10, step=0.05)
            cost_lbl = cm2.number_input("Label Cost ($)", min_value=0.0, value=0.05, step=0.05)
            cost_sec = cm3.number_input("Secondary Box ($)", min_value=0.0, value=0.00, step=0.05)
            cost_ter = cm4.number_input("Tertiary/Carton ($)", min_value=0.0, value=0.00, step=0.05)

        st.write("##")

        # --- Math Engine ---
        bulk_cost = 0.0
        n_only = ""
        if sel_form:
            n_only = sel_form.split("] ")[1]
            rec = formulas_df[formulas_df['formula_name'] == n_only].iloc[0]['recipe']
            for ing, p in rec.items():
                req_g = (p/100) * fill_wt
                m = inventory[inventory['trade_name'] == ing]
                if not m.empty:
                    p_kg = float(m['price_per_kg'].values[0])
                    bulk_cost += (req_g/1000) * p_kg

        pack_cost = 0.0
        if sel_pack != "None / Custom":
            p_only = sel_pack.split("] ")[1]
            pack_cost = float(packaging[packaging['material_name'] == p_only].iloc[0]['cost_per_unit'])

        total_cogs = bulk_cost + pack_cost + cost_mfg + cost_lbl + cost_sec + cost_ter

        # --- Financial Results ---
        st.markdown("#### Cost Breakdown & Profit Margin")
        r1, r2 = st.columns([2, 1])
        
        with r1:
            st.dataframe(pd.DataFrame([
                {"Component": "Formula (Bulk Oil)", "Cost per Unit": f"${bulk_cost:.4f}"},
                {"Component": "Primary Bottle/Dropper", "Cost per Unit": f"${pack_cost:.4f}"},
                {"Component": "Labeling", "Cost per Unit": f"${cost_lbl:.4f}"},
                {"Component": "Secondary Packaging", "Cost per Unit": f"${cost_sec:.4f}"},
                {"Component": "Tertiary Packaging", "Cost per Unit": f"${cost_ter:.4f}"},
                {"Component": "Labor / Mfg Overhead", "Cost per Unit": f"${cost_mfg:.4f}"}
            ]), use_container_width=True, hide_index=True)
            
        with r2:
            with st.container(border=True):
                st.metric("Total COGS per Unit", f"${total_cogs:.2f}")
                target_retail = st.number_input("Target Retail Price ($)", min_value=0.0, value=total_cogs * 4 if total_cogs > 0 else 0.0, step=1.0)
                
                margin_pct = 0.0
                if target_retail > 0:
                    gross_profit = target_retail - total_cogs
                    margin_pct = (gross_profit / target_retail) * 100
                    st.write("---")
                    st.metric("Gross Profit", f"${gross_profit:.2f}", f"{margin_pct:.1f}% Margin")

        # --- Profile Save Section ---
        st.write("##")
        with st.container(border=True):
            st.markdown("#### 💾 Save COGS Configuration")
            sc1, sc2 = st.columns([3, 1])
            cogs_name = sc1.text_input("Product Name / SKU", placeholder="e.g., Actiflam 30ml Retail Bottle")
            
            sc2.write("<br>", unsafe_allow_html=True)
            if sc2.button("Commit Profile to Vault", type="primary", use_container_width=True):
                if cogs_name:
                    supabase.table('cogs_records').insert({
                        "product_name": cogs_name, "formula_name": n_only if sel_form else "None",
                        "fill_weight_g": fill_wt, "primary_packaging": sel_pack.split("] ")[1] if sel_pack != "None / Custom" else "Custom",
                        "bulk_cost": bulk_cost, "packaging_cost": pack_cost, "mfg_cost": cost_mfg, "label_cost": cost_lbl,
                        "total_cogs": total_cogs, "target_retail": target_retail, "gross_margin_pct": margin_pct
                    }).execute()
                    st.success(f"Saved profile: {cogs_name}")
                    st.rerun()
                else:
                    st.error("Please enter a Product Name before saving.")

        # --- Saved COGS Profiles Vault ---
        st.write("---")
        st.markdown("#### 📂 Saved COGS Profiles")
        if not cogs_records_df.empty:
            display_cogs = cogs_records_df.copy()
            display_cogs['Date'] = pd.to_datetime(display_cogs['created_at']).dt.strftime('%Y-%m-%d')
            display_cogs.insert(0, '🔍', False)
            
            st.write("💡 *Edit the 'product_name' or 'target_retail' directly in the table. Margins auto-update when saving.*")
            
            with st.container(border=True):
                edited_cogs = st.data_editor(
                    display_cogs[['🔍', 'Date', 'product_name', 'formula_name', 'fill_weight_g', 'total_cogs', 'target_retail', 'gross_margin_pct']],
                    use_container_width=True, hide_index=True, 
                    disabled=['Date', 'formula_name', 'fill_weight_g', 'total_cogs', 'gross_margin_pct'],
                    column_config={
                        "total_cogs": st.column_config.NumberColumn("Total COGS", format="$%.2f"),
                        "target_retail": st.column_config.NumberColumn("Target Retail", format="$%.2f"),
                        "gross_margin_pct": st.column_config.NumberColumn("Margin %", format="%.1f%%")
                    }
                )
                
                if st.button("💾 Synchronize COGS Vault", type="primary"):
                    for index, row in edited_cogs.iterrows():
                        orig = cogs_records_df.loc[index]
                        if row['product_name'] != orig['product_name'] or row['target_retail'] != orig['target_retail']:
                            new_retail = float(row['target_retail'])
                            new_cogs = float(orig['total_cogs'])
                            new_margin = ((new_retail - new_cogs) / new_retail * 100) if new_retail > 0 else 0.0
                            
                            supabase.table('cogs_records').update({
                                "product_name": row['product_name'],
                                "target_retail": new_retail,
                                "gross_margin_pct": new_margin
                            }).eq('id', int(orig['id'])).execute()
                    st.success("COGS profiles synced!")
                    st.rerun()
            
            selected_cogs = edited_cogs[edited_cogs['🔍'] == True]
            if not selected_cogs.empty:
                cogs_item = cogs_records_df.loc[selected_cogs.index[0]]
                st.write("##")
                with st.container(border=True):
                    st.markdown(f"#### {cogs_item['product_name']}")
                    st.write(f"**Base Formula:** {cogs_item['formula_name']} ({cogs_item['fill_weight_g']}g fill)")
                    st.write(f"**Primary Packaging:** {cogs_item['primary_packaging']}")
                    
                    with st.expander("System Actions"):
                        del_cogs_pass = st.text_input("Authorization Passcode", type="password", key="dcogsp")
                        if st.button("Erase COGS Profile"):
                            if del_cogs_pass == "lab2026":
                                supabase.table('cogs_records').delete().eq('id', int(cogs_item['id'])).execute()
                                st.rerun()
                            else:
                                st.error("Incorrect passcode.")
        else:
            st.info("No COGS profiles saved in the vault.")

    # --- 7. PRODUCTION LOGS ---
    elif menu == "Production Logs":
        st.title("Production Logs")
        st.markdown("<p style='color: #64748B;'>GMP-compliant traceability records.</p>", unsafe_allow_html=True)
        logs = supabase.table('production_records').select("*").order("created_at", desc=True).execute()
        if logs.data:
            df = pd.DataFrame(logs.data); df['Date'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            with st.container(border=True):
                st.dataframe(df[['Date', 'batch_number', 'lot_number', 'formula_name', 'batch_size_g', 'total_cost']], use_container_width=True, hide_index=True)
        else: st.info("No records found in the vault.")
