from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
import json

app = FastAPI()

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "materials.json"
)

print(DATA_PATH)


@app.get("/")
def root():
    return {
        "message": "Welcome to the Donizo Materials API. Use /materials/{category} to query products."
    }


@app.get("/materials/{category}")
def get_materials_by_category(category: str):
    if not os.path.exists(DATA_PATH):
        return JSONResponse(
            status_code=404, content={"error": "materials.json not found"}
        )
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    category_lower = category.lower()
    results = []
    for item in data:
        # Check main category field (can be list or str)
        cat = item.get("category", "")
        if isinstance(cat, list):
            if any(category_lower in str(c).lower() for c in cat):
                results.append(item)
                continue
        elif category_lower in str(cat).lower():
            results.append(item)
            continue
        # Check primary/secondary/tertiary
        for key in ["category_primary", "category_secondary", "category_tertiary"]:
            val = item.get(key, "")
            if val and category_lower in str(val).lower():
                results.append(item)
                break
    return results
