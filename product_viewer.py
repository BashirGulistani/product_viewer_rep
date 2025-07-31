import streamlit as st
import pandas as pd
import requests
import re
import ast

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
        response.raise_for_status()
        data = response.json()
        return data.get("Products", [])
    except requests.exceptions.RequestException as e:
        st.error(f"GitHub API error: {e}")
    except ValueError:
        st.error("Failed to parse JSON from GitHub response.")
    return []

# --- Helper Functions ---

def render_color_swatches(hex_list_str):
    """Generates and renders HTML for small color swatches."""
    swatches_html = ""
    if not isinstance(hex_list_str, str):
        return
    try:
        hex_codes = ast.literal_eval(hex_list_str)
        if isinstance(hex_codes, list):
            for color in hex_codes:
                color_parts = re.split(r'[-/]', color)
                for part in color_parts:
                    clean_part = part.strip()
                    if clean_part.startswith('#'):
                        swatches_html += f'<div style="width:22px; height:22px; background-color:{clean_part}; border-radius:50%; display:inline-block; margin:0 4px 4px 0; border:1px solid #eee;"></div>'
    except (ValueError, SyntaxError):
        pass
    st.markdown(f'<div style="height: 30px;">{swatches_html}</div>', unsafe_allow_html=True)


def render_image_slideshow(images, product_id):
    """Renders a Swiper.js image slideshow."""
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

# --- Dialog Function (using the decorator pattern) ---

st.markdown(
    """
<style>
div[data-testid="stDialog"] div[role="dialog"]:has(.big-dialog) {
    width: 80vw;
    height: 80vh;
}
</style>
""",
    unsafe_allow_html=True,
)


@st.dialog("Product Details")
def show_product_dialog(product):
    """Renders the full product details inside the dialog."""
    st.subheader(product.get("productName", "Unnamed Product"))
    images = [product.get(f'image_url_{i}') for i in range(1, 6)]
    images = [img for img in images if isinstance(img, str) and img.startswith("http")]
    render_image_slideshow(images, product.get("productId"))

    st.divider()
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
        if link := product.get("url_link"):
            st.link_button("View on Supplier Website", link)

    st.divider()
    pricing_data = []
    for i in range(5):
        if pd.notnull(product.get(f"ProductPrice_{i}_quantityMin")) and pd.notnull(product.get(f"ProductPrice_{i}_price")):
            pricing_data.append({"Quantity": int(product[f"ProductPrice_{i}_quantityMin"]), "Price per item (USD)": f"${product[f'ProductPrice_{i}_price']:.2f}"})
    if pricing_data:
        st.markdown("##### Tiered Pricing")
        st.dataframe(pd.DataFrame(pricing_data), use_container_width=True, hide_index=True)
    st.html("<span class='big-dialog'></span>")

# --- Main App ---
logo_url = "https://raw.githubusercontent.com/BashirGulistani/product_viewer_rep/main/idYu324uEk_logos.png"
st.markdown(f'<div style="background-color:#0E3B53; padding:1em; text-align:center;"><img src="{logo_url}" height="60"></div>', unsafe_allow_html=True)
st.title("Your Recommended Products")
st.markdown("Here are the product recommendations based on your request. Click **'View Details'** on any product card to learn more.")
st.divider()

df = load_data()
product_ids = fetch_product_ids_from_github()

if not product_ids:
    st.warning("Could not find any recommended products. Please generate a new list from the main app.")
else:
    product_ids_str = [str(pid) for pid in product_ids]
    products_df = df[df["productId"].astype(str).isin(product_ids_str)].copy()

    if products_df.empty:
        st.error("Product details for the recommended IDs could not be found in the data file.")
    else:
        cols = st.columns(3)
        for index, product in products_df.iterrows():
            with cols[index % 3]:
                with st.container(border=True):
                    image_url = product.get("image_url_1")
                    if isinstance(image_url, str) and image_url.startswith("http"):
                        st.image(image_url)
                    else:
                        st.image("https://via.placeholder.com/600x400.png?text=Image+Not+Available")

                    st.markdown(f"**{product.get('productName', 'No Name')}**")
                    render_color_swatches(product.get('hexColor'))
                    st.caption(f"Item #{product.get('productId')}")
                    
                    price = product.get("product_price")
                    price_text = f"As low as **${price:,.2f}**" if pd.notnull(price) else ""
                    st.markdown(price_text)
                    
                    st.write("") # Spacer
                    
                    # Button now calls the decorated dialog function
                    if st.button("View Details", key=f"view_{product.get('productId')}", use_container_width=True):
                        show_product_dialog(product)
