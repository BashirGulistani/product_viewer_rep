import streamlit as st
import pandas as pd
import requests
import re
import ast
from urllib.parse import quote

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
    """Generates and renders HTML for small, centered color swatches with tooltips."""
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
                        # Get color name for the tooltip
                        color_name = get_color_name(clean_part)
                        # Add the 'title' attribute for the hover effect
                        swatches_html += f'<div title="{color_name}" style="width:22px; height:22px; background-color:{clean_part}; border-radius:50%; display:inline-block; margin:0 4px 4px 0; border:1px solid #eee;"></div>'
    except (ValueError, SyntaxError):
        pass
    st.markdown(f'<div style="height: 30px; text-align: center;">{swatches_html}</div>', unsafe_allow_html=True)

######

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Functions for managing favorites ---

def add_to_favorites(product_id):
    """Adds a product ID to the favorites list in session state."""
    if product_id not in st.session_state.favorites:
        st.session_state.favorites.append(product_id)

def remove_from_favorites(product_id):
    """Removes a product ID from the favorites list."""
    if product_id in st.session_state.favorites:
        st.session_state.favorites.remove(product_id)


######


def clean_product_name(name_str):
    """
    Cleans product names by removing characters that are not standard letters,
    numbers, or common punctuation.
    """
    if not isinstance(name_str, str):
        return "Unnamed Product"
    
    # This regular expression finds any character that is NOT a letter (a-z, A-Z),
    # a number (0-9), a space, or one of the common symbols in the set: - & / ' , .
    # It replaces them with an empty string.
    allowed_chars_pattern = r"[^a-zA-Z0-9\s\-&/',.]"
    cleaned_name = re.sub(allowed_chars_pattern, '', name_str)
    
    # Replace multiple spaces with a single space for cleanliness
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name)
    
    return cleaned_name.strip()

def find_first_available_image(product):
    """Iterates through image_url_1 to 5 and returns the first valid URL."""
    for i in range(1, 6):
        image_url = product.get(f"image_url_{i}")
        if isinstance(image_url, str) and image_url.startswith("http"):
            return image_url
    # Return None if no valid image is found
    return None


import webcolors
import math


def get_color_name(hex_code):
    """
    Finds the nearest CSS3 color name for a given hex code.
    This version incorporates the optimization of comparing squared Euclidean distances.
    """
    try:
        # First, try for an exact match, which is most efficient.
        return webcolors.hex_to_name(hex_code).title()
    except ValueError:
        try:
            # If no exact match, convert the input hex to an RGB tuple.
            requested_rgb = webcolors.hex_to_rgb(hex_code)
        except ValueError:
            # Handle cases where the hex code is invalid.
            return "Unknown Color"

        min_distance_sq = float('inf')
        closest_name = "Unknown Color"

        # Loop through all known CSS3 colors to find the closest one.
        for name in webcolors.names("css3"):
            current_rgb = webcolors.name_to_rgb(name)
            
            # Calculate the squared Euclidean distance (more efficient).
            dist_sq = sum([(a - b) ** 2 for a, b in zip(requested_rgb, current_rgb)])

            # If this color is closer than the closest one found so far, update.
            if dist_sq < min_distance_sq:
                min_distance_sq = dist_sq
                closest_name = name
        
        return closest_name.title()

def render_image_slideshow(images, product_id):
    """Renders a Swiper.js image slideshow with responsive images."""
    
    # Filter for valid image URLs, effectively ignoring NA/null values
    valid_images = [
        img for img in images 
        if isinstance(img, str) and img.startswith("http")
    ]

    if not valid_images:
        st.image("https://via.placeholder.com/600x400.png?text=Image+Not+Available", use_column_width=True)
        return

    # Create image tags with improved CSS for responsive sizing
    image_tags = "".join(
        f"""
        <div class='swiper-slide' style='display: flex; align-items: center; justify-content: center;'>
            <img src='{img}' 
                 style='max-width: 100%; max-height: 380px; display: block; object-fit: contain;'/>
        </div>
        """
        for img in valid_images
    )

    # Set container height to accommodate the max image height and controls
    container_height = 410

    st.components.v1.html(f"""
    <link rel="stylesheet" href="https://unpkg.com/swiper/swiper-bundle.min.css"/>
    <div class="swiper-container" id="swiper-{product_id}" style="height: {container_height}px;">
        <div class="swiper-wrapper">{image_tags}</div>
        <div class="swiper-pagination"></div>
        <div class="swiper-button-prev" style="color:#0E3B53;"></div>
        <div class="swiper-button-next" style="color:#0E3B53;"></div>
    </div>
    <script src="https://unpkg.com/swiper/swiper-bundle.min.js"></script>
    <script>
    new Swiper('#swiper-{product_id}', {{
        loop: {str(len(valid_images) > 1).lower()}, // Disable loop if only one image
        pagination: {{ el: '.swiper-pagination', clickable: true }},
        navigation: {{ nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' }},
    }});
    </script>
    """, height=container_height)

