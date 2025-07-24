import streamlit as st
import pandas as pd
import ast

# Load product details from CSV
@st.cache_data
def load_data():
    return pd.read_csv("combined_dataset.csv")

df = load_data()

# Get product IDs from app.py via session_state
import requests

url = "https://raw.githubusercontent.com/BashirGulistani/product_viewer_rep/main/batches/recommendation_001.json"
response = requests.get(url)
recommended_ids = response.json()
st.write("Loaded recommendation IDs:", recommended_ids)


category_names = {
    "Best": "Signature",
    "Better": "Select",
    "Good": "Standard"
}

# Reusable component to render product card
def render_product_card(product):
    with st.container():
        col1, col2 = st.columns([1, 2])

        # Image slideshow on left
        with col1:
            
            images = [
                product.get("image_url_1"),
                product.get("image_url_2"),
                product.get("image_url_3"),
                product.get("image_url_4"),
                product.get("image_url_5"),
            ]
            
            # Filter: keep only non-empty strings
            images = [img for img in images if isinstance(img, str) and img.startswith("http")]

            if images:
                st.image(images, width=180)
            else:
                st.markdown("No image available.")

        # Product info on right
        with col2:
            st.subheader(product.get("productName", "Unnamed Product"))
            st.markdown(f"**Brand:** {product.get('productBrand', 'N/A')}")
            st.markdown(f"**Material:** {product.get('primaryMaterial', 'N/A')}")
            st.markdown(f"**Color:** {product.get('colorName', 'N/A')}")
            link = product.get("url_link")
            if pd.notna(link):
                st.markdown(f"**Link:** [View Product]({link})")
            st.markdown("---")

            # Price tiers
            st.markdown("**Price Tiers:**")
            price_data = {
                "Min Qty": [],
                "Max Qty": [],
                "Price": []
            }
            for i in range(5):
                min_q = product.get(f"ProductPrice_{i}_quantityMin")
                max_q = product.get(f"ProductPrice_{i}_quantityMax")
                price = product.get(f"ProductPrice_{i}_price")
                if pd.notna(price):
                    price_data["Min Qty"].append(min_q)
                    price_data["Max Qty"].append(max_q)
                    price_data["Price"].append(price)
            if price_data["Price"]:
                st.table(pd.DataFrame(price_data))
            else:
                st.markdown("No pricing data available.")

            desc = product.get("description")
            if pd.notna(desc):
                st.markdown(f"**Description:** {desc}")

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
