from fastapi import FastAPI, Query
import requests
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Allow your frontend origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)
SCRYFALL_URL = "https://api.scryfall.com/cards/search"
SCRYFALL_SETS_URL = "https://api.scryfall.com/sets"


@app.get("/")
def read_root():
    return {"message": "Welcome to the MTG Deckbuilder API! Use /search to search for cards."}


@app.get("/sets")
async def get_sets():
    """Fetch all Magic: The Gathering sets from Scryfall API."""
    try:
        response = requests.get(SCRYFALL_SETS_URL)
        response.raise_for_status()
        data = response.json()

        if "data" in data:
            # Transform the data to the expected format
            sets = [{"code": set_data.get("code"), "name": set_data.get("name")}
                    for set_data in data.get("data", [])]
            return {"sets": sets}
        else:
            return {"error": "Unexpected response structure from Scryfall."}

    except requests.exceptions.RequestException as e:
        return {"error": f"An error occurred while fetching sets: {str(e)}"}


@app.get("/search")
async def search_cards(
        query: str = "",
        page: int = Query(1, ge=1),
        # Filter parameters
        mana_min: int = Query(0, ge=0),
        mana_max: int = Query(16, le=20),
        colors: Optional[str] = None,  # Comma-separated list of colors
        types: Optional[str] = None,  # Comma-separated list of types
        rarities: Optional[str] = None,  # Comma-separated list of rarities
        sets: Optional[str] = None,  # Comma-separated list of set codes
        power_value: Optional[int] = None,
        power_operator: Optional[str] = None,  # "equal", "greater", "less"
        toughness_value: Optional[int] = None,
        toughness_operator: Optional[str] = None  # "equal", "greater", "less"
):
    """
    Search for Magic: The Gathering cards with various filters.

    The filters are converted to Scryfall syntax and included in the query.
    """
    try:
        # Parse filter parameters
        color_list = colors.split(',') if colors else []
        type_list = types.split(',') if types else []
        rarity_list = rarities.split(',') if rarities else []
        set_list = sets.split(',') if sets else []

        # Build Scryfall query
        scryfall_query = query.strip()

        # Add mana cost filter
        if mana_min > 0 or mana_max < 16:
            if scryfall_query:
                scryfall_query += " "
            scryfall_query += f"cmc>={mana_min} cmc<={mana_max}"

        # Add color filter
        if color_list:
            color_query = "c:" + "".join(color_list)
            if scryfall_query:
                scryfall_query += " "
            scryfall_query += color_query

        # Add type filter
        for type_name in type_list:
            if scryfall_query:
                scryfall_query += " "
            scryfall_query += f"t:{type_name}"

        # Add rarity filter
        for rarity in rarity_list:
            if scryfall_query:
                scryfall_query += " "
            scryfall_query += f"r:{rarity}"

        # Add set filter
        for set_code in set_list:
            if scryfall_query:
                scryfall_query += " "
            scryfall_query += f"s:{set_code}"

        # Add power filter
        if power_value is not None and power_operator:
            operator_map = {"equal": "=", "greater": ">", "less": "<"}
            op = operator_map.get(power_operator, "=")
            if scryfall_query:
                scryfall_query += " "
            scryfall_query += f"pow{op}{power_value}"

        # Add toughness filter
        if toughness_value is not None and toughness_operator:
            operator_map = {"equal": "=", "greater": ">", "less": "<"}
            op = operator_map.get(toughness_operator, "=")
            if scryfall_query:
                scryfall_query += " "
            scryfall_query += f"tou{op}{toughness_value}"

        # If no query is provided and no filters are applied, return a default search
        if not scryfall_query:
            scryfall_query = "type:creature"  # Default search if no query/filters

        # Make the API request to Scryfall
        response = requests.get(
            SCRYFALL_URL,
            params={"q": scryfall_query, "page": page}
        )
        response.raise_for_status()
        data = response.json()

        if "data" in data:
            return {
                "cards": data["data"],
                "has_more": data.get("has_more", False),
                "next_page": page + 1 if data.get("has_more", False) else None,
                "total_cards": data.get("total_cards", 0),
                "applied_query": scryfall_query  # Return the query that was sent to Scryfall
            }
        else:
            return {"error": "Unexpected response structure from Scryfall."}

    except requests.exceptions.RequestException as e:
        return {"error": f"An error occurred while fetching data: {str(e)}"}