import os
import json
import random
import yaml
import time
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]

DATA_PATH = os.path.join(BASE_DIR, "data", "materials.json")


def get_user_agents():
    return USER_AGENTS


def get_data_path():
    return DATA_PATH


def load_env():
    """Load environment variables from .env file in config directory (idempotent)."""
    env_path = os.path.join(BASE_DIR, "config", ".env")
    if not getattr(load_env, "_loaded", False):
        load_dotenv(env_path)
        load_env._loaded = True


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
    CONFIG_PATH = os.path.join(BASE_DIR, "config", "scraper_config.yaml")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_data(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    # Try to load existing data
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []
    else:
        existing = []
    # Avoid duplicates by url
    existing_urls = {
        item.get("url") for item in existing if isinstance(item, dict) and "url" in item
    }
    new_data = [
        item
        for item in data
        if isinstance(item, dict) and item.get("url") not in existing_urls
    ]
    all_data = existing + new_data
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)


def human_scroll(page):
    for _ in range(random.randint(3, 6)):
        page.mouse.wheel(0, random.randint(200, 1000))
        time.sleep(random.uniform(0.5, 1.5))
