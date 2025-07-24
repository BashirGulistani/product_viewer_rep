import streamlit as st
import pandas as pd
import ast

# Load product details from CSV
@st.cache_data
def load_data():
    return pd.read_csv("combined_data.csv")

df = load_data()

# Get product IDs from app.py via session_state
import requests

url = "https://raw.githubusercontent.com/BashirGulistani/product_viewer_rep/main/batches/recommendation_001.json"
response = requests.get(url)
recommended_ids = response.json()


category_names = {
    "Best": "Signature",
    "Better": "Select",
    "Good": "Standard"
}

# Reusable component to render product card
def render_product_card(product):
    st.markdown(f"<h3 style='font-weight:700'>{product.get('productName', '')}</h3>", unsafe_allow_html=True)

    price = product.get("product_price")
    if pd.notnull(price):
        st.markdown(f"<p style='font-size:16px; color:gray'><strong>As low as ${price:.2f}</strong></p>", unsafe_allow_html=True)

    # Image slideshow (carousel-like using st.image)
    images = [
        product.get("image_url_1"),
        product.get("image_url_2"),
        product.get("image_url_3"),
        product.get("image_url_4"),
        product.get("image_url_5")
    ]
    images = [img for img in images if isinstance(img, str) and img.startswith("http")]
    if images:
        st.image(images, width=600, caption=product.get("productName", "Product"))

    # Optional fields
    with st.expander("Product Details"):
        if desc := product.get("description"):
            st.markdown(f"**Description:** {desc}")
        if brand := product.get("productBrand"):
            st.markdown(f"**Brand:** {brand}")
        if color := product.get("colorName"):
            st.markdown(f"**Color:** {color}")
        if material := product.get("primaryMaterial"):
            st.markdown(f"**Material:** {material}")

    # Quantity and Price Table
    pricing = []
    for i in range(5):
        qty = product.get(f"ProductPrice_{i}_quantityMin")
        price = product.get(f"ProductPrice_{i}_price")
        if pd.notnull(qty) and pd.notnull(price):
            qty_str = f"{int(qty)}+" if i == 4 else f"{int(qty)}"
            pricing.append((qty_str, f"${price:.2f}"))

    if pricing:
        st.markdown("#### **Pricing**")
        table_md = "| Quantity | Price |\n|----------|-------|\n"
        for qty, p in pricing:
            table_md += f"| {qty} | {p} |\n"
        st.markdown(table_md)

# Render sections
st.title("🎯 AI-Powered Product Recommendations")

if not any(recommended_ids.values()):
    st.warning("No recommendations found. Please go back to the main app and generate recommendations.")
else:
    for level in ["Best", "Better", "Good"]:
        label = category_names[level]
        ids = recommended_ids.get(level, [])
        section_df = df[df["productId"].astype(str).isin(ids)]

        if not section_df.empty:
            st.header(f"{label} Collection")
            for _, row in section_df.iterrows():
                render_product_card(row)
            st.markdown("---")
