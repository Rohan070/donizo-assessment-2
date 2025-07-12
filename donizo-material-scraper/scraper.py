import os
import json
import yaml
import argparse
import random
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import re

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "scraper_config.yaml")
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "materials.json")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]


def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    }


def apply_stealth(page):
    page.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', { get: function () { return window; } });
        Object.defineProperty(screen, 'availTop', { get: () => 0 });
        Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
    """
    )


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_data(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def human_scroll(page):
    for _ in range(random.randint(3, 6)):
        page.mouse.wheel(0, random.randint(200, 1000))
        time.sleep(random.uniform(0.5, 1.5))


def discover_categories(base_url, container_selector):
    discovered = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent=random.choice(USER_AGENTS))
        page = context.new_page()
        apply_stealth(page)
        page.goto(base_url, timeout=45000)
        time.sleep(7)  # Cloudflare challenge pause
        human_scroll(page)
        page.wait_for_selector(container_selector, timeout=15000)
        soup = BeautifulSoup(page.content(), "html.parser")
        section = soup.select_one(container_selector)
        if section:
            for link in section.find_all("a", href=True):
                text = link.get_text(strip=True).lower()
                href = link["href"]
                if not href.startswith("http"):
                    href = base_url.rstrip("/") + href
                key = text.replace(" ", "_")
                suffix = 2
                while key in discovered:
                    key = f"{key}_{suffix}"
                    suffix += 1
                discovered[key] = href
                if len(discovered) >= 2:
                    break
        browser.close()
    return discovered


def open_castorama_menu(page):
    try:
        print("🕵️ Looking for menu button...")
        menu_btn = page.wait_for_selector(
            'button[data-test-id="menu-button-open"]', timeout=10000, state="attached"
        )

        # Try scrolling into view
        menu_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)

        # Make sure it's interactable
        menu_btn.wait_for_element_state("visible", timeout=5000)
        menu_btn.wait_for_element_state("enabled", timeout=5000)
        menu_btn.click(force=True)

        print("✅ Menu button clicked.")
        time.sleep(2)
        return True

    except Exception as e:
        print(f"❌ Failed to open menu: {e}")
        return False


def handle_castorama_cookie_banner(page):
    try:
        cookie_btn = page.query_selector(
            "button#truste-consent-button.trustarc-agree-btn"
        )
        if cookie_btn:
            print("🍪 Clicking Castorama cookie consent button...")
            cookie_btn.click()
            time.sleep(1)
    except Exception as e:
        print("No Castorama cookie consent button found or error:", e)


def handle_castorama_location_drawer(page):
    try:
        # Try to close the location/postal code drawer if it appears
        close_btn = page.query_selector(
            'button[data-test-id="location-drawer-close-button"]'
        )
        if close_btn:
            print("📍 Closing location/postal code drawer...")
            close_btn.click()
            time.sleep(1)
        # Sometimes there is a 'Continuer sans choisir' button
        continue_btn = page.query_selector(
            'button[data-test-id="location-drawer-continue-without"]'
        )
        if continue_btn:
            print("📍 Continuing without choosing location...")
            continue_btn.click()
            time.sleep(1)
        # Also close tooltip/location popup if present
        tooltip_btn = page.query_selector(
            'button[data-test-id="location-tool-tip-button"]'
        )
        if tooltip_btn:
            print("📍 Closing location tooltip popup...")
            tooltip_btn.click()
            time.sleep(1)
    except Exception as e:
        print("No location drawer to close or error:", e)


def discover_castorama_categories_with_paths(base_url):
    """
    Discover all category paths (primary, secondary, tertiary) and their product listing URLs from Castorama's homepage menu.
    For each primary: up to 2 secondaries; for each secondary: up to 2 tertiaries (without clicking them).
    Returns: dict with keys (primary, secondary, tertiary) and values as URLs.
    """
    from playwright.sync_api import (
        sync_playwright,
        TimeoutError as PlaywrightTimeoutError,
    )

    args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--disable-infobars",
        "--no-sandbox",
    ]

    discovered = {}
    headers = get_random_headers()

    # Limits for sampling
    MAX_SECONDARIES = 1  # Change here to increase number of secondaries
    MAX_TERTIARIES = 1  # Change here to increase number of tertiaries

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=400, args=args)
        context = browser.new_context(
            extra_http_headers=headers,
            user_agent=headers["User-Agent"],
        )
        page = context.new_page()

        page.goto(base_url, timeout=45000)
        handle_castorama_cookie_banner(page)
        handle_castorama_location_drawer(page)
        time.sleep(2)

        # Open main menu
        print("🕵️ Opening main menu...")
        menu_btn = page.wait_for_selector(
            'button[data-test-id="menu-button-open"]', timeout=15000, state="visible"
        )
        menu_btn.click()
        page.wait_for_selector('ol[id^="megaNav-list[1]"]', timeout=10000)
        print("✅ Main menu opened.")

        # Get all primary categories
        primary_ol = page.query_selector('ol[id^="megaNav-list[1]"]')
        if not primary_ol:
            print("❌ Primary category list not found!")
            browser.close()
            return discovered
        primary_lis = primary_ol.query_selector_all(
            'li > a[data-test-id^="category-menu-link "]'
        )
        # Limit to 2 main categories for now (can increase later)
        for primary_idx, primary_a in enumerate(
            primary_lis[:1]
        ):  # Only open one main category once
            try:
                primary_name = primary_a.inner_text().strip().split("\n")[0]
                print(f"➡️ Primary: {primary_name}")
                primary_a.click()
                # Wait for secondary drawer
                page.wait_for_selector(
                    'ol[data-test-id="subcategory-list-v2-level-2"]', timeout=7000
                )
                secondary_ol = page.query_selector(
                    'ol[data-test-id="subcategory-list-v2-level-2"]'
                )
                if not secondary_ol:
                    print(f"❌ No secondary for {primary_name}")
                    continue
                secondary_lis = secondary_ol.query_selector_all(
                    'li > a[data-test-id^="category-menu-link "]'
                )
                for secondary_idx, secondary_a in enumerate(
                    secondary_lis[:MAX_SECONDARIES]
                ):
                    try:
                        secondary_name = secondary_a.inner_text().strip().split("\n")[0]
                        print(f"  ↪️ Secondary: {secondary_name}")
                        url_before = page.url
                        secondary_a.click()
                        time.sleep(1)
                        url_after = page.url
                        if url_after != url_before:
                            print(
                                f"    [LEAF] {primary_name} > {secondary_name} (no tertiary)"
                            )
                            discovered[(primary_name, secondary_name, None)] = url_after
                            # Re-open menu for next secondary
                            menu_btn = page.query_selector(
                                'button[data-test-id="menu-button-open"]'
                            )
                            if menu_btn:
                                menu_btn.click()
                                page.wait_for_selector(
                                    'ol[id^="megaNav-list[1]"]', timeout=10000
                                )
                                primary_ol = page.query_selector(
                                    'ol[id^="megaNav-list[1]"]'
                                )
                                primary_lis = primary_ol.query_selector_all(
                                    'li > a[data-test-id^="category-menu-link "]'
                                )
                                primary_lis[primary_idx].click()
                                page.wait_for_selector(
                                    'ol[data-test-id="subcategory-list-v2-level-2"]',
                                    timeout=7000,
                                )
                                secondary_ol = page.query_selector(
                                    'ol[data-test-id="subcategory-list-v2-level-2"]'
                                )
                                secondary_lis = secondary_ol.query_selector_all(
                                    'li > a[data-test-id^="category-menu-link "]'
                                )
                            continue
                        # Otherwise, look for tertiary links (do NOT click them)
                        if page.query_selector(
                            'ol[data-test-id="subcategory-list-v2-level-3"]'
                        ):
                            tertiary_ol = page.query_selector(
                                'ol[data-test-id="subcategory-list-v2-level-3"]'
                            )
                            tertiary_lis = tertiary_ol.query_selector_all(
                                'li > a[data-test-id^="category-menu-link "]'
                            )
                            for tertiary_idx, tertiary_a in enumerate(
                                tertiary_lis[:MAX_TERTIARIES]
                            ):
                                tertiary_name = (
                                    tertiary_a.inner_text().strip().split("\n")[0]
                                )
                                tertiary_url = tertiary_a.get_attribute("href")
                                if tertiary_url and not tertiary_url.startswith("http"):
                                    tertiary_url = (
                                        "https://www.castorama.fr" + tertiary_url
                                    )
                                print(
                                    f"    ➡️ Tertiary: {tertiary_name} (URL: {tertiary_url})"
                                )
                                discovered[
                                    (primary_name, secondary_name, tertiary_name)
                                ] = tertiary_url
                        else:
                            print(
                                f"    [WARN] No tertiary for {primary_name} > {secondary_name}"
                            )
                        # Re-open menu for next secondary
                        menu_btn = page.query_selector(
                            'button[data-test-id="menu-button-open"]'
                        )
                        if menu_btn:
                            menu_btn.click()
                            page.wait_for_selector(
                                'ol[id^="megaNav-list[1]"]', timeout=10000
                            )
                            primary_ol = page.query_selector(
                                'ol[id^="megaNav-list[1]"]'
                            )
                            primary_lis = primary_ol.query_selector_all(
                                'li > a[data-test-id^="category-menu-link "]'
                            )
                            primary_lis[primary_idx].click()
                            page.wait_for_selector(
                                'ol[data-test-id="subcategory-list-v2-level-2"]',
                                timeout=7000,
                            )
                            secondary_ol = page.query_selector(
                                'ol[data-test-id="subcategory-list-v2-level-2"]'
                            )
                            secondary_lis = secondary_ol.query_selector_all(
                                'li > a[data-test-id^="category-menu-link "]'
                            )
                    except Exception as e:
                        print(f"⚠️ Error in secondary category loop: {e}")
                        # Try to re-open menu for next secondary
                        menu_btn = page.query_selector(
                            'button[data-test-id="menu-button-open"]'
                        )
                        if menu_btn:
                            menu_btn.click()
                            page.wait_for_selector(
                                'ol[id^="megaNav-list[1]"]', timeout=10000
                            )
                            primary_ol = page.query_selector(
                                'ol[id^="megaNav-list[1]"]'
                            )
                            primary_lis = primary_ol.query_selector_all(
                                'li > a[data-test-id^="category-menu-link "]'
                            )
                            primary_lis[primary_idx].click()
                            page.wait_for_selector(
                                'ol[data-test-id="subcategory-list-v2-level-2"]',
                                timeout=7000,
                            )
                            secondary_ol = page.query_selector(
                                'ol[data-test-id="subcategory-list-v2-level-2"]'
                            )
                            secondary_lis = secondary_ol.query_selector_all(
                                'li > a[data-test-id^="category-menu-link "]'
                            )
                # After all secondaries, re-open menu for next primary
                menu_btn = page.query_selector(
                    'button[data-test-id="menu-button-open"]'
                )
                if menu_btn:
                    menu_btn.click()
                    page.wait_for_selector('ol[id^="megaNav-list[1]"]', timeout=10000)
            except Exception as e:
                print(f"⚠️ Error in primary category loop: {e}")
                # Try to re-open menu for next primary
                menu_btn = page.query_selector(
                    'button[data-test-id="menu-button-open"]'
                )
                if menu_btn:
                    menu_btn.click()
                    page.wait_for_selector('ol[id^="megaNav-list[1]"]', timeout=10000)
        browser.close()
    return discovered


def scrape_category(supplier, category_key, category_url, selectors):
    results = []
    page_url = category_url
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, args=["--disable-blink-features=AutomationControlled"]
        )
        headers = get_random_headers()
        while True:
            context = browser.new_context(
                extra_http_headers=headers, user_agent=headers["User-Agent"]
            )
            page = context.new_page()
            if supplier["name"].lower() == "manomano":
                apply_stealth(page)

            page.goto(page_url, timeout=45000)
            page.wait_for_load_state("networkidle")  # important!
            time.sleep(10)  # Cloudflare wait
            human_scroll(page)
            try:
                page.wait_for_selector(selectors["product_selector"], timeout=15000)
                product_cards = page.query_selector_all(selectors["product_selector"])
                for card in product_cards:
                    # Name
                    name = (
                        (
                            card.query_selector(selectors["name_selector"])
                            .inner_text()
                            .strip()
                        )
                        if selectors.get("name_selector")
                        else None
                    )
                    # Price
                    price = (
                        (
                            card.query_selector(selectors["price_selector"])
                            .inner_text()
                            .strip()
                        )
                        if selectors.get("price_selector")
                        else None
                    )
                    if price:
                        price = re.sub(r"[\n\r\u00A0\xa0]+", "", price)
                        price = re.sub(r"\s+", " ", price).strip()
                    # URL
                    url = card.get_attribute("href") or ""
                    if url.startswith("/"):
                        url = supplier["base_url"] + url
                    # Brand
                    brand = None
                    if selectors.get("brand_selector") and card.query_selector(
                        selectors["brand_selector"]
                    ):
                        brand_el = card.query_selector(selectors["brand_selector"])
                        if supplier["name"].lower() == "manomano":
                            brand = brand_el.get_attribute("alt")
                        else:
                            brand = brand_el.inner_text().strip()
                    # Unit
                    unit = None
                    if supplier["name"].lower() == "manomano":
                        # Try to extract unit/pack size from name/title
                        unit_patterns = [
                            r"\b\d+\s?(cm|m|pcs|places|personnes|L|kg|ml|mm)\b",
                            r"\b(lot de|lot)\s*\d+",
                            r"\bx\s?\d+",
                            r"\b\d+\s?pi[eè]ces?\b",
                        ]
                        unit = None
                        if name:
                            for pat in unit_patterns:
                                match = re.search(pat, name, re.IGNORECASE)
                                if match:
                                    unit = match.group(0)
                                    break
                    elif selectors.get("unit_selector") and card.query_selector(
                        selectors["unit_selector"]
                    ):
                        unit = (
                            card.query_selector(selectors["unit_selector"])
                            .inner_text()
                            .strip()
                        )
                    # Image URL
                    image_url = (
                        (
                            card.query_selector(
                                selectors["image_selector"]
                            ).get_attribute("src")
                        )
                        if selectors.get("image_selector")
                        and card.query_selector(selectors["image_selector"])
                        else None
                    )
                    results.append(
                        {
                            "name": name,
                            "category": category_key,
                            "price": price,
                            "url": url,
                            "brand": brand,
                            "unit": unit,
                            "image_url": image_url,
                            "supplier": supplier["name"],
                            "category_primary": supplier.get("category_primary"),
                            "category_secondary": supplier.get("category_secondary"),
                            "category_tertiary": supplier.get("category_tertiary"),
                        }
                    )
                if len(results) >= 100:
                    context.close()
                    break
                next_button = page.query_selector('a[aria-label="Page suivante"]')
                if next_button and next_button.is_enabled():
                    next_href = next_button.get_attribute("href")
                    if next_href:
                        # Use full URL for next page
                        if next_href.startswith("http"):
                            page_url = next_href
                        else:
                            page_url = supplier["base_url"] + next_href
                        time.sleep(random.uniform(2, 4))
                        context.close()
                        continue
                context.close()
                break
            except Exception as e:
                print(f"Error scraping {category_key}: {e}")
                context.close()
                break
        browser.close()
    return results


SUPPLIER_FUNCS = {
    "manomano": {
        "discover": lambda url: discover_categories(url, "section.ec_tSD"),
        "scrape": scrape_category,
    },
    "castorama": {
        "discover": lambda url: discover_castorama_categories_with_paths(url),
        "scrape": scrape_category,
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--supplier", type=str, default="all")
    args = parser.parse_args()

    config = load_config()
    suppliers = [
        s
        for s in config["suppliers"]
        if args.supplier == "all" or s["name"].lower() == args.supplier.lower()
    ]
    all_data = []

    for supplier in suppliers:
        sname = supplier["name"].lower()
        funcs = SUPPLIER_FUNCS.get(sname)
        if not funcs:
            print(f"Skipping unsupported: {sname}")
            continue
        print(f"\n=== Scraping {supplier['name']} ===")
        discovered = funcs["discover"](supplier["base_url"])
        print("Discovered categories:", discovered)
        # Skip first category for manomano
        items = list(discovered.items())
        if sname == "manomano":
            items = items[1:]
        for cat_key, cat_url in items:
            # For Castorama, cat_key is a tuple (primary, secondary, tertiary)
            if sname == "castorama" and isinstance(cat_key, tuple):
                selectors = supplier["categories"].get(
                    "tiles"
                )  # fallback or use logic to map
                results = funcs["scrape"](
                    {
                        "name": supplier["name"],
                        "base_url": supplier["base_url"],
                        "category_primary": cat_key[0],
                        "category_secondary": cat_key[1],
                        "category_tertiary": cat_key[2],
                    },
                    cat_key,
                    cat_url,
                    selectors,
                )
                all_data.extend(results)
            else:
                selectors = supplier["categories"].get(cat_key) or supplier[
                    "categories"
                ].get("tiles")
                results = funcs["scrape"](
                    {
                        "name": supplier["name"],
                        "base_url": supplier["base_url"],
                    },
                    cat_key,
                    cat_url,
                    selectors,
                )
                all_data.extend(results)

    save_data(all_data)
    print(f"\nSaved {len(all_data)} products to {DATA_PATH}")


if __name__ == "__main__":
    main()
