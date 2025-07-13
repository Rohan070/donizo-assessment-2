import os
import json
import subprocess
import time
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


def test_scraper_runs_and_outputs_data():
    # Do NOT delete materials.json
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "materials.json"
    )

    # Run the scraper for Castorama (limit to 1 category for speed)
    result = subprocess.run(
        ["python", "-m", "scrapers.main", "--supplier", "castorama"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Scraper failed: {result.stderr}"

    # Wait a moment for file write
    time.sleep(2)
    assert os.path.exists(data_path), "materials.json was not created"

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list), "Output is not a list"
    assert len(data) > 0, "No products scraped"

    # Check required fields in at least one product
    required_fields = ["name", "category", "price", "url", "supplier"]
    found = False
    for item in data:
        if all(field in item for field in required_fields):
            found = True
            break
    assert found, f"No product contains all required fields: {required_fields}"
