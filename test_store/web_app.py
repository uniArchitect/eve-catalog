import streamlit as st
import pandas as pd

# 1. Setup Page
st.set_page_config(page_title="Eve Catalog", page_icon="🛍️")
st.title("🛍️ Eve Catalog")

# 2. Load Data
df = pd.read_csv("products.csv")

# 3. Sidebar Cart (Session State keeps the cart saved while you click)
if 'cart' not in st.session_state:
    st.session_state.cart = []

st.sidebar.header("Your Cart")
if not st.session_state.cart:
    st.sidebar.write("Cart is empty.")
else:
    for item in st.session_state.cart:
        st.sidebar.write(f"- {item['name']}: ${item['price']}")
    
    total = sum(item['price'] for item in st.session_state.cart)
    st.sidebar.divider()
    st.sidebar.subheader(f"Total: ${total:.2f}")
    if st.sidebar.button("Clear Cart"):
        st.session_state.cart = []
        st.rerun()

# 4. Main Catalog Display
st.subheader("Available Products")
cols = st.columns(3) # Creates a grid

for index, row in df.iterrows():
    with cols[index % 3]:
        st.write(f"**{row['name']}**")
        st.write(f"${row['price']}")
        if st.button(f"Add to Cart", key=row['id']):
            st.session_state.cart.append({'name': row['name'], 'price': row['price']})
            st.toast(f"Added {row['name']}!")
            st.rerun()
