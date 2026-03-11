import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Eve Catalog", page_icon="🛍️", layout="wide")


@st.cache_data
def load_data(csv_path: str = "products.csv") -> pd.DataFrame:
    """Load raw pricing data from CSV."""
    return pd.read_csv(csv_path)


def build_brand_catalog(df: pd.DataFrame) -> dict:
    """
    Transform the attribute-style CSV into a nested structure focused on lengths:
    {
        brand: {
            "lengths": {value: price},
        },
        ...
    }
    """
    catalog: dict[str, dict] = {}

    # Normalize key columns
    df = df.copy()
    df["Brand"] = df["Brand"].astype(str)
    df["Attribute_Type"] = df["Attribute_Type"].astype(str).str.strip().str.lower()
    df["Value"] = df["Value"].astype(str).str.strip()
    if "Parent_Value" in df.columns:
        df["Parent_Value"] = df["Parent_Value"].fillna("").astype(str).str.strip()

    for brand, group in df.groupby("Brand"):
        length_rows = group[group["Attribute_Type"] == "length"]

        lengths = (
            length_rows.set_index("Value")["Price_Adjustment"].astype(float).to_dict()
            if not length_rows.empty
            else {}
        )

        catalog[brand] = {
            "lengths": lengths,
        }

    return catalog


def compute_unit_price(length_price: float, color_price: float) -> float:
    """Final price is the sum of the selected length and color prices."""
    return float(length_price) + float(color_price)


# ---- Initialize data ----
df = load_data()
brand_catalog = build_brand_catalog(df)
all_brands = sorted(brand_catalog.keys())

# ---- Initialize session state ----
if "cart" not in st.session_state or not isinstance(st.session_state.cart, dict):
    st.session_state.cart = {}

if "global_discount" not in st.session_state:
    st.session_state.global_discount = 0.0

if "order_notes" not in st.session_state:
    st.session_state.order_notes = ""

st.title("🛍️ Eve Catalog - Sales Order Configurator")

# ---- Main Configurator Area ----
st.subheader("Configure Your SKU")

# Search/filter by brand
search_query = st.text_input("Search by Brand", "").lower().strip()

if search_query:
    filtered_brands = [b for b in all_brands if search_query in b.lower()]
else:
    filtered_brands = all_brands

if not filtered_brands:
    st.warning("No brands found matching that search.")
