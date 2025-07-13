import argparse
import os

from scrapers.helpers import (
    load_config,
    load_env,
    save_data,
    get_data_path,
)
from scrapers.castorama import discover_castorama_categories_with_paths
from scrapers.manomano import discover_manomano_categories
from scrapers.common import scrape_category


def main():
    # Load environment variables
    load_env()

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
        print(f"\n=== Scraping {supplier['name']} ===")

        # Discover categories
        if sname == "castorama":
            discovered = discover_castorama_categories_with_paths(supplier["base_url"])
            CATEGORY_LIMIT = int(os.getenv("CASTORAMA_CATEGORY_LIMIT", 2))
        elif sname == "manomano":
            discovered = discover_manomano_categories(
                supplier["base_url"], "section.ec_tSD"
            )
            CATEGORY_LIMIT = int(os.getenv("MANOMANO_CATEGORY_LIMIT", 2))
        else:
            print(f"Skipping unsupported: {sname}")
            continue

        print("Discovered categories:", discovered)
        items = list(discovered.items())
        if sname == "manomano":
            items = items[1:]  # skip first category if needed

        for i, (cat_key, cat_url) in enumerate(items):
            if i >= CATEGORY_LIMIT:
                break
            # For Castorama, cat_key is a tuple (primary, secondary, tertiary)
            if sname == "castorama" and isinstance(cat_key, tuple):
                selectors = supplier["categories"].get("tiles")
                results = scrape_category(
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
                results = scrape_category(
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
    print(f"\nSaved {len(all_data)} products to {get_data_path()}")


if __name__ == "__main__":
    main()
