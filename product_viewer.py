import streamlit as st
import pandas as pd
import requests
import re
import ast
from urllib.parse import quote
import webcolors

# --- Page Configuration (MUST be the first st command) ---
st.set_page_config(
    layout="wide",
    page_title="Product Recommendations",
    initial_sidebar_state="expanded"
)

# --- Caching and Data Loading ---

@st.cache_data
def load_data():
    """Loads the product data from the CSV file."""
    try:
        return pd.read_csv("final_data.csv")
    except FileNotFoundError:
        st.error("The 'final_data.csv' file was not found. Please make sure it's in the same directory.")
        return pd.DataFrame()

@st.cache_data
def fetch_product_batches_from_github():
    """Fetches the recommended product batches from the GitHub JSON file."""
    # Updated URL to point to the new batch file
    api_url = "https://api.github.com/repos/BashirGulistani/product_viewer_rep/contents/batches/recommendation_batch.json"
    headers = {"Accept": "application/vnd.github.v3.raw"}

    # Use GitHub token from secrets if available for private repos
    if "github" in st.secrets and "token" in st.secrets["github"]:
        headers["Authorization"] = f"Bearer {st.secrets['github']['token']}"

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        # The response is now expected to be a dictionary, e.g., {"Category": [IDs]}
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"GitHub API error: Could not fetch data. {e}")
    except ValueError:
        st.error("Failed to parse JSON from GitHub response. The file might be malformed.")
    # Return an empty dictionary on failure
    return {}


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
                        color_name = get_color_name(clean_part)
                        swatches_html += f'<div title="{color_name}" style="width:22px; height:22px; background-color:{clean_part}; border-radius:50%; display:inline-block; margin:0 4px 4px 0; border:1px solid #eee;"></div>'
    except (ValueError, SyntaxError):
        pass # Ignore malformed color strings
    st.markdown(f'<div style="height: 30px; text-align: center;">{swatches_html}</div>', unsafe_allow_html=True)


def add_to_favorites(product_id):
    """Adds a product ID to the favorites list in session state."""
    if product_id not in st.session_state.favorites:
        st.session_state.favorites.append(product_id)

def remove_from_favorites(product_id):
    """Removes a product ID from the favorites list."""
    if product_id in st.session_state.favorites:
        st.session_state.favorites.remove(product_id)

def clean_product_name(name_str):
    """Cleans product names by removing disallowed characters."""
    if not isinstance(name_str, str):
        return "Unnamed Product"
    cleaned_name = re.sub(r"[^a-zA-Z0-9\s\-&/',.]", '', name_str)
    return re.sub(r'\s+', ' ', cleaned_name).strip()

def find_first_available_image(product):
    """Iterates through image_url columns and returns the first valid URL."""
    for i in range(1, 6):
        image_url = product.get(f"image_url_{i}")
        if isinstance(image_url, str) and image_url.startswith("http"):
            return image_url
    return None # Return None if no valid image is found

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

    # Image Slideshow Logic (assuming a helper function not shown for brevity)
    # Image Slideshow Logic
    valid_images = [img for img in images if isinstance(img, str) and img.startswith("http")]

    if valid_images:
        # Use tabs to create a simple, clickable image gallery/slideshow
        tab_titles = [f"Image {i+1}" for i in range(len(valid_images))]
        tabs = st.tabs(tab_titles)
        for i, tab in enumerate(tabs):
            with tab:
                st.image(valid_images[i], use_column_width='auto')
    else:
        st.image("https://via.placeholder.com/600x400.png?text=Image+Not+Available")


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

    # Transposed pricing table
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
        qty_cells = "".join([f"<td style='text-align:center;'>{q}</td>" for q in quantities])
        price_cells = "".join([f"<td style='text-align:center;'><strong>{p}</strong></td>" for p in prices])

        # Construct the full HTML table with inline CSS
        st.html(f"""
        <style> .pricing-table {{ width: 100%; border-collapse: collapse; }} .pricing-table th, .pricing-table td {{ border: 1px solid #d3d3d3; padding: 10px; }} .pricing-table th {{ text-align: left; background-color: #f0f2f6; }} </style>
        <table class="pricing-table">
            <tbody>
                <tr><th>Quantity</th>{qty_cells}</tr>
                <tr><th>Price per item (USD)</th>{price_cells}</tr>
            </tbody>
        </table>
        """)


# --- Main App ---

