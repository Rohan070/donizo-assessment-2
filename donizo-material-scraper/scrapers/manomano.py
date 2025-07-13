"""
manomano.py
ManoMano-specific scraping logic and helpers.
"""

import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from scrapers.helpers import human_scroll, get_random_headers, apply_stealth
import random
import os


def discover_manomano_categories(base_url, container_selector):
    discovered = {}
    USER_AGENTS = get_random_headers()["User-Agent"]
    # Get category limit from env or config
    category_limit = int(os.environ.get("MANOMANO_CATEGORY_LIMIT", 5))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent=USER_AGENTS)
        page = context.new_page()
        # Apply stealth for ManoMano (as in original logic)
        apply_stealth(page)
        page.goto(base_url, timeout=45000)
        time.sleep(7)
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
                if len(discovered) >= category_limit:
                    break
        browser.close()
    return discovered
