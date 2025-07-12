import os
import json
import yaml
import argparse
from bs4 import BeautifulSoup, Tag
from playwright.sync_api import sync_playwright
import random
import time
import playwright_stealth

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "scraper_config.yaml")
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "materials.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

TARGET_CATEGORIES = ["tiles", "sinks", "toilets", "paint", "vanities", "showers"]
CATEGORY_KEYWORDS = {
    "tiles": ["carrelage", "tile"],
    "sinks": ["evier", "sink"],
    "toilets": ["toilette", "wc", "toilet"],
    "paint": ["peinture", "paint"],
    "vanities": ["meuble", "vanity"],
    "showers": ["douche", "shower"],
}
VIEW_BTN_SELECTOR = "span.sc-hTtwUo.gCRoTb"

# List of realistic User-Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]


def get_random_headers():
    """Return a random User-Agent and Accept-Language header."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    }


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_data(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_text(soup, selector):
    if not selector:
        return None
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else None


def extract_attr(soup, selector, attr):
    if not selector:
        return None
    el = soup.select_one(selector)
    if el and el.has_attr(attr):
        val = el[attr]
        if isinstance(val, list):
            return val[0]
        return val
    return None


# --- Castorama ---
def discover_castorama_categories(base_url):
    discovered = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_extra_http_headers(HEADERS)
        page.goto(base_url)
        page.wait_for_timeout(5000)
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        nav_links = soup.find_all("a", href=True)
        for link in nav_links:
            text = link.get_text(strip=True).lower()
            href = link["href"]
            for cat_key, keywords in CATEGORY_KEYWORDS.items():
                if cat_key in discovered:
                    continue
                if any(kw in text for kw in keywords):
                    if "/cat_id_" in href or "/c/" in href:
                        if not href.startswith("http"):
                            href = base_url.rstrip("/") + href
                        discovered[cat_key] = href
        browser.close()
    return discovered


def scrape_castorama_product_listing(page, selectors, supplier, category_key):
    results = []
    while True:
        page.wait_for_timeout(1500)
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        products = soup.select(selectors["product_selector"])
        for prod in products:
            name = extract_text(prod, selectors["name_selector"])
            price = extract_text(prod, selectors["price_selector"])
            prod_url = extract_attr(prod, selectors["url_selector"], "href")
            if prod_url and not str(prod_url).startswith("http"):
                prod_url = supplier["base_url"].rstrip("/") + prod_url
            brand = (
                extract_text(prod, selectors.get("brand_selector", ""))
                if selectors.get("brand_selector")
                else None
            )
            unit = (
                extract_text(prod, selectors.get("unit_selector", ""))
                if selectors.get("unit_selector")
                else None
            )
            image_url = (
                extract_attr(prod, selectors.get("image_selector", ""), "src")
                if selectors.get("image_selector")
                else None
            )
            item = {
                "name": name,
                "category": category_key,
                "price": price,
                "url": prod_url,
                "brand": brand,
                "unit": unit,
                "image_url": image_url,
                "supplier": supplier["name"],
            }
            if item not in results:
                results.append(item)
        # Try to click next button
        try:
            next_btn = page.query_selector(
                supplier["pagination"]["next_button_selector"]
            )
            if next_btn and not next_btn.is_disabled():
                next_btn.click()
                page.wait_for_timeout(2000)
            else:
                break
        except Exception:
            break
    return results


def scrape_castorama_category_playwright(
    supplier, category_key, category_url, selectors
):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_extra_http_headers(HEADERS)
        page.goto(category_url)
        page.wait_for_timeout(2000)
        view_btns = page.query_selector_all(VIEW_BTN_SELECTOR)
        print(
            f"[{category_key}] Found {len(view_btns)} 'View' buttons on category page."
        )
        for idx, btn in enumerate(view_btns):
            try:
                btn.click()
                page.wait_for_timeout(2000)
                cat_results = scrape_castorama_product_listing(
                    page, selectors, supplier, category_key
                )
                results.extend(cat_results)
                page.go_back()
                page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Error clicking 'View' button {idx}: {e}")
                continue
        browser.close()
    return results


# --- ManoMano ---
def discover_manomano_categories(base_url):
    discovered = {}
    found_urls = set()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_extra_http_headers(HEADERS)
        page.goto(base_url)
        page.wait_for_selector("section.ec_tSD", timeout=15000)
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        section = soup.find("section", class_="ec_tSD")
        if section and isinstance(section, Tag):
            subcats = section.find_all(
                "a", {"data-testid": "seo-family-subcategory"}, href=True
            )
            for link in subcats:
                text = link.get_text(strip=True).lower()
                href = link["href"]
                if not href.startswith("http"):
                    href = base_url.rstrip("/") + href
                if href not in found_urls:
                    # Use subcategory text as key, add numeric suffix if duplicate
                    base_key = text.replace(" ", "_")
                    key = base_key
                    i = 2
                    while key in discovered:
                        key = f"{base_key}_{i}"
                        i += 1
                    discovered[key] = href
                    found_urls.add(href)
                if len(discovered) >= 10:
                    break
        browser.close()
    return discovered


def scrape_manomano_category_playwright(
    supplier, category_key, category_url, selectors
):
    """
    Scrape all products from a ManoMano category page, following paginated navigation.
    Uses global headers and rotates User-Agent for each session. Applies stealth to reduce bot detection.
    """
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        headers = get_random_headers()
        page = browser.new_page(extra_http_headers=headers)
        playwright_stealth.stealth(page)
        page.goto(category_url)
        # Wait for products container to load
        page.wait_for_selector(selectors["products_container"], timeout=15000)
        while True:
            # Wait for product cards to load
            page.wait_for_selector(selectors["product_selector"], timeout=10000)
            product_cards = page.query_selector_all(selectors["product_selector"])
            for card in product_cards:
                # Extract product details
                title_el = card.query_selector(selectors["name_selector"])
                image_el = card.query_selector(selectors["image_selector"])
                price_el = card.query_selector(selectors["price_selector"])
                title = title_el.inner_text().strip() if title_el else ""
                image = image_el.get_attribute("src") if image_el else ""
                price = price_el.inner_text().strip() if price_el else ""
                url = card.get_attribute("href") or ""
                if url and url.startswith("/"):
                    url = supplier["base_url"] + url
                results.append(
                    {
                        "category": category_key,
                        "title": title,
                        "image": image,
                        "price": price,
                        "url": url,
                    }
                )
            # Pagination: look for next page button
            next_button = page.query_selector('a[aria-label="Page suivante"]')
            if next_button and next_button.is_enabled():
                next_href = next_button.get_attribute("href")
                if next_href:
                    next_url = (
                        supplier["base_url"] + next_href
                        if next_href.startswith("/")
                        else next_href
                    )
                    time.sleep(
                        random.uniform(1, 3)
                    )  # Random delay to mimic human behavior
                    page.goto(next_url)
                    continue
            break
        browser.close()
    return results


# --- Main orchestrator ---
SUPPLIER_FUNCS = {
    "castorama": {
        "discover": discover_castorama_categories,
        "scrape": scrape_castorama_category_playwright,
    },
    "manomano": {
        "discover": discover_manomano_categories,
        "scrape": scrape_manomano_category_playwright,
    },
}


def main():
    parser = argparse.ArgumentParser(description="Donizo Material Scraper")
    parser.add_argument(
        "--supplier",
        type=str,
        default="all",
        help="Supplier to scrape (castorama, manomano, or all)",
    )
    args = parser.parse_args()

    config = load_config()
    all_data = []
    suppliers = [
        s
        for s in config["suppliers"]
        if args.supplier == "all" or s["name"].lower() == args.supplier.lower()
    ]
    for supplier in suppliers:
        sname = supplier["name"].lower()
        if sname not in SUPPLIER_FUNCS:
            print(f"Skipping unsupported supplier: {sname}")
            continue
        print(f"\n=== Scraping {supplier['name']} ===")
        base_url = supplier["base_url"]
        pagination = supplier.get("pagination", {})
        discover_func = SUPPLIER_FUNCS[sname]["discover"]
        scrape_func = SUPPLIER_FUNCS[sname]["scrape"]
        discovered = discover_func(base_url)
        print("Discovered categories:", discovered)
        for cat_key, cat_url in discovered.items():
            # Use category-specific selectors if present, else fallback to 'tiles'
            cat_selectors = supplier["categories"].get(cat_key) or supplier[
                "categories"
            ].get("tiles")
            print(f"Scraping {supplier['name']} category: {cat_key} -> {cat_url}")
            results = scrape_func(
                {
                    "name": supplier["name"],
                    "base_url": base_url,
                    "pagination": pagination,
                },
                cat_key,
                cat_url,
                cat_selectors,
            )
            all_data.extend(results)
    save_data(all_data)
    print(f"\nSaved {len(all_data)} products to {DATA_PATH}")


if __name__ == "__main__":
    main()
