import streamlit as st
import pandas as pd

st.set_page_config(page_title="Eve Catalog", page_icon="🛍️", layout="wide")

# 1. Load Data
@st.cache_data
def load_data():
    return pd.read_csv('products.csv')

df = load_data()
inventory = dict(zip(df['product'], df['price']))

# 2. Initialize Cart
if 'cart' not in st.session_state:
    st.session_state.cart = {} # Using a dict now: { "item": quantity }

st.title("🛍️ Eve Catalog")

# 3. The Grid Layout (3 Columns)
cols = st.columns(3)
for i, (item, price) in enumerate(inventory.items()):
    col = cols[i % 3] # Cycles through columns
    with col.container(border=True):
        st.subheader(item.title())
        st.write(f"Price: **${price:.2f}**")
        
        # Quantity selector + Add button
        qty = st.number_input(f"Qty for {item}", min_value=1, max_value=10, key=f"qty_{item}")
        if st.button(f"Add {item.title()}", key=f"btn_{item}"):
            st.session_state.cart[item] = st.session_state.cart.get(item, 0) + qty
            st.toast(f"Added {qty}x {item} to cart!")

# 4. Sidebar: The Shopping Cart
with st.sidebar:
    st.header("🛒 Your Cart")
    
    if not st.session_state.cart:
        st.write("Cart is empty.")
    else:
        grand_total = 0
        for item, qty in list(st.session_state.cart.items()):
            if qty > 0:
                price = inventory[item]
                subtotal = price * qty
                grand_total += subtotal
                
                # Show item info + Remove button
                col_a, col_b = st.columns([3, 1])
                col_a.write(f"**{qty}x** {item.title()} (${subtotal:.2f})")
                if col_b.button("❌", key=f"remove_{item}"):
                    del st.session_state.cart[item]
                    st.rerun()

        st.divider()
        st.subheader(f"Total: ${grand_total:.2f}")
        
        if st.button("Clear All"):
            st.session_state.cart = {}
            st.rerun()
            
        if st.button("✅ Checkout"):
            st.balloons()
            st.success(f"Final Total: ${grand_total:.2f}. Receipt generated!")