# --- Dialog Function (using the decorator pattern) ---

st.markdown(
    """
<style>
div[data-testid="stDialog"] div[role="dialog"]:has(.big-dialog) {
    width: 80vw;
}
</style>
""",
    unsafe_allow_html=True,
)


@st.dialog("Product Details")
def show_product_dialog(product):
    """Renders the full product details inside the dialog."""
    
    cleaned_title = clean_product_name(product.get("productName", "Unnamed Product"))
    st.subheader(cleaned_title)

    images = [product.get(f'image_url_{i}') for i in range(1, 6)]
    render_image_slideshow(images, product.get("productId"))

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Features")
        if desc := product.get("description"):
            for sentence in re.split(r'(?<=[.!?])\s+', desc):
                if sentence.strip():
                    st.markdown(f"- {sentence.strip()}")
        else:
            st.markdown("- No features listed.")
    with col2:
        st.markdown("### Specifications")
        if brand := product.get("productBrand"):
            st.markdown(f"**Brand:** {brand}")
        if material := product.get("primaryMaterial"):
            st.markdown(f"**Material:** {material}")
        if link := product.get("url_link"):
            st.link_button("View on Supplier Website", link)

    st.divider()

    # --- CHANGED: Transposed pricing table ---
    quantities = []
    prices = []
    for i in range(5):
        qty = product.get(f"ProductPrice_{i}_quantityMin")
        price_val = product.get(f"ProductPrice_{i}_price")
        if pd.notnull(qty) and pd.notnull(price_val):
            quantities.append(f"{int(qty)}")
            prices.append(f"${price_val:,.2f}")

    if quantities:
        st.markdown("### Tiered Pricing")
        
        # Generate the HTML table cells for each row
        qty_cells = "".join([f"<td>{q}</td>" for q in quantities])
        price_cells = "".join([f"<td><strong>{p}</strong></td>" for p in prices])

        # Construct the full HTML table with inline CSS
        html_table = f"""
        <style>
            .pricing-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            .pricing-table th, .pricing-table td {{
                border: 1px solid #d3d3d3;
                padding: 10px;
                text-align: center;
            }}
            .pricing-table th {{
                text-align: left;
                background-color: #f0f2f6;
                width: 35%;
            }}
        </style>
        <table class="pricing-table">
            <tbody>
                <tr>
                    <th>Quantity</th>
                    {qty_cells}
                </tr>
                <tr>
                    <th>Price per item (USD)</th>
                    {price_cells}
                </tr>
            </tbody>
        </table>
        """
        # Use st.html to render the custom table
        st.html(html_table)
    st.html("<span class='big-dialog'></span>")

# --- Main App ---
logo_url = "https://raw.githubusercontent.com/BashirGulistani/product_viewer_rep/main/idYu324uEk_logos.png"
st.markdown(f'<div style="background-color:#0E3B53; padding:1em; text-align:center;"><img src="{logo_url}" height="60"></div>', unsafe_allow_html=True)
st.title("Your Recommended Products")
st.markdown("Here are the product recommendations based on your request. Click **'View Details'** on any product card to learn more.")
st.divider()

df = load_data()
product_ids = fetch_product_ids_from_github()



###

# --- Initialize Session State for Favorites ---
if 'favorites' not in st.session_state:
    st.session_state.favorites = []

