"""Application constants.

UI labels and application configuration belong here.

Important:
Numeric emission factors must NOT be stored here.
They belong exclusively in data/emission_factors.json.
"""

APP_TITLE = "Personal Carbon Footprint Estimator"
APP_ICON = None


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------

TRANSPORT_OPTIONS = {
    "Walking": "walking",
    "Cycling": "cycling",
    "Bus": "bus",
    "Two-wheeler": "two_wheeler",
    "Car": "car",
}

TWO_WHEELER_OPTIONS = {
    "Standard (scooter / lower engine capacity)": "standard",
    "Premium (motorcycle / higher engine capacity)": "premium",
}

CAR_CATEGORY_OPTIONS = {
    "Small car": "small",
    "Hatchback": "hatchback",
    "Sedan": "sedan",
    "SUV": "suv",
    "Hybrid": "hybrid",
    "Electric car": "electric",
}

CAR_FUEL_OPTIONS_BY_CATEGORY = {
    "small": {
        "Petrol": "petrol",
        "CNG": "cng",
    },
    "hatchback": {
        "Petrol": "petrol",
        "Diesel": "diesel",
    },
    "sedan": {
        "Petrol": "petrol",
        "Diesel": "diesel",
    },
    "suv": {
        "Petrol": "petrol",
        "Diesel": "diesel",
    },
}


# ---------------------------------------------------------------------------
# Lifestyle categories
# ---------------------------------------------------------------------------

DIET_OPTIONS = {
    "High meat": "high_meat",
    "Medium meat": "medium_meat",
    "Low meat": "low_meat",
    "Pescatarian": "pescatarian",
    "Vegetarian": "vegetarian",
    "Vegan": "vegan",
}

RECYCLING_OPTIONS = {
    "Rarely": "rarely",
    "Sometimes": "sometimes",
    "Consistently": "consistently",
}

SHOPPING_OPTIONS = {
    "Rarely buys new items": "rarely_buys_new_items",
    "Buys occasionally": "buys_occasionally",
    "Buys frequently": "buys_frequently",
}


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

CLASSIFICATION_LABELS = (
    "Low",
    "Medium",
    "High",
)


# ---------------------------------------------------------------------------
# Transparency / methodology
# ---------------------------------------------------------------------------

FOOTPRINT_DISCLOSURE = (
    "Indicative estimate based on published emission factors, documented "
    "proxies, and stated assumptions. It is not a complete life-cycle "
    "assessment. Household electricity and waste are allocated equally across "
    "household members. EV transport uses a BEE-reported vehicle energy proxy "
    "multiplied by the CEA grid factor; charging losses are not separately modeled."
)

CLASSIFICATION_DISCLOSURE = (
    "Low / Medium / High is a project-defined classification and is not "
    "presented as a universal scientific threshold."
)


# ---------------------------------------------------------------------------
# IBM Granite
# ---------------------------------------------------------------------------

GRANITE_DEFAULT_MODEL_ID = "ibm/granite-3-2-8b-instruct"

GRANITE_DEFAULT_URL = (
    "https://us-south.ml.cloud.ibm.com"
)

GRANITE_DEFAULT_MAX_NEW_TOKENS = 220

GRANITE_DEFAULT_TEMPERATURE = 0.2