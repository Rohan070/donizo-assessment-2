import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from scrapers.helpers import human_scroll, get_random_headers
import os


def open_castorama_menu(page):
    try:
        print("🕵️ Looking for menu button...")
        menu_btn = page.wait_for_selector(
            'button[data-test-id="menu-button-open"]', timeout=10000, state="attached"
        )
        menu_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
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
        close_btn = page.query_selector(
            'button[data-test-id="location-drawer-close-button"]'
        )
        if close_btn:
            print("📍 Closing location/postal code drawer...")
            close_btn.click()
            time.sleep(1)
        continue_btn = page.query_selector(
            'button[data-test-id="location-drawer-continue-without"]'
        )
        if continue_btn:
            print("📍 Continuing without choosing location...")
            continue_btn.click()
            time.sleep(1)
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
    MAX_PRIMARIES = int(os.getenv("CASTORAMA_PRIMARY_LIMIT", 2))
    MAX_SECONDARIES = int(os.getenv("CASTORAMA_SECONDARY_LIMIT", 2))
    MAX_TERTIARIES = int(os.getenv("CASTORAMA_TERTIARY_LIMIT", 2))
    args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--disable-infobars",
        "--no-sandbox",
    ]
    discovered = {}
    headers = get_random_headers()
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
        print("🕵️ Opening main menu...")
        menu_btn = page.wait_for_selector(
            'button[data-test-id="menu-button-open"]', timeout=15000, state="visible"
        )
        menu_btn.click()
        page.wait_for_selector('ol[id^="megaNav-list[1]"]', timeout=10000)
        print("✅ Main menu opened.")
        primary_ol = page.query_selector('ol[id^="megaNav-list[1]"]')
        if not primary_ol:
            print("❌ Primary category list not found!")
            browser.close()
            return discovered
        primary_lis = primary_ol.query_selector_all(
            'li > a[data-test-id^="category-menu-link "]'
        )
        for primary_idx, primary_a in enumerate(primary_lis[:MAX_PRIMARIES]):
            try:
                primary_name = primary_a.inner_text().strip().split("\n")[0]
                print(f"➡️ Primary: {primary_name}")
                primary_a.click()
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
                menu_btn = page.query_selector(
                    'button[data-test-id="menu-button-open"]'
                )
                if menu_btn:
                    menu_btn.click()
                    page.wait_for_selector('ol[id^="megaNav-list[1]"]', timeout=10000)
            except Exception as e:
                print(f"⚠️ Error in primary category loop: {e}")
                menu_btn = page.query_selector(
                    'button[data-test-id="menu-button-open"]'
                )
                if menu_btn:
                    menu_btn.click()
                    page.wait_for_selector('ol[id^="megaNav-list[1]"]', timeout=10000)
        browser.close()
    return discovered
