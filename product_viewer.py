import streamlit as st
import pandas as pd
import requests
import re 
import time
import ast

# --- Set the page layout to wide. This MUST be the first st command. ---
st.set_page_config(layout="wide")

# Load product details from CSV
@st.cache_data
def load_data():
    return pd.read_csv("combined_data.csv")

df = load_data()


url = f"https://raw.githubusercontent.com/BashirGulistani/product_viewer_rep/main/batches/recommendation_001.json?t={int(time.time())}"

headers = {
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}

response = requests.get(url, headers=headers)
recommended_ids = response.json()


category_names = {
    "Best": "Signature",
    "Better": "Select",
    "Good": "Standard"
}

def render_image_slideshow(images, product_id):
    if not images:
        st.image("https://via.placeholder.com/600x600.png?text=No+Image+Available", use_column_width=True)
        return
    image_tags = ""
    for img in images:
        if isinstance(img, str) and img.startswith("http"):
            # Added object-fit: contain to ensure the whole image is visible
            image_tags += f"<div class='swiper-slide'><img src='{img}' style='width:100%; height:100%; object-fit: contain;'/></div>"

    st.components.v1.html(f"""
    <link rel="stylesheet" href="https://unpkg.com/swiper/swiper-bundle.min.css" />
    <div class="swiper-container" id="swiper-{product_id}" style="height: 100%;">
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
        pagination: {{ el: '.swiper-pagination', clickable: true }},
        navigation: {{ nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' }},
    }});
    </script>
    """, height=550)


def clean_color_names(color_raw):
    if not color_raw:
        return ""

    # Handle stringified list: "['Navy', 'Black']"
    if isinstance(color_raw, str) and color_raw.strip().startswith("["):
        try:
            color_list = ast.literal_eval(color_raw)
        except Exception:
            color_list = [color_raw]  # fallback: treat entire string as one color
    elif isinstance(color_raw, str):
        color_list = [c.strip() for c in color_raw.split(",")]
    else:
        color_list = color_raw  # assume it's already a list

    # Clean parentheses from each color name
    clean_list = [re.sub(r"\s*\(.*?\)", "", color).strip() for color in color_list if color.strip()]
    return ", ".join(clean_list)

def render_product_card(product):
    # --- ENHANCEMENT: Wrap each product card in a container with a border ---
    with st.container(border=True):
        cols = st.columns(2)
        with cols[0]:
            images = [product.get(f'image_url_{i}') for i in range(1, 6)]
            images = [img for img in images if isinstance(img, str) and img.startswith("http")]
            render_image_slideshow(images, product.get("productId", "unknown"))

        with cols[1]:
            st.markdown(f"<h3>{product.get('productName', 'Unnamed Product')}</h3>", unsafe_allow_html=True)
            
            # --- ENHANCEMENT: Use st.metric for a cleaner price display ---
            price = product.get("product_price")
            if pd.notnull(price):
                st.metric(label="As low as", value=f"${price:,.2f}")

            st.divider()

            # --- CHANGE: Display "Description" as bulleted "Features" ---
            if desc := product.get("description"):
                st.markdown("<h5>Features</h5>", unsafe_allow_html=True)
            
                # Split description into sentences for bullet points
                sentences = re.split(r'(?<=[.!?])\s+', desc)
            
                # Start an indented list container
                features_html = '<div style="margin-left: 20px;"><ul style="margin-bottom: 0;">'
            
                for sentence in sentences[:3]:
                    if sentence.strip():  # Avoid empty bullet points
                        features_html += f"<li>{sentence.strip()}</li>"
            
                features_html += "</ul></div>"
            
                st.markdown(features_html, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)  # Add vertical space


            # --- ENHANCEMENT: Group other details under "Specifications" ---
            # The 'if field := ...' syntax already handles hiding missing fields
            spec_html = ""
            
            # Start an outer div for indentation and spacing
            spec_html += '<div style="margin-left: 20px; line-height: 1.8em;">'
            
            if brand := product.get("productBrand"):
                spec_html += f"<div><strong>Brand:</strong> {brand}</div>"
            
            if color := product.get("colorName"):
                cleaned_color = clean_color_names(color)
                spec_html += f"<div><strong>Color:</strong> {cleaned_color}</div>"
            
            if material := product.get("primaryMaterial"):
                spec_html += f"<div><strong>Material:</strong> {material}</div>"
            
            if link := product.get("url_link"):
                spec_html += f'<div><a href="{link}" target="_blank">More Info</a></div>'
            
            spec_html += "</div>"  # Close outer div
            
            if spec_html:
                st.markdown("<h5>Product Specifications</h5>", unsafe_allow_html=True)
                st.markdown(spec_html, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

            # --- CHANGE: Transposed pricing table ---
            pricing_data = []
            
            # Track available tiers: list of (index, quantityMin, price)
            available_tiers = []
            
            # Step 1: Collect available tiers (0–4)
            for i in range(5):
                qty = product.get(f"ProductPrice_{i}_quantityMin")
                price = product.get(f"ProductPrice_{i}_price")
                if pd.notnull(qty) and pd.notnull(price):
                    available_tiers.append((i, int(qty), float(price)))
            
            # Step 2: Identify if tier 4 is present
            tier_4_present = any(t[0] == 4 for t in available_tiers)
            
            # Step 3: Build pricing data
            for idx, (tier_index, qty, price) in enumerate(available_tiers):
                is_last = idx == len(available_tiers) - 1
                if (tier_index == 4) or (not tier_4_present and is_last):
                    qty_str = f"{qty}+"
                else:
                    qty_str = f"{qty}"
                pricing_data.append((qty_str, f"${price:,.2f}"))


            if pricing_data:
                # --- CHANGE: Add currency note and remove "Pricing" header ---
                st.markdown("_Prices displayed in US Dollars (USD)_")
                
                quantities = [item[0] for item in pricing_data]
                prices = [item[1] for item in pricing_data]
                
                qty_cells = "".join([f"<td>{q}</td>" for q in quantities])
                price_cells = "".join([f"<td><strong>{p}</strong></td>" for p in prices])

                html_table = f"""
                <style>
                    .pricing-table {{ width: 100%; border-collapse: collapse; margin-top: 5px; }}
                    .pricing-table th, .pricing-table td {{ padding: 8px 12px; text-align: center; border: 1px solid #ddd; }}
                    .pricing-table th {{ background-color: #f8f9fa; font-weight: bold; text-align: left; width: 100px; }}
                </style>
                <table class="pricing-table">
                    <tr><th>Quantity</th>{qty_cells}</tr>
                    <tr><th>Approximate Price</th>{price_cells}</tr>
                </table>
                """
                st.html(html_table)

def render_section(title, df_section):
    st.markdown(f"<h2 style='border-bottom: 3px solid #007bff; color: #007bff; padding-bottom: 10px; margin-top: 40px; margin-bottom: 20px;'>{title}</h2>", unsafe_allow_html=True)
    for _, row in df_section.iterrows():
        render_product_card(row)

if not any(recommended_ids.values()):
    st.warning("No recommendations found. Please go back to the main app and generate recommendations.")
else:
    st.title("Recommended Products")
    st.markdown("Here are the top product recommendations based on your request, curated into our Signature, Select, and Standard tiers.")
    st.divider()
    
    for level in ["Best", "Better", "Good"]:
        label = category_names[level]
        ids = recommended_ids.get(level, [])
        section_df = df[df["productId"].astype(str).isin(ids)]

        if not section_df.empty:
            section_df = section_df.copy()
            render_section(label, section_df)
