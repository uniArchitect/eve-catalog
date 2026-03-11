import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Eve Catalog", page_icon="🛍️", layout="wide")


@st.cache_data
def load_data(csv_path: str = "products.csv") -> pd.DataFrame:
    """Load raw pricing data from CSV."""
    df = pd.read_csv(csv_path)
    df = df.copy()

    # Normalize expected columns for combo pricing with Brand/Series naming
    df["Brand_Name"] = df["Brand_Name"].astype(str).str.strip()
    df["Series"] = df["Series"].astype(str).str.strip()
    df["Length"] = df["Length"].astype(str).str.strip()
    df["Color"] = df["Color"].astype(str).str.strip()
    if "Description" in df.columns:
        df["Description"] = df["Description"].fillna("").astype(str).str.strip()
    else:
        df["Description"] = ""

    if "Price" not in df.columns:
        raise ValueError("CSV must contain a 'Price' column.")
    df["Price"] = df["Price"].astype(float)

    return df


def build_brand_catalog(df: pd.DataFrame) -> dict:
    """
    Transform the combo-style CSV into a nested structure:
    {
        brand_name: {
            "series": {
                series: {
                    "lengths": [length1, length2, ...],
                    "colors_by_length": {
                        length1: [color_a, color_b, ...],
                        ...
                    },
                    "price_table": {
                        (length, color): price,
                        ...
                    },
                },
                ...
            },
        },
        ...
    }
    """
    catalog: dict[str, dict] = {}

    for brand_name, brand_group in df.groupby("Brand_Name"):
        series_dict: dict[str, dict] = {}

        for series, series_group in brand_group.groupby("Series"):
            lengths = sorted(series_group["Length"].unique(), key=str)

            colors_by_length: dict[str, set[str]] = {}
            price_table: dict[tuple[str, str], float] = {}
            description_table: dict[tuple[str, str], str] = {}

            for _, row in series_group.iterrows():
                length = str(row["Length"])
                color = str(row["Color"])
                price = float(row["Price"])
                description = str(row.get("Description", ""))

                colors_by_length.setdefault(length, set()).add(color)
                price_table[(length, color)] = price
                description_table[(length, color)] = description

            colors_by_length_lists = {
                length: sorted(list(colors), key=str) for length, colors in colors_by_length.items()
            }

            series_dict[series] = {
                "lengths": lengths,
                "colors_by_length": colors_by_length_lists,
                "price_table": price_table,
                "description_table": description_table,
            }

        catalog[brand_name] = {
            "series": series_dict,
        }

    return catalog


def compute_unit_price(series_cfg: dict, length: str, color: str) -> float:
    """Look up the price directly from the Series+Length+Color combo table."""
    key = (str(length), str(color))
    price_table = series_cfg.get("price_table", {})
    if key not in price_table:
        raise KeyError(f"No price configured for combination: {key}")
    return float(price_table[key])


# ---- Initialize data ----
df = load_data()
brand_catalog = build_brand_catalog(df)
all_brand_names = sorted(brand_catalog.keys())

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

# Search/filter by Brand_Name
search_query = st.text_input("Search by Brand Name", "").lower().strip()

if search_query:
    filtered_brands = [b for b in all_brand_names if search_query in b.lower()]
else:
    filtered_brands = all_brand_names

if not filtered_brands:
    st.warning("No brands found matching that search.")
else:
    selected_brand_name = st.selectbox("Select Brand", filtered_brands)

    if selected_brand_name:
        brand_cfg = brand_catalog[selected_brand_name]
        series_dict = brand_cfg.get("series", {})
        series_options = sorted(series_dict.keys())

        if not series_options:
            st.error("This brand does not have any Series configuration in the data.")
        else:
            selected_series = st.selectbox("Series", series_options)

            if selected_series:
                series_cfg = series_dict[selected_series]

                # Lengths available for the selected Brand_Name + Series
                length_options = series_cfg["lengths"]

                if not length_options:
                    st.error("This series does not have any Length configuration in the data.")
                else:
                    # Display Brand_Name and Series clearly
                    st.markdown(f"**Brand:** {selected_brand_name}  •  **Series:** {selected_series}")

                    col1, col2 = st.columns(2)
                    with col1:
                        selected_length = st.selectbox("Length", length_options)

                    # Colors available for the selected Brand_Name + Series + Length
                    colors_for_length = series_cfg["colors_by_length"].get(str(selected_length), [])
                    color_options = colors_for_length

                    if not color_options:
                        st.error(
                            "No Color options are configured for this Brand/Series/Length combination "
                            "(missing Series+Length+Color row in the CSV)."
                        )
                    else:
                        with col2:
                            selected_color = st.selectbox("Color", color_options)

                        try:
                            unit_price = compute_unit_price(series_cfg, selected_length, selected_color)
                            description = series_cfg.get("description_table", {}).get(
                                (str(selected_length), str(selected_color)), ""
                            )
                        except KeyError:
                            st.error(
                                "No price configured for this Brand/Series/Length/Color combination. "
                                "Please check the CSV."
                            )
                            unit_price = 0.0
                            description = ""

                        if unit_price > 0:
                            # SKU built from Series-Length-Color
                            sku = f"{selected_series}-{selected_length}-{selected_color}"

                            st.markdown(
                                f"**SKU:** `{sku}`  •  **Price:** ${unit_price:,.2f} per unit"
                            )
                            if description:
                                st.caption(description)

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

                            if st.button("Add to Cart"):
                                existing = st.session_state.cart.get(
                                    sku,
                                    {
                                        "qty": 0,
                                        "original_price": unit_price,
                                        "discount_percent": line_discount,
                                        "description": description,
                                    },
                                )

                                new_qty = existing["qty"] + qty
                                st.session_state.cart[sku] = {
                                    "qty": new_qty,
                                    "original_price": unit_price,
                                    "discount_percent": line_discount,
                                    "description": description or existing.get("description", ""),
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
            description = item.get("description", "")

            if qty <= 0:
                continue

            line_price_after_discount = qty * original_price * (1 - discount_percent / 100.0)
            subtotal_before_global += line_price_after_discount

            col_a, col_b = st.columns([4, 1])
            col_a.write(
                f"**{qty}x** {sku} @ ${original_price:,.2f} "
                f"(-{discount_percent:.0f}%): ${line_price_after_discount:,.2f}"
            )
            if description:
                col_a.caption(description)
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