import streamlit as st
import pandas as pd
import requests
import re
import ast
from urllib.parse import quote
import webcolors
from streamlit_extras.add_vertical_space import add_vertical_space
import math

# --- Page Configuration (MUST be the first st command) ---
st.set_page_config(
    layout="wide",
    page_title="Product Recommendations",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.title-stack{
  display:block;
}
.title-stack .title{
  /* kill the global title spacing just for this spot */
  min-height: 0 !important;
  margin: 0 !important;
  line-height: 1.12;          /* tight */
  text-align: left;           /* left align */
}
.title-stack .pid{
  margin: 0 0 10px 0;       /* zero gap under the name */
  padding-left: 16px;         /* slight indent to the right */
  line-height: 1.12;
  font-size: 0.9em;
  opacity: .75;               /* caption look */
  text-align: left;
}
.title-inline{
  display:flex; align-items:baseline; justify-content:space-between; gap:8px;
}
.title-inline .title{ margin:0; }            /* you already style .title */
.title-inline .meta{                         /* caption look */
  font-size:.85em; opacity:.75; white-space:nowrap; margin:0;
}
/* same variables & layout helpers */
:root { --card-h: 520px; }

[data-testid="stHorizontalBlock"] { align-items: stretch; row-gap: 10px; }
[data-testid="stHorizontalBlock"] [data-testid="column"] { padding-left:.25rem; padding-right:.25rem; }
[data-testid="stHorizontalBlock"] [data-testid="column"] > div { display:flex; }

/* Uniform card (works whether you wrap with .card OR rely on :has(.img-wrap)) */


/* If you didn't add .card, apply same look to any block that contains .img-wrap */


[data-testid="stHorizontalBlock"] [data-testid="column"] > div:has(.img-wrap):not(:has(.card)){
  display:flex !important; flex-direction:column;
  height: var(--card-h) !important; overflow:hidden;
  border:1px solid #e8eaef; border-radius:14px; padding:10px; background:#fff;
  box-shadow:0 1px 2px rgba(0,0,0,.04);
}

/* Image frame */
.img-wrap {
  height: 220px; display:flex; align-items:center; justify-content:center;
  background:#fafafa; border:1px solid #f0f0f0; border-radius:10px; overflow:hidden;
}
.img-wrap img { max-height:100%; max-width:100%; object-fit:contain; }

/* Title with fixed space (2 lines max) */
.title {
  min-height:48px; margin:18px 0 4px; text-align:center;
  font: 500 13px/1.2 "Libre Franklin", system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
}
.meta { text-align:center; opacity:.7; font-size:.9em; }
.price { text-align:center; margin-top:2px; }

.stButton > button{
  border-radius: 10px;
  font-weight: 600;
  border: 1px solid #e5e7eb;
  background: #0E3B53;
  color: #fff;
  box-shadow: 0 1px 2px rgba(15, 0, 75, 1);
  transition: background .2s ease, box-shadow .2s ease, transform .02s ease;
}
.stButton > button:hover{
  background: #0b2f42;   /* darker */
  border-color: #0b2f42;
  color: #fff;
  box-shadow: none;
  filter: none;
}
</style>
""", unsafe_allow_html=True)



# --- Caching and Data Loading ---


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    df = pd.read_parquet('final_data.parquet')
    return df



def fetch_product_batches_from_github():
    """Fetches the recommended product batches from the GitHub JSON file."""
    # Updated URL to point to the new batch file
    api_url = "https://api.github.com/repos/BashirGulistani/product_rec_v2/contents/batches/recommendation_bundle.json"
    headers = {"Accept": "application/vnd.github.v3.raw"}

    # Use GitHub token from secrets if available for private repos
    headers["Authorization"] = f"Bearer {st.secrets["GITHUB_TOKEN"]}"

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
    def _norm_hex(s: str):
        s = s.strip()
        if not s.startswith('#'):
            return None
        h = s[1:]
        # expand #RGB -> #RRGGBB
        if len(h) == 3 and all(c in '0123456789abcdefABCDEF' for c in h):
            h = ''.join(c*2 for c in h)
        # accept #RRGGBB
        if len(h) == 6 and all(c in '0123456789abcdefABCDEF' for c in h):
            return '#' + h.lower()
        return None

    swatches_html = ""
    seen = set()  # track normalized hexes we've already added

    if not isinstance(hex_list_str, str):
        return

    try:
        hex_codes = ast.literal_eval(hex_list_str)
        if isinstance(hex_codes, list):
            for color in hex_codes:
                # split things like "#fff/#000 - #FF0000"
                for part in re.split(r'[-/;,]\s*', str(color)):
                    nh = _norm_hex(part)
                    if not nh or nh in seen:
                        continue
                    seen.add(nh)
                    color_name = get_color_name(nh)
                    swatches_html += (
                        f'<div title="{color_name}" '
                        f'style="width:22px; height:22px; background-color:{nh}; '
                        f'display:inline-block; margin:0 4px 4px 0; border:1px solid #ddd;"></div>'
                    )
    except (ValueError, SyntaxError):
        pass

    st.markdown(
        f'''
        <div style="min-height:56px; max-height:56px; overflow:hidden; text-align:center;">
            {swatches_html}
        </div>
        ''',
        unsafe_allow_html=True
    )



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

def render_image_slideshow(images, product_id):
    valid_images = [i for i in images if isinstance(i, str) and i.startswith("http")]
    if not valid_images:
        st.image("https://via.placeholder.com/800x600.png?text=Image+Not+Available", use_column_width=True)
        return

    swiper_id = f"swiper_{product_id}"
    container_height = 400    # taller = bigger images
    max_width = 1100          # clamp width inside the (now wider) dialog

    slides_html = "".join(f'''
      <div class="swiper-slide"><img src="{img}" /></div>
    ''' for img in valid_images)

    st.components.v1.html(f'''
<link rel="stylesheet" href="https://unpkg.com/swiper@9/swiper-bundle.min.css"/>
<style>
  /* center and size the carousel inside the iframe */
  #{swiper_id} {{
    width: 100%;                /* fill iframe width */
    max-width: {max_width}px;   /* clamp for readability */
    height: {container_height}px;
    margin: 0 auto;             /* center within iframe */
  }}
  #{swiper_id} .swiper-wrapper, #{swiper_id} .swiper-slide {{ height: 100%; }}
  #{swiper_id} .swiper-slide {{
    display:flex; align-items:center; justify-content:center; background:#fff;
  }}
  #{swiper_id} .swiper-slide img {{
    max-width:100%; max-height:100%; width:auto; height:auto; object-fit:contain; display:block;
  }}
</style>

<div class="swiper" id="{swiper_id}">
  <div class="swiper-wrapper">{slides_html}</div>
  <div class="swiper-pagination {swiper_id}-pagination"></div>
  <div class="swiper-button-prev {swiper_id}-prev" style="color:#0E3B53;"></div>
  <div class="swiper-button-next {swiper_id}-next" style="color:#0E3B53;"></div>
</div>

<script src="https://unpkg.com/swiper@9/swiper-bundle.min.js"></script>
<script>
  new Swiper('#{swiper_id}', {{
    loop: {str(len(valid_images) > 1).lower()},
    centeredSlides: true,
    pagination: {{ el: '.{swiper_id}-pagination', clickable: true }},
    navigation: {{ nextEl: '.{swiper_id}-next', prevEl: '.{swiper_id}-prev' }},
  }});
</script>
''', height=container_height)



# --- Dialog Function (using the decorator pattern) ---

st.markdown(
    """
<style>
/* Target the dialog container directly for robust styling */
div[data-testid="stDialog"] > div > div[role="dialog"] {
    width: 60vw;
    max-width: 900px;
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

    #images = [product.get(f'image_url_{i}') for i in range(1, 6)]
    #render_image_slideshow(images, product.get("productId"))
    imgs = [product.get(f"image_url_{i}") for i in range(1, 6)]
    imgs = [u for u in imgs if isinstance(u, str) and u.startswith("http")]
    pid = str(product.get("productId", "0"))

    # Center the carousel in the dialog
    left, mid, right = st.columns([2, 7, 1])   # wider middle = centered
    with mid:
        render_image_slideshow(imgs, pid)      # your Swiper-based function


            # Transposed pricing table
    quantities = []
    prices = []
    for i in range(5):
        qty_raw = pd.to_numeric(product.get(f"ProductPrice_{i}_quantityMin"), errors="coerce")
        price_raw = pd.to_numeric(product.get(f"ProductPrice_{i}_price"), errors="coerce")
        if pd.notnull(qty_raw) and pd.notnull(price_raw) and qty_raw > 0 and price_raw > 0:
            quantities.append(f"{int(qty_raw)}")
            prices.append(f"${price_raw:,.2f}")


    if quantities:
        
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
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Features")
        #if desc := product.get("description"):
        if (desc := product.get("description")) and desc.lower() != "nan":
            for sentence in re.split(r'(?<=[.!?])\s+', desc):
                if sentence.strip():
                    st.markdown(f"- {sentence.strip()}")
        else:
            st.markdown("- No features listed.")
    with col2:
        st.markdown("### Specifications")
        #if brand := product.get("productBrand"):
        if (brand := product.get("productBrand")) and brand.lower() != "nan" and brand != "-":
            st.markdown(f"**Brand:** {brand}")
        #if material := product.get("primaryMaterial"):
        if (material := product.get("primaryMaterial")) and material.lower() != "nan":
            st.markdown(f"**Material:** {material}")
        dimension_parts = []
        if (
            (height := product.get("height")) is not None and not (
                (isinstance(height, float) and math.isnan(height)) or
                (isinstance(height, str) and height.lower() == "nan")
            )
        ):
            dimension_parts.append(f'{height}"H')

        if (
            (width := product.get("width")) is not None and not (
                (isinstance(width, float) and math.isnan(width)) or
                (isinstance(width, str) and width.lower() == "nan")
            )
        ):
            dimension_parts.append(f'{width}"W')
        if dimension_parts:
            dimensions_str = " x ".join(dimension_parts)
            st.markdown(f"**Dimensions:** {dimensions_str}")

        if (
            (weight := product.get("weight")) is not None and not (
                (isinstance(weight, float) and math.isnan(weight)) or
                (isinstance(weight, str) and weight.lower() == "nan")
            )
        ):
            st.markdown(f"**Weight:** {weight} Ib.")
            
        #if labelsize := product.get("labelSizes"):
        if (labelsize := product.get("labelSizes")) and labelsize.lower() != "nan":
            if isinstance(labelsize, (list, tuple)):
                size_order = ["XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]
                sorted_label_sizes = sorted(labelsize, key=size_order.index)
                size_string = ", ".join(sorted_label_sizes)
                st.markdown(f"**Size Options:** {size_string}")        
        #if link := product.get("url_link"):
        if (link := product.get("url_link")) and link.lower() != "nan":
            st.link_button("View on Supplier Website", link)

    st.divider()
    


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

# --- Sidebar for Viewing Favorites ---
if st.session_state.favorites:
    with st.sidebar:
        st.header(f"View Favorites ({len(st.session_state.favorites)})")
        favorited_products_df = df[df['productId'].astype(str).isin(st.session_state.favorites)]
        number = 1
        for _, product in favorited_products_df.iterrows():            
            title = clean_product_name(product.get("productName", ""))
            pid   = str(product.get("productId", ""))
            
            st.markdown(
                f"""
                <div class="title-stack">
                  <div class="title">({number}) {title}</div>
                  <div class="pid">Item # {pid}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            number+=1
        
        st.divider()
        #to_email = st.text_input("Your Email Address")
        to_email = 'jay@inkdstores.com'
        company_name = st.text_input(
            label="Company Name",  
            placeholder="Your Company Name",
            label_visibility="hidden"
        )

        if st.button("Submit"):
            if to_email and company_name and "@" in to_email:
                body_lines = [f"Hello,\n\nHere is my list of favorited products from {company_name}:\n"]
                for _, product in favorited_products_df.iterrows():
                    body_lines.append(f"• {product.get('productName', 'N/A')} (Item #{product.get('productId', 'N/A')})")
                    body_lines.append(f"  Link: {product.get('url_link', 'Not Available')}\n")
                
                subject = f"Product Inquiry from {company_name}"
                mailto_link = f"mailto:{to_email}?subject={quote(subject)}&body={quote('\n'.join(body_lines))}"
                st.markdown(f'<a href="{mailto_link}" target="_blank">Click Here to Open Email</a>', unsafe_allow_html=True)
            else:
                st.warning("Please provide your company name.")

# --- Display Product Batches ---

product_batches = fetch_product_batches_from_github()


# --- Normalize & globally dedupe the incoming JSON --------------------------
def _normalize_batches(batches: dict):
    """Return (favorites_map, others_map, subcats_map) where each map is:
       {subcat_name: [str(productId), ...]} and empty entries removed."""
    def _norm_map(m):
        out = {}
        for k, ids in (m or {}).items():
            if not ids:
                continue
            # coerce to strings & de-dupe within the list preserving order
            seen = set()
            uniq = []
            for pid in ids:
                spid = str(pid)
                if spid not in seen:
                    seen.add(spid)
                    uniq.append(spid)
            if uniq:
                out[str(k)] = uniq
        return out

    has_top = ("Favorites" in batches) or ("Others" in batches)
    fav = _norm_map(batches.get("Favorites") if has_top else {})
    oth = _norm_map(batches.get("Others") if has_top else {})
    # everything else = subcategory buckets
    sub = _norm_map({k: v for k, v in batches.items() if k not in ("Favorites", "Others")})
    return fav, oth, sub

def _dedupe_across_sections(fav_map, oth_map, sub_map):
    """Remove any productId already emitted by a higher-priority section."""
    seen = set()

    def _strip_seen(m):
        cleaned = {}
        for subcat, ids in m.items():
            keep = []
            for pid in ids:
                if pid not in seen:
                    seen.add(pid)
                    keep.append(pid)
            if keep:
                cleaned[subcat] = keep
        return cleaned

    fav_clean = _strip_seen(fav_map)
    oth_clean = _strip_seen(oth_map)
    sub_clean = _strip_seen(sub_map)
    return fav_clean, oth_clean, sub_clean


def _coerce_id_list(v):
    """Return a list[str] of productIds."""
    if isinstance(v, (list, tuple, set)):
        return [str(x) for x in v]
    # single value fallback
    return [str(v)] if pd.notna(v) else []

def _as_subcat_map(value):
    """
    Normalize a value into {subcat: [ids...]}.
    - dict -> keep keys as subcats (values coerced to list of ids)
    - list -> single bucket 'All'
    - other -> empty
    """
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            ids = _coerce_id_list(v)
            if ids:
                out[str(k)] = ids
        return out
    elif isinstance(value, (list, tuple, set)):
        ids = _coerce_id_list(value)
        return {"All": ids} if ids else {}
    return {}

def _render_product_grid(title_prefix, subcat_label, id_list):
    """Render a single subcategory grid."""
    if not id_list:
        return

    # Filter df and keep only rows with a valid thumbnail
    products_df = df[df["productId"].astype(str).isin([str(i) for i in id_list])].copy()
    if "thumbnail_url" not in products_df.columns:
        products_df["thumbnail_url"] = products_df.apply(find_first_available_image, axis=1)
    else:
        # backfill if any missing
        products_df.loc[products_df["thumbnail_url"].isna(), "thumbnail_url"] = (
            products_df[products_df["thumbnail_url"].isna()].apply(find_first_available_image, axis=1)
        )

    products_to_display_df = products_df.dropna(subset=["thumbnail_url"]).copy()
    if products_to_display_df.empty:
        st.info(f"No products with valid images for: {subcat_label}")
        return

    # your existing sort
    products_to_display_df = products_to_display_df.sort_values(by="product_price", na_position="last")

    # grid
    num_columns = 5
    cols = st.columns(num_columns)
    k = 1
    for i, (_, product) in enumerate(products_to_display_df.iterrows()):
        key_suffix = f"{title_prefix}_{subcat_label}_{product.get('productId')}_{k}"
        k+=1
        with cols[i % num_columns]:
            with st.container(border=True):
                pid = str(product.get("productId"))

                #####
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                # image in a fixed-height frame
                thumb = product.get("thumbnail_url")
                if thumb:
                    st.markdown(f"<div class='img-wrap'><img src='{thumb}'></div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='img-wrap'><img src='https://via.placeholder.com/400x300.png?text=No+Image'></div>", unsafe_allow_html=True)
                
                # title / meta / price exactly like the main page
                title = clean_product_name(product.get("productName"))
                st.markdown(f"<div class='title'>{title}</div>", unsafe_allow_html=True)
                render_color_swatches(product.get('hexColor'))
                pid = str(product.get('productId'))
                st.markdown(f"<div class='meta'>Item #{pid}</div>", unsafe_allow_html=True)
                
                price_val = pd.to_numeric(product.get("product_price"), errors="coerce")
                if pd.notnull(price_val) and price_val > 0:
                    st.markdown(
                        f"<div class='price'>As low as <strong style='font-size:1.05em;'>${price_val:,.2f}</strong></div>",
                        unsafe_allow_html=True
                    )
                
                st.markdown("</div>", unsafe_allow_html=True)  # close .card




                
                # Card content


                add_vertical_space(1)
                if st.button("View Details", key=f"view_{key_suffix}", use_container_width=True):
                    show_product_dialog(product)
                # Favorite toggle (use unique keys to avoid collisions)
                is_favorited = pid in st.session_state.favorites
                if is_favorited:
                    st.button("Remove", key=f"fav_rm_{key_suffix}", on_click=remove_from_favorites, args=[pid], use_container_width=True)
                else:
                    st.button("Add to Kit", key=f"fav_add_{key_suffix}", on_click=add_to_favorites, args=[pid],use_container_width=True)



def _render_section(section_title, subcat_map, emphasize=False):
    """Render a whole section (Favorites/Others or a single-category block)."""
    key = str(section_title).strip().lower()
    title_map = {
        "favorites": "Recommended",
        "others": "More Options",
    }
    # Use .get() with a default value to handle any section_title gracefully
    display_title = title_map.get(key, section_title)

    # pick heading level
    (st.header if emphasize else st.subheader)(display_title)

    # Show each subcategory inside this section (sorted for consistency)
    for subcat_name in sorted(subcat_map.keys()):
        
        # MODIFIED PART:
        # Always show the subcategory name as a label, unless it's a special "All" bucket.
        # This now works for "Favorites", "Others", AND direct category blocks.
        if subcat_name != "All":
            st.markdown(f"**{subcat_name}**")
            
        _render_product_grid(section_title, subcat_name, subcat_map[subcat_name])
    st.divider()



# 1) normalize incoming structure (supports either Favorites/Others or just subcats)
fav_map, oth_map, subcats_map = _normalize_batches(product_batches)

# 2) globally de-dupe in priority order: Favorites > Others > Subcategories
fav_clean, oth_clean, sub_clean = _dedupe_across_sections(fav_map, oth_map, subcats_map)

# 3) Build sections in the order you want to render
sections = []
if fav_clean: sections.append(("Favorites", fav_clean, True))   # emphasize=True if you want bold/labels
if oth_clean: sections.append(("Others", oth_clean, False))
if sub_clean: sections.append(("Categories", sub_clean, False))  # label for your subcategory block(s)

# 4) Render
if not sections:
    st.warning("Could not find any usable products in the JSON.")
else:
    for title, subcat_map, emphasize in sections:
        _render_section(title, subcat_map, emphasize=emphasize)
