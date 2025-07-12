import os
import json
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "materials.json")
CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "scraper_config.yaml"
)


def test_config_loadable():
    import yaml

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    assert "suppliers" in config
    assert isinstance(config["suppliers"], list)


def test_output_format():
    if not os.path.exists(DATA_PATH):
        pytest.skip("No data file yet")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        assert "name" in item
        assert "category" in item
        assert "price" in item
        assert "url" in item
        assert "supplier" in item
