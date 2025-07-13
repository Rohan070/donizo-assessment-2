import os
import re
import random
import time
from playwright.sync_api import sync_playwright
from scrapers.helpers import get_random_headers, human_scroll, apply_stealth


def scrape_category(supplier, category_key, category_url, selectors):
    results = []
    page_url = category_url
    supplier_name = supplier["name"].lower()
    if supplier_name == "castorama":
        PRODUCT_LIMIT = int(os.getenv("CASTORAMA_PRODUCT_LIMIT", 100))
        PAGE_LIMIT = int(os.getenv("CASTORAMA_PAGE_LIMIT", 10))
    elif supplier_name == "manomano":
        PRODUCT_LIMIT = int(os.getenv("MANOMANO_PRODUCT_LIMIT", 100))
        PAGE_LIMIT = int(os.getenv("MANOMANO_PAGE_LIMIT", 10))
    else:
        PRODUCT_LIMIT = 100
        PAGE_LIMIT = 10
    page_count = 0
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
            time.sleep(10)  # Cloudflare wait
            if supplier["name"].lower() == "castorama":
                from scrapers.castorama import handle_castorama_location_drawer

                handle_castorama_location_drawer(page)
                time.sleep(2)
            human_scroll(page)
            try:
                page.wait_for_selector(selectors["product_selector"], timeout=15000)
                product_cards = page.query_selector_all(selectors["product_selector"])
                print(f"Found {len(product_cards)} products")
                for card in product_cards:
                    name = (
                        (
                            card.query_selector(selectors["name_selector"])
                            .inner_text()
                            .strip()
                        )
                        if selectors.get("name_selector")
                        else None
                    )
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
                    url = card.get_attribute("href") or ""
                    if url.startswith("/"):
                        url = supplier["base_url"] + url
                    brand = None
                    if selectors.get("brand_selector") and card.query_selector(
                        selectors["brand_selector"]
                    ):
                        brand_el = card.query_selector(selectors["brand_selector"])
                        if supplier["name"].lower() == "manomano":
                            brand = brand_el.get_attribute("alt")
                        else:
                            brand = brand_el.inner_text().strip()
                    else:
                        if supplier["name"].lower() == "castorama" and name:
                            generic_words = [
                                "plastique",
                                "bois",
                                "acier",
                                "métal",
                                "metal",
                                "verre",
                                "alu",
                                "aluminium",
                                "inox",
                                "pvc",
                                "cuivre",
                                "laiton",
                                "béton",
                                "beton",
                                "céramique",
                                "ceramique",
                                "résine",
                                "resine",
                                "polypropylène",
                                "polypropylene",
                                "polyéthylène",
                                "polyethylene",
                                "caoutchouc",
                                "papier",
                                "carton",
                                "tissu",
                                "coton",
                                "laine",
                                "soie",
                                "nylon",
                                "polyester",
                                "polyamide",
                                "polyuréthane",
                                "polyurethane",
                                "liège",
                                "bambou",
                                "osier",
                                "rotin",
                                "chanvre",
                                "jute",
                                "lin",
                                "sisal",
                                "coco",
                                "peau",
                                "cuir",
                                "fourrure",
                                "laqué",
                                "laque",
                                "émaillé",
                                "emaille",
                                "fonte",
                                "granit",
                                "marbre",
                                "pierre",
                                "ardoise",
                                "terre",
                                "terre-cuite",
                                "terre cuite",
                                "porcelaine",
                                "argile",
                                "silicone",
                                "graphite",
                                "carbone",
                                "chrome",
                                "zinc",
                                "titane",
                                "plomb",
                                "argent",
                                "or",
                                "bronze",
                                "étain",
                                "etain",
                                "plastics",
                                "wood",
                                "steel",
                                "glass",
                                "iron",
                                "copper",
                                "brass",
                                "concrete",
                                "ceramic",
                                "resin",
                                "rubber",
                                "paper",
                                "cardboard",
                                "fabric",
                                "cotton",
                                "wool",
                                "silk",
                                "nylon",
                                "polyester",
                                "polyamide",
                                "polyurethane",
                                "cork",
                                "bamboo",
                                "rattan",
                                "hemp",
                                "jute",
                                "linen",
                                "sisal",
                                "coconut",
                                "skin",
                                "leather",
                                "fur",
                                "lacquered",
                                "enameled",
                                "cast",
                                "granite",
                                "marble",
                                "stone",
                                "slate",
                                "clay",
                                "porcelain",
                                "silicon",
                                "graphite",
                                "carbon",
                                "chrome",
                                "zinc",
                                "titanium",
                                "lead",
                                "silver",
                                "gold",
                                "bronze",
                                "tin",
                            ]
                            first_word = name.split()[0].lower()
                            if first_word not in generic_words:
                                brand = name.split()[0]
                            else:
                                brand = None
                    unit = None
                    if supplier["name"].lower() == "manomano":
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
                    if len(results) >= PRODUCT_LIMIT:
                        context.close()
                        browser.close()
                        return results
                page_count += 1
                if page_count >= PAGE_LIMIT:
                    context.close()
                    break
                next_button = page.query_selector('a[aria-label="Page suivante"]')
                if next_button and next_button.is_enabled():
                    next_href = next_button.get_attribute("href")
                    if next_href:
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
