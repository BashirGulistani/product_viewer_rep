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

def render_image_slideshow(images, product_id):
    if not images:
        return
    image_tags = ""
    for img in images:
        if isinstance(img, str) and img.startswith("http"):
            image_tags += f"<div class='swiper-slide'><img src='{img}' style='width:100%; height:auto;'/></div>"

    st.components.v1.html(f"""
    <link rel="stylesheet" href="https://unpkg.com/swiper/swiper-bundle.min.css" />
    <div class="swiper-container" id="swiper-{product_id}">
        <div class="swiper-wrapper">
            {image_tags}
        </div>
        <div class="swiper-pagination"></div>
        <div class="swiper-button-prev"></div>
        <div class="swiper-button-next"></div>
    </div>
    <script src="https://unpkg.com/swiper/swiper-bundle.min.js"></script>
    <script>
    new Swiper('#swiper-{product_id}', {{
        loop: true,
        pagination: {{
            el: '.swiper-pagination',
            clickable: true,
        }},
        navigation: {{
            nextEl: '.swiper-button-next',
            prevEl: '.swiper-button-prev',
        }},
    }});
    </script>
    """, height=420)

def render_product_card(product):
    cols = st.columns([1, 2])
    with cols[0]:
        images = [product.get(f'image_url_{i}') for i in range(1, 6)]
        images = [img for img in images if isinstance(img, str) and img.startswith("http")]
        render_image_slideshow(images, product.get("productId", "unknown"))

    with cols[1]:
        st.markdown(f"<h3 style='font-weight:700'>{product.get('productName', '')}</h3>", unsafe_allow_html=True)

        price = product.get("product_price")
        if pd.notnull(price):
            st.markdown(f"<p style='font-size:16px; color:#444;'>As low as <strong>${price:.2f}</strong></p>", unsafe_allow_html=True)

        if desc := product.get("description"):
            st.markdown(f"**Description:** {desc}")
        if brand := product.get("productBrand"):
            st.markdown(f"**Brand:** {brand}")
        if color := product.get("colorName"):
            st.markdown(f"**Color:** {color}")
        if material := product.get("primaryMaterial"):
            st.markdown(f"**Material:** {material}")

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

def render_section(title, df_section):
    st.markdown(f"<h2 style='border-bottom: 2px solid #ccc; padding-bottom: 4px; margin-top: 40px'>{title}</h2>", unsafe_allow_html=True)
    for _, row in df_section.iterrows():
        render_product_card(row)
        st.markdown("---")

category_names = {
    "Best": "Signature",
    "Better": "Select",
    "Good": "Standard"
}

if not any(recommended_ids.values()):
    st.warning("No recommendations found. Please go back to the main app and generate recommendations.")
else:
    st.title("AI-Powered Product Recommendations")
    for level in ["Best", "Better", "Good"]:
        label = category_names[level]
        ids = recommended_ids.get(level, [])
        section_df = df[df["productId"].astype(str).isin(ids)]

        if not section_df.empty:
            section_df = section_df.copy()
            section_df["category"] = level  # Add category column if needed
            render_section(label, section_df)

