# Donizo Material Scraper

## Overview
A robust, modular Python scraper to extract renovation material pricing data from major French suppliers (Leroy Merlin, Castorama, ManoMano) for Donizo’s pricing engine. Handles multiple categories, pagination, product variations, and outputs developer-friendly JSON.

## Project Structure
```
donizo-material-scraper/
├── scraper.py
├── config/
│   └── scraper_config.yaml
├── data/
│   └── materials.json
├── tests/
│   └── test_scraper.py
└── README.md
```

## Features
- Scrapes 100+ products across multiple categories (tiles, sinks, toilets, paint, vanities, showers)
- Handles pagination/infinite scroll
- Extracts product variations/grouped listings
- Modular config for categories/sites
- Output: JSON (developer- and product-friendly)
- Anti-bot logic (headers, delays, Selenium/Playwright)
- **Bonus:** API simulation, multi-supplier comparison, vector DB-ready output

## How to Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure categories/sites in `config/scraper_config.yaml`
3. Run the scraper:
   ```bash
   python scraper.py
   ```
4. Output saved to `data/materials.json`

## Output Format
Each product is a JSON object with:
- `name`: Product name
- `category`: Category (e.g., tiles)
- `price`: Price (with currency)
- `url`: Product URL
- `brand`: Brand (if available)
- `unit`: Measurement unit or pack size
- `image_url`: Screenshot or photo URL (if available)
- `supplier`: Supplier name

Example:
```json
{
  "name": "Carrelage sol gris",
  "category": "tiles",
  "price": "19.99 €",
  "url": "https://www.leroymerlin.fr/produit/123",
  "brand": "Artens",
  "unit": "m²",
  "image_url": "https://...jpg",
  "supplier": "Leroy Merlin"
}
```

## Assumptions & Transformations
- Prices are scraped as displayed (may include currency symbol)
- Categories mapped to config names
- Product variations are flattened as separate entries
- Only public product data is scraped

## Pagination & Anti-bot Handling
- Handles next-page buttons, infinite scroll, or load-more
- Uses user-agent rotation, delays, and Selenium/Playwright for dynamic content

## Bonus Features (Elite)
- **API Simulation:** Run `python scraper.py --api` to start a FastAPI server with `/materials/{category}` endpoint
- **Multi-supplier Comparison:** Scrapes and compares prices for same category across suppliers
- **Vector DB Ready:** Output structured for ingestion into vector DBs

## Tests
Run tests with:
```bash
pytest tests/
```

---