import streamlit as st
import pandas as pd
import requests
import re
import ast
from streamlit_card import card

# --- Page Configuration (MUST be the first st command) ---
st.set_page_config(layout="wide", page_title="Product Recommendations")

# --- Caching and Data Loading ---

@st.cache_data
def load_data():
    """Loads the product data from the CSV file."""
    return pd.read_csv("final_data.csv")

@st.cache_data
def fetch_product_ids_from_github():
    """Fetches the recommended product IDs from the GitHub JSON file."""
    api_url = "https://api.github.com/repos/BashirGulistani/product_viewer_rep/contents/batches/recommendation_001.json"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    
    if "github" in st.secrets and "token" in st.secrets["github"]:
        headers["Authorization"] = f"Bearer {st.secrets['github']['token']}"

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raises an exception for bad status codes
        data = response.json()
        # Expects JSON like: {"Products": ["id1", "id2", ...]}
        return data.get("Products", [])
    except requests.exceptions.RequestException as e:
        st.error(f"GitHub API error: {e}")
    except ValueError:
        st.error("Failed to parse JSON from GitHub response.")
    return []

# --- Helper Functions ---

def clean_color_names(color_raw):
    """Cleans the color names from various formats for display."""
    if not isinstance(color_raw, str):
        return ""
    try:
        color_list = ast.literal_eval(color_raw)
        if isinstance(color_list, list):
            clean_list = [re.sub(r"\s*\(.*?\)", "", color).strip() for color in color_list]
            return ", ".join(filter(None, clean_list))
    except (ValueError, SyntaxError):
        pass # Fallback for non-list strings
    return color_raw

def render_image_slideshow(images, product_id):
    """Renders a Swiper.js image slideshow for the product details modal."""
    if not images:
        st.image("https://via.placeholder.com/600x600.png?text=No+Image", use_column_width=True)
        return
        
    image_tags = "".join(
        f"<div class='swiper-slide'><img src='{img}' style='width:100%; height:auto; object-fit: contain;'/></div>"
        for img in images if isinstance(img, str) and img.startswith("http")
    )

    st.components.v1.html(f"""
    <link rel="stylesheet" href="https://unpkg.com/swiper/swiper-bundle.min.css"/>
    <div class="swiper-container" id="swiper-{product_id}" style="height: 400px;">
        <div class="swiper-wrapper">{image_tags}</div>
        <div class="swiper-pagination"></div>
        <div class="swiper-button-prev" style="color:#0E3B53;"></div>
        <div class="swiper-button-next" style="color:#0E3B53;"></div>
    </div>
    <script src="https://unpkg.com/swiper/swiper-bundle.min.js"></script>
    <script>
    new Swiper('#swiper-{product_id}', {{
        loop: true,
        pagination: {{ el: '.swiper-pagination', clickable: true }},
        navigation: {{ nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' }},
    }});
    </script>
    """, height=410)

def render_product_details_modal(product):
    """Renders the full product details inside the st.dialog modal."""
    # Main details section
    st.subheader(product.get("productName", "Unnamed Product"))
    
    # Image Slideshow
    images = [product.get(f'image_url_{i}') for i in range(1, 6)]
    images = [img for img in images if isinstance(img, str) and img.startswith("http")]
    render_image_slideshow(images, product.get("productId"))

    st.divider()

    # Features and Specifications in columns
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Features")
        if desc := product.get("description"):
            for sentence in re.split(r'(?<=[.!?])\s+', desc):
                if sentence.strip():
                    st.markdown(f"- {sentence.strip()}")
        else:
            st.markdown("- No features listed.")
    
    with col2:
        st.markdown("##### Specifications")
        if brand := product.get("productBrand"):
            st.markdown(f"**Brand:** {brand}")
        if material := product.get("primaryMaterial"):
            st.markdown(f"**Material:** {material}")
        if color := product.get("colorName"):
            st.markdown(f"**Colors:** {clean_color_names(color)}")
        if link := product.get("url_link"):
            st.link_button("View on Supplier Website", link)

    st.divider()

    # Pricing Table
    pricing_data = []
    for i in range(5):
        qty = product.get(f"ProductPrice_{i}_quantityMin")
        price = product.get(f"ProductPrice_{i}_price")
        if pd.notnull(qty) and pd.notnull(price):
            pricing_data.append({"Quantity": int(qty), "Price per item (USD)": f"${price:,.2f}"})
    
    if pricing_data:
        st.markdown("##### Tiered Pricing")
        st.dataframe(pd.DataFrame(pricing_data), use_container_width=True, hide_index=True)


# --- Main App ---

# Display fixed header with logo
logo_url = "https://raw.githubusercontent.com/BashirGulistani/product_viewer_rep/main/idYu324uEk_logos.png"
st.markdown(f'<div style="background-color:#0E3B53; padding:1em; text-align:center;"><img src="{logo_url}" height="60"></div>', unsafe_allow_html=True)
st.title("Your Recommended Products")
st.markdown("Here are the product recommendations based on your request. **Click on any product card to see more details.**")
st.divider()

# Load data and filter based on fetched IDs
df = load_data()
product_ids = fetch_product_ids_from_github()

if not product_ids:
    st.warning("Could not find any recommended products. Please generate a new list from the main app.")
else:
    # Ensure IDs are strings for comparison
    product_ids_str = [str(pid) for pid in product_ids]
    products_df = df[df["productId"].astype(str).isin(product_ids_str)].copy()
    
    if products_df.empty:
        st.error("Product details for the recommended IDs could not be found in the data file.")
    else:
        # Create a grid with 3 columns
        cols = st.columns(3)
        
        # Loop through products and display a summary card in each column
        for index, product in products_df.iterrows():
            with cols[index % 3]:
                # Prepare content for the summary card
                card_title = product.get("productName", "No Name")
                card_image = product.get("image_url_1", "https://via.placeholder.com/600")
                price_val = product.get("product_price")
                price_text = f"${price_val:,.2f}" if pd.notnull(price_val) else "N/A"
                colors = clean_color_names(product.get("colorName", ""))
                
                # Use streamlit-card, which returns True when clicked
                is_clicked = card(
                    title=card_title,
                    text=[f"Colors: {colors}", f"As low as: {price_text}"],
                    image=card_image,
                    styles={
                        "card": {"width": "100%", "height": "400px", "margin-bottom": "20px"},
                        "text": {"font-family": "sans-serif"}
                    }
                )
                
                # If the card is clicked, open the modal dialog
                if is_clicked:
                    with st.dialog(f"Details for {card_title}", expanded=True):
                        render_product_details_modal(product)