else:
    selected_brand = st.selectbox("Select Brand", filtered_brands)

    if selected_brand:
        brand_cfg = brand_catalog[selected_brand]

        length_options = sorted(brand_cfg["lengths"].keys(), key=str)

        if not length_options:
            st.error("This brand does not have any Length configuration in the data.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                selected_length = st.selectbox("Length", length_options)

            # Filter colors based on Parent_Value mapping for the selected length
            brand_rows = df[df["Brand"].astype(str) == selected_brand].copy()
            brand_rows["Attribute_Type"] = (
                brand_rows["Attribute_Type"].astype(str).str.strip().str.lower()
            )
            brand_rows["Value"] = brand_rows["Value"].astype(str).str.strip()
            color_rows = brand_rows[brand_rows["Attribute_Type"] == "color"]

            # Clean Parent_Value and apply flexible matching rules
            if "Parent_Value" in color_rows.columns:
                parent_clean = color_rows["Parent_Value"].fillna("").astype(str).str.strip()
            else:
                parent_clean = pd.Series([""] * len(color_rows), index=color_rows.index)

            selected_length_str = str(selected_length)
            # Colors with empty Parent_Value apply to all lengths;
            # otherwise use a "contains" check to match entries like "18, 22"
            mask_all_lengths = parent_clean == ""
            mask_match_length = parent_clean.str.contains(selected_length_str)
            valid_colors = color_rows[mask_all_lengths | mask_match_length]
            colors_for_length = (
                valid_colors.set_index("Value")["Price_Adjustment"].astype(float).to_dict()
                if not valid_colors.empty
                else {}
            )
            color_options = sorted(colors_for_length.keys(), key=str)

            if not color_options:
                st.error(
                    "No Color options are configured for this Length/Brand combination "
                    "(check the Parent_Value mapping in the CSV)."
                )
            else:
                with col2:
                    selected_color = st.selectbox("Color", color_options)

                length_price = float(brand_cfg["lengths"].get(str(selected_length), 0.0))
                color_price = float(colors_for_length.get(str(selected_color), 0.0))
                unit_price = compute_unit_price(length_price, color_price)

                st.markdown(
                    f"**Configured Price: ${unit_price:,.2f} per unit** "
                    f"(Length: ${length_price:,.2f} + Color: ${color_price:,.2f})"
                )

                col3, col4 = st.columns(2)
                with col3:
                    line_discount = st.number_input(
                        "Line-Item Discount (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=0.0,
                        step=1.0,
                    )
                with col4:
                    qty = st.number_input(
                        "Quantity",
                        min_value=1,
                        max_value=1000,
                        value=1,
                        step=1,
                    )

                discounted_unit_price = unit_price * (1 - line_discount / 100.0)
                st.markdown(
                    f"Price after line discount: **${discounted_unit_price:,.2f} per unit** "
                    f"({qty} units = ${discounted_unit_price * qty:,.2f})"
                )

                sku = f"{selected_brand}-{selected_length}-{selected_color}"
                if st.button("Add to Cart"):
                    existing = st.session_state.cart.get(
                        sku,
                        {
                            "qty": 0,
                            "original_price": unit_price,
                            "discount_percent": line_discount,
                        },
                    )

                    new_qty = existing["qty"] + qty
                    st.session_state.cart[sku] = {
                        "qty": new_qty,
                        "original_price": unit_price,
                        "discount_percent": line_discount,
                    }
                    st.toast(f"Added {qty}x {sku} to cart.")


# ---- Sidebar: Cart, Discounts, Fees, Notes ----
with st.sidebar:
    st.header("🛒 Your Cart")

    cart = st.session_state.cart
    subtotal_before_global = 0.0

    if not cart:
        st.write("Cart is empty.")
    else:
        for sku, item in list(cart.items()):
            qty = int(item.get("qty", 0))
            original_price = float(item.get("original_price", 0.0))
            discount_percent = float(item.get("discount_percent", 0.0))

            if qty <= 0:
                continue

            line_price_after_discount = qty * original_price * (1 - discount_percent / 100.0)
            subtotal_before_global += line_price_after_discount

            col_a, col_b = st.columns([4, 1])
            col_a.write(
                f"**{qty}x** {sku} @ ${original_price:,.2f} "
                f"(-{discount_percent:.0f}%): ${line_price_after_discount:,.2f}"
            )
            if col_b.button("❌", key=f"remove_{sku}"):
                del st.session_state.cart[sku]
                st.rerun()

        st.divider()

        # Order Notes
        st.subheader("Order Notes")
        st.session_state.order_notes = st.text_area(
            "Notes",
            value=st.session_state.order_notes,
            placeholder="Special instructions, PO number, delivery details...",
        )

        st.divider()

        # Global Discount
        st.subheader("Global Discount")
        st.session_state.global_discount = st.number_input(
            "Global Discount (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(st.session_state.global_discount),
            step=1.0,
        )

        global_discount = float(st.session_state.global_discount)
        discount_amount = subtotal_before_global * (global_discount / 100.0)
        subtotal_after_global = subtotal_before_global - discount_amount

        # Handling Fee: $5 for every $1000 of the post-discount subtotal
        handling_fee = math.ceil(subtotal_after_global / 1000.0) * 5 if subtotal_after_global > 0 else 0.0
        grand_total = subtotal_after_global + handling_fee

        st.write(f"Line-item discounted subtotal: ${subtotal_before_global:,.2f}")
        st.write(f"Global discount: -${discount_amount:,.2f} ({global_discount:.0f}%)")
        st.write(f"Post-discount subtotal: **${subtotal_after_global:,.2f}**")
        st.write(f"Handling Fee ($5 per $1k): **${handling_fee:,.2f}**")
        st.header(f"Total: ${grand_total:,.2f}")

        col_left, col_right = st.columns(2)
        if col_left.button("Clear All"):
            st.session_state.cart = {}
            st.session_state.order_notes = ""
            st.rerun()

        if col_right.button("✅ Checkout"):
            st.balloons()
            st.success("Order Processed!")
            st.info(
                f"Finalizing order for ${grand_total:,.2f}.\n\n"
                f"Order Notes:\n{st.session_state.order_notes or '(none)'}"
            )