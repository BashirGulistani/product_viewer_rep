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

def render_product_card(product: Dict[str, Any]):
    st.markdown("---")
    images = [
        product.get("image_url_1"),
        product.get("image_url_2"),
        product.get("image_url_3"),
        product.get("image_url_4"),
        product.get("image_url_5")
    ]
    images = [img for img in images if isinstance(img, str) and img.startswith("http")]

    image_key = f"image_index_{product['productId']}"
    if image_key not in st.session_state:
        st.session_state[image_key] = 0

    left_col, right_col = st.columns([1.2, 2])

    with left_col:
        if images:
            current_index = st.session_state[image_key]
            st.image(images[current_index], width=400)
            btn1, btn2, _ = st.columns([1, 1, 2])
            with btn1:
                if st.button("◀", key=f"prev_{product['productId']}"):
                    st.session_state[image_key] = max(0, current_index - 1)
            with btn2:
                if st.button("▶", key=f"next_{product['productId']}"):
                    st.session_state[image_key] = min(len(images) - 1, current_index + 1)

    with right_col:
        st.markdown(f"### **{product.get('productName', 'Unnamed Product')}**")

        price = product.get("product_price")
        if pd.notna(price):
            st.markdown(f"#### 💲 As low as: **${price:.2f}**")

        brand = product.get("productBrand")
        material = product.get("primaryMaterial")
        color = product.get("colorName")

        if brand:
            st.markdown(f"**Brand:** {brand}")
        if material:
            st.markdown(f"**Material:** {material}")
        if color:
            st.markdown(f"**Available Colors:** {color}")

        description = product.get("description")
        if description:
            st.markdown(f"**Description:** {description}")

        price_data = []
        for i in range(5):
            qty_min = product.get(f"ProductPrice_{i}_quantityMin")
            price = product.get(f"ProductPrice_{i}_price")
            if pd.notna(qty_min) and pd.notna(price):
                label = f"{int(qty_min)}+" if i == 4 else str(int(qty_min))
                price_data.append((label, f"${price:.2f}"))

        if price_data:
            st.markdown("#### 📦 Price Tiers")
            price_df = pd.DataFrame(price_data, columns=["Quantity", "Price"])
            st.table(price_df)

        if url := product.get("url_link"):
            st.markdown(f"[🔗 View Product]({url})")

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