# --- Sidebar for Viewing Favorites ---
with st.sidebar:
    st.header(f"View Favorites ({len(st.session_state.favorites)})")

    if not st.session_state.favorites:
        st.write("You haven't added any favorites yet. Click the ❤️ on a product to add it.")
    else:
        # Get details for favorited products
        favorited_products_df = df[df['productId'].astype(str).isin(st.session_state.favorites)]

        for _, product in favorited_products_df.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                #st.write(product['productName'])
                st.write(clean_product_name(product.get("productName", "Unnamed Product")))
            with col2:
                st.button("➖", key=f"remove_{product['productId']}", on_click=remove_from_favorites, args=[str(product['productId'])])

        st.divider()
        st.subheader("Prepare Email")
        st.write("Enter your details below to generate a pre-filled email in your own email client.")
        
        user_email = st.text_input("Send To")
        company_name = st.text_input("Your Company Name")

        if st.button("Prepare Email"):
            if user_email and company_name and "@" in user_email:
                # Construct the email body
                body_lines = [
                    f"Hello,\n\nHere is my list of favorited products from {company_name}:\n"
                ]
                for _, product in favorited_products_df.iterrows():
                    cleaned_title2 = clean_product_name(product.get("productName", "Unnamed Product"))
                    name = cleaned_title2
                    pid = product.get('productId', 'N/A')
                    link = product.get('url_link', 'Not Available')
                    body_lines.append(f"• {name} (Item #{pid})")
                    body_lines.append(f"  Link: {link}\n")
                
                body = "\n".join(body_lines)

                # Create the mailto link
                subject = f"Product Inquiry from {company_name}"
                mailto_link = f"mailto:{user_email}?subject={quote(subject)}&body={quote(body)}"
                
                # Display the clickable link
                st.markdown(f'<a href="{mailto_link}" target="_blank" style="display:inline-block;padding:0.5em 1em;background-color:#007bff;color:white;border-radius:5px;text-decoration:none;">Click Here to Open Email</a>', unsafe_allow_html=True)
            else:
                st.warning("Please fill in a valid email and your company name.")

if not product_ids:
    st.warning("Could not find any recommended products. Please generate a new list from the main app.")
else:
    product_ids_str = [str(pid) for pid in product_ids]
    products_df = df[df["productId"].astype(str).isin(product_ids_str)].copy()

    products_df['thumbnail_url'] = products_df.apply(find_first_available_image, axis=1)
    products_with_images_df = products_df.dropna(subset=['thumbnail_url']).copy()

    if products_with_images_df.empty:
        st.error("No products with valid images could be found from your recommendation list.")
    else:
        cols = st.columns(5)
        for i, (index, product) in enumerate(products_with_images_df.iterrows()):
            with cols[i % 5]:
                with st.container(border=True):
                    
                    # --- Favorite Button (Heart Icon) ---
                    product_id_str = str(product.get('productId'))
                    is_favorited = product_id_str in st.session_state.favorites
                    
                    if is_favorited:
                        st.button("❤️ Remove", key=f"fav_{product_id_str}", on_click=remove_from_favorites, args=[product_id_str])
                    else:
                        st.button("🤍 Favorite", key=f"fav_{product_id_str}", on_click=add_to_favorites, args=[product_id_str])

                    # Card content
                    st.image(product['thumbnail_url'])
                    cleaned_title2 = clean_product_name(product.get("productName", "Unnamed Product"))
                    st.markdown(f"<p style='text-align:center; font-weight:bold;'>{cleaned_title2}</p>", unsafe_allow_html=True)
                    render_color_swatches(product.get('hexColor'))
                    st.markdown(f"<p style='text-align:center; opacity:0.7; font-size:0.9em;'>Item #{product_id_str}</p>", unsafe_allow_html=True)
                    
                    price = product.get("product_price")
                    price_text = f"As low as <strong style='font-size: 1.15em;'>${price:,.2f}</strong>" if pd.notnull(price) else ""
                    st.markdown(f"<p style='text-align:center;'>{price_text}</p>", unsafe_allow_html=True)

                    if st.button("View Details", key=f"view_{product_id_str}", use_container_width=True):
                        show_product_dialog(product)
                
                st.write("")
