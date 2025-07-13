import streamlit as st
import json
from pathlib import Path
import random
from collections import defaultdict
import difflib
import spacy

# Load data
data_path = Path(__file__).parent / "data" / "materials.json"
with open(data_path, encoding="utf-8") as f:
    materials = json.load(f)


# Helper: filter valid category names
def valid_category(cat):
    return isinstance(cat, str) and len(cat.strip()) > 1


def normalize(text):
    return "".join(e for e in text.lower() if e.isalnum() or e.isspace()).strip()


def words(text):
    return set(normalize(text).split())


# Get all unique, proper categories and suppliers (handle string or list for category)
all_categories = set()
for item in materials:
    cats = item.get("category", [])
    if isinstance(cats, str):
        cats = [cats]
    if isinstance(cats, list):
        for cat in cats:
            if valid_category(cat):
                all_categories.add(cat.strip())
all_categories = sorted(all_categories)

all_suppliers = sorted(
    {item.get("supplier", "") for item in materials if item.get("supplier")}
)

st.title("Donizo Materials Explorer")

tabs = st.tabs(["Browse", "Compare Prices"])

with tabs[0]:
    # Sidebar: select category and supplier
    category = st.sidebar.selectbox("Select a category", ["All"] + all_categories)
    supplier = st.sidebar.selectbox("Select a supplier", ["All"] + all_suppliers)

    # --- Sidebar: Show 3 sample categories and API links ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Sample API Links:**")
    if len(all_categories) >= 3:
        sample_cats = random.sample(all_categories, 3)
    else:
        sample_cats = all_categories
    for cat in sample_cats:
        api_url = f"http://127.0.0.1:8000/materials/{cat.replace(' ', '%20')}"
        st.sidebar.markdown(
            f"<a href='{api_url}' target='_blank'><button style='width:100%;margin-bottom:6px'>{cat} (View as API)</button></a>",
            unsafe_allow_html=True,
        )

    # Filter data
    filtered = materials
    if category != "All":
        filtered = [
            item
            for item in filtered
            if (
                (
                    isinstance(item.get("category", []), list)
                    and category in item.get("category", [])
                )
                or (
                    isinstance(item.get("category", []), str)
                    and category == item.get("category", [])
                )
            )
        ]
    if supplier != "All":
        filtered = [item for item in filtered if item.get("supplier") == supplier]

    st.write(
        f"Showing {len(filtered)} products in category: {category}, supplier: {supplier}"
    )

    # Set max width for the main content area
    st.markdown(
        """
        <style>
        [data-testid=\"stMainBlockContainer\"] {
            max-width: 80vw;
            margin-left: auto;
            margin-right: auto;
        }
        .ecom-card {
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 18px 12px 12px 12px;
            margin-bottom: 18px;
            background: #fff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            text-align: center;
            width: 100%;
            display: block;
        }
        .ecom-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin: 10px 0 4px 0;
            text-align: center;
        }
        .ecom-price {
            color: #2e7d32;
            font-size: 1.1rem;
            font-weight: bold;
            margin-bottom: 6px;
        }
        .ecom-badge {
            display: inline-block;
            background: #1976d2;
            color: #fff;
            border-radius: 8px;
            font-size: 0.85rem;
            padding: 2px 10px;
            margin-bottom: 8px;
        }
        .ecom-fields {
            font-size: 0.95rem;
            margin-top: 8px;
            width: 100%;
            text-align: left;
            display: inline-block;
        }
        .ecom-fields strong {
            color: #333;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Display products in a grid (3 per row), e-commerce style
    cols = st.columns(3)
    for idx, item in enumerate(filtered):
        with cols[idx % 3]:
            card_html = '<div class="ecom-card">'
            if item.get("image_url"):
                card_html += f'<img src="{item["image_url"]}" width="180" style="margin-bottom:8px;"/>'
            card_html += f'<div class="ecom-title">{item.get("name", "")}</div>'
            if item.get("price"):
                card_html += f'<div class="ecom-price">{item["price"]}</div>'
            if item.get("supplier"):
                card_html += f'<span class="ecom-badge">{item["supplier"]}</span>'
            # Show only non-empty fields except image_url, name, price, supplier
            field_html = ""
            for key, value in item.items():
                if key in ["image_url", "name", "price", "supplier"]:
                    continue
                if value is None or value == "" or value == []:
                    continue
                field_html += f"<div><strong>{key}:</strong> {value}</div>"
            if field_html:
                card_html += f'<div class="ecom-fields">{field_html}</div>'
            card_html += "</div>"
            st.markdown(card_html, unsafe_allow_html=True)


@st.cache_resource
def get_nlp():
    return spacy.load("fr_core_news_md")  # Use medium model for better similarity


nlp = get_nlp()


def spacy_normalize(text):
    doc = nlp(text.lower())
    tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
    return " ".join(tokens)


def spacy_similarity(text1, text2):
    if not text1.strip() or not text2.strip():
        return 0.0
    doc1 = nlp(text1)
    doc2 = nlp(text2)
    return doc1.similarity(doc2)


with tabs[1]:
    st.header("Compare Prices Across Suppliers")
    st.write(
        "Products available from multiple suppliers (using spaCy NLP on name and all category fields) are shown below. In production this would be tokenized and processed via a vector database."
    )

    filter_keyword = st.text_input(
        "Enter a keyword to filter products for debug (e.g., 'spa', 'piscine', 'bain'):",
        value="spa",
    )
    norm_filter_keyword = spacy_normalize(filter_keyword)
    show_debug = st.checkbox("Show debug info", value=False)
    compare_clicked = st.button("Compare")

    if compare_clicked:
        with st.spinner("Comparing products across suppliers..."):
            # Build a list of (norm_name, norm_category, item) using all category fields
            product_tuples = []
            for item in materials:
                name = item.get("name", "")
                cats = item.get("category", [])
                if isinstance(cats, str):
                    cats = [cats]
                for cat_field in [
                    "category_primary",
                    "category_secondary",
                    "category_tertiary",
                ]:
                    cat_val = item.get(cat_field)
                    if cat_val and isinstance(cat_val, str):
                        cats.append(cat_val)
                cat_str = " ".join(
                    sorted(set([str(cat) for cat in cats if isinstance(cat, str)]))
                )
                norm_name = spacy_normalize(name)
                norm_cat = spacy_normalize(cat_str)
                product_tuples.append((norm_name, norm_cat, item))

            # Debug output (optional)
            if show_debug:
                st.markdown(
                    f"**Debug: Normalized names and categories for products containing '{filter_keyword}':**"
                )
                for norm_name, norm_cat, item in product_tuples:
                    orig_name = item.get("name", "")
                    orig_cats = item.get("category", [])
                    if isinstance(orig_cats, str):
                        orig_cats = [orig_cats]
                    all_cats = orig_cats + [
                        item.get(f, "")
                        for f in [
                            "category_primary",
                            "category_secondary",
                            "category_tertiary",
                        ]
                    ]
                    all_cats_str = " ".join([str(c) for c in all_cats if c])
                    # Use normalized keyword for matching
                    if (
                        norm_filter_keyword in norm_name
                        or norm_filter_keyword in norm_cat
                    ):
                        st.write(f"Supplier: {item.get('supplier','')}")
                        st.write(f"Original Name: {orig_name}")
                        st.write(f"Normalized Name: {norm_name}")
                        st.write(f"All Categories: {all_cats_str}")
                        st.write(f"Normalized Categories: {norm_cat}")
                        st.write("---")

            # Group by spaCy similarity (lowered thresholds)
            groups = []
            used = set()
            for i, (name1, cat1, item1) in enumerate(product_tuples):
                if i in used:
                    continue
                group = [item1]
                used.add(i)
                for j, (name2, cat2, item2) in enumerate(product_tuples):
                    if j == i or j in used:
                        continue
                    # Lowered thresholds for more flexible matching
                    name_sim = spacy_similarity(name1, name2)
                    cat_sim = spacy_similarity(cat1, cat2)
                    if name_sim > 0.6 and cat_sim > 0.5:
                        group.append(item2)
                        used.add(j)
                if len({g["supplier"] for g in group}) > 1:
                    groups.append(group)

            # Results display: use e-commerce card style for each product in group
            if not groups:
                st.info("No matching products found across suppliers.")
            else:
                for group in groups:
                    st.subheader(group[0]["name"])
                    # Display in rows of 3 cards per row
                    for row_start in range(0, len(group), 3):
                        row_items = group[row_start : row_start + 3]
                        cols = st.columns(len(row_items))
                        for idx, item in enumerate(row_items):
                            with cols[idx]:
                                card_html = '<div class="ecom-card">'
                                if item.get("image_url"):
                                    card_html += f'<img src="{item["image_url"]}" width="180" style="margin-bottom:8px;"/>'
                                card_html += f'<div class="ecom-title">{item.get("name", "")}</div>'
                                if item.get("price"):
                                    card_html += (
                                        f'<div class="ecom-price">{item["price"]}</div>'
                                    )
                                if item.get("supplier"):
                                    card_html += f'<span class="ecom-badge">{item["supplier"]}</span>'
                                # Show only non-empty fields except image_url, name, price, supplier
                                field_html = ""
                                for key, value in item.items():
                                    if key in [
                                        "image_url",
                                        "name",
                                        "price",
                                        "supplier",
                                    ]:
                                        continue
                                    if value is None or value == "" or value == []:
                                        continue
                                    field_html += (
                                        f"<div><strong>{key}:</strong> {value}</div>"
                                    )
                                if field_html:
                                    card_html += (
                                        f'<div class="ecom-fields">{field_html}</div>'
                                    )
                                card_html += "</div>"
                                st.markdown(card_html, unsafe_allow_html=True)
                    st.markdown("---")