# Initialize session state for favorites
if 'favorites' not in st.session_state:
    st.session_state.favorites = []

logo_url = "https://raw.githubusercontent.com/BashirGulistani/product_viewer_rep/main/idYu324uEk_logos.png"
st.markdown(f'<div style="background-color:#0E3B53; padding:1em; text-align:center;"><img src="{logo_url}" height="60"></div>', unsafe_allow_html=True)
st.title("Your Recommended Products")
st.markdown("Here are the product recommendations based on your request, grouped by category.")
st.divider()

df = load_data()
product_batches = fetch_product_batches_from_github()

# --- Sidebar for Viewing Favorites ---
if st.session_state.favorites:
    with st.sidebar:
        st.header(f"View Favorites ({len(st.session_state.favorites)})")
        favorited_products_df = df[df['productId'].astype(str).isin(st.session_state.favorites)]

        for _, product in favorited_products_df.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(clean_product_name(product.get("productName")))
            with col2:
                st.button("➖", key=f"remove_{product['productId']}", on_click=remove_from_favorites, args=[str(product['productId'])])
        
        st.divider()
        st.subheader("Prepare Email")
        user_email = st.text_input("Your Email Address")
        company_name = st.text_input("Your Company Name")

        if st.button("Prepare Email"):
            if user_email and company_name and "@" in user_email:
                body_lines = [f"Hello,\n\nHere is my list of favorited products from {company_name}:\n"]
                for _, product in favorited_products_df.iterrows():
                    body_lines.append(f"• {product.get('productName', 'N/A')} (Item #{product.get('productId', 'N/A')})")
                    body_lines.append(f"  Link: {product.get('url_link', 'Not Available')}\n")
                
                subject = f"Product Inquiry from {company_name}"
                mailto_link = f"mailto:{user_email}?subject={quote(subject)}&body={quote('\n'.join(body_lines))}"
                st.markdown(f'<a href="{mailto_link}" target="_blank">Click Here to Open Email</a>', unsafe_allow_html=True)
            else:
                st.warning("Please fill in a valid email and your company name.")

# --- Display Product Batches ---
if not product_batches:
    st.warning("Could not find any recommended products. Please generate a new list from the main app.")
else:
    for category, product_ids in product_batches.items():
        if not product_ids:
            continue

        # Display category headline
        st.subheader(category)

        # Filter the main DataFrame for products in the current category
        product_ids_str = [str(pid) for pid in product_ids]
        products_df = df[df["productId"].astype(str).isin(product_ids_str)].copy()
        
        products_df['thumbnail_url'] = products_df.apply(find_first_available_image, axis=1)
        products_to_display_df = products_df.dropna(subset=['thumbnail_url']).copy()

        if products_to_display_df.empty:
            st.info(f"No products with valid images could be found for the category: {category}")
            continue

        # Display products in a single row that wraps
        num_columns = 5 # Set number of columns for the grid
        cols = st.columns(num_columns)
        for i, (index, product) in enumerate(products_to_display_df.iterrows()):
            with cols[i % num_columns]:
                with st.container(border=True):
                    product_id_str = str(product.get('productId'))
                    is_favorited = product_id_str in st.session_state.favorites
                    
                    # Favorite button logic
                    if is_favorited:
                        st.button("❤️ Remove", key=f"fav_{product_id_str}", on_click=remove_from_favorites, args=[product_id_str])
                    else:
                        st.button("🤍 Favorite", key=f"fav_{product_id_str}", on_click=add_to_favorites, args=[product_id_str])

                    # Card content
                    st.image(product['thumbnail_url'])
                    cleaned_title = clean_product_name(product.get("productName"))
                    st.markdown(f"<p style='text-align:center; font-weight:bold; height: 3em; overflow: hidden;'>{cleaned_title}</p>", unsafe_allow_html=True)
                    render_color_swatches(product.get('hexColor'))
                    st.markdown(f"<p style='text-align:center; opacity:0.7; font-size:0.9em;'>Item #{product_id_str}</p>", unsafe_allow_html=True)

                    price = product.get("product_price")
                    price_text = f"As low as <strong style='font-size: 1.15em;'>${price:,.2f}</strong>" if pd.notnull(price) else ""
                    st.markdown(f"<p style='text-align:center;'>{price_text}</p>", unsafe_allow_html=True)

                    if st.button("View Details", key=f"view_{product_id_str}", use_container_width=True):
                        show_product_dialog(product)

        st.divider() # Add a line after each category's products
