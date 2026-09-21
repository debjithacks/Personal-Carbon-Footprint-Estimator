"""
Deterministic carbon-footprint calculation engine.

Responsibilities:
- Load all numeric emission factors from data/emission_factors.json.
- Validate quantitative user inputs.
- Calculate annual CO2e for transport, electricity, diet, and waste.
- Return a typed category-level and total result.
- Keep AI completely outside the numerical calculation path.

Important:
The calculation engine must never hardcode emission factors. The JSON
configuration is the single source of truth for numeric factors.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FACTORS_FILE = PROJECT_ROOT / "data" / "emission_factors.json"

DAYS_PER_YEAR = 365
MONTHS_PER_YEAR = 12
KG_PER_TONNE = 1_000

SUPPORTED_TRANSPORT_MODES = frozenset(
    {"walking", "cycling", "bus", "two_wheeler", "car"}
)
SUPPORTED_TWO_WHEELER_TYPES = frozenset({"standard", "premium"})
SUPPORTED_CAR_CATEGORIES = frozenset(
    {"small", "hatchback", "sedan", "suv", "hybrid", "electric"}
)
SUPPORTED_CAR_FUELS = frozenset({"petrol", "diesel", "cng"})
SUPPORTED_FUEL_OPTIONS_BY_CAR_CATEGORY = {
    "small": frozenset({"petrol", "cng"}),
    "hatchback": frozenset({"petrol", "diesel"}),
    "sedan": frozenset({"petrol", "diesel"}),
    "suv": frozenset({"petrol", "diesel"}),
}
SUPPORTED_RECYCLING_HABITS = frozenset(
    {"rarely", "sometimes", "consistently"}
)


class CarbonCalculationError(ValueError):
    """Raised when carbon-calculation inputs or configuration are invalid."""


@dataclass(frozen=True)
class CarbonInput:
    """Validated user-facing inputs used by the calculation engine.

    shopping_habit is retained as contextual input for the AI recommendation
    layer but intentionally does not contribute to the numeric CO2e total.
    Household electricity and waste are allocated equally across household
    members using household_size.
    """

    transport_mode: str
    distance_km_per_day: float

    car_category: str | None = None
    car_fuel: str | None = None
    two_wheeler_type: str | None = None

    electricity_kwh_per_month: float = 0.0
    household_size: int = 1
    diet_category: str = "vegetarian"
    waste_kg_per_day: float = 0.0
    recycling_habit: str = "rarely"
    shopping_habit: str = "buys_occasionally"


@dataclass(frozen=True)
class CategoryResult:
    """Annual result for one quantitative footprint category."""

    kg_co2e: float
    percentage: float


@dataclass(frozen=True)
class CarbonResult:
    """Complete annual carbon-footprint result."""

    total_kg_co2e: float
    total_tonnes_co2e: float

    transport: CategoryResult
    electricity: CategoryResult
    diet: CategoryResult
    waste: CategoryResult

    shopping_included: bool
    classification: str


def load_emission_factors(
    factors_file: Path = FACTORS_FILE,
) -> dict[str, Any]:
    """Load the emission-factor configuration.

    Raises:
        CarbonCalculationError: If the file is missing, invalid JSON, or does
            not contain a JSON object at the top level.
    """
    if not factors_file.exists():
        raise CarbonCalculationError(
            f"Emission factor file not found: {factors_file}"
        )

    if not factors_file.is_file():
        raise CarbonCalculationError(
            f"Emission factor path is not a file: {factors_file}"
        )

    try:
        with factors_file.open("r", encoding="utf-8") as file:
            factors = json.load(file)
    except json.JSONDecodeError as exc:
        raise CarbonCalculationError(
            f"Invalid JSON in emission factor file: {factors_file}"
        ) from exc
    except OSError as exc:
        raise CarbonCalculationError(
            f"Unable to read emission factor file: {factors_file}"
        ) from exc

    if not isinstance(factors, dict):
        raise CarbonCalculationError(
            "Emission factor configuration must contain a JSON object."
        )

    return factors


def _require_finite_non_negative(value: float, field_name: str) -> None:
    """Require a real, finite, non-negative numeric value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CarbonCalculationError(
            f"{field_name} must be a numeric value."
        )

    numeric_value = float(value)

    if not math.isfinite(numeric_value):
        raise CarbonCalculationError(
            f"{field_name} must be finite."
        )

    if numeric_value < 0:
        raise CarbonCalculationError(
            f"{field_name} cannot be negative."
        )


def _get_factor(
    factors: dict[str, Any],
    *path: str,
) -> float:
    """Safely retrieve a numeric factor from the configuration."""
    current: Any = factors

    try:
        for key in path:
            current = current[key]
        value = current["value"]
    except (KeyError, TypeError) as exc:
        location = ".".join(path)
        raise CarbonCalculationError(
            f"Missing emission factor configuration: {location}"
        ) from exc

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        location = ".".join(path)
        raise CarbonCalculationError(
            f"Emission factor at {location} must be numeric."
        )

    value = float(value)

    if not math.isfinite(value) or value < 0:
        location = ".".join(path)
        raise CarbonCalculationError(
            f"Emission factor at {location} must be finite and non-negative."
        )

    return value


def calculate_transport(
    user_input: CarbonInput,
    factors: dict[str, Any],
) -> float:
    """Calculate annual transport CO2e in kilograms.

    Formula:
        daily distance × emission factor × 365
    """
    _require_finite_non_negative(
        user_input.distance_km_per_day,
        "distance_km_per_day",
    )

    mode = user_input.transport_mode

    if mode not in SUPPORTED_TRANSPORT_MODES:
        raise CarbonCalculationError(
            f"Unsupported transport mode: {mode}"
        )

    if mode in {"walking", "cycling"}:
        factor = _get_factor(factors, "transport", "modes", mode)

    elif mode == "bus":
        factor = _get_factor(factors, "transport", "modes", "bus")

    elif mode == "two_wheeler":
        two_wheeler_type = user_input.two_wheeler_type

        if two_wheeler_type not in SUPPORTED_TWO_WHEELER_TYPES:
            raise CarbonCalculationError(
                "two_wheeler_type must be 'standard' or 'premium'."
            )

        factor = _get_factor(
            factors,
            "transport",
            "modes",
            f"two_wheeler_{two_wheeler_type}",
        )

    else:
        car_category = user_input.car_category

        if car_category not in SUPPORTED_CAR_CATEGORIES:
            raise CarbonCalculationError(
                "Invalid car_category."
            )

        if car_category in {"hybrid", "electric"}:
            if user_input.car_fuel is not None:
                raise CarbonCalculationError(
                    f"{car_category} cars do not accept a separate fuel selection."
                )

            factor_key = f"car_{car_category}"

            if car_category == "electric":
                energy_kwh_per_km = _get_factor(
                    factors,
                    "transport",
                    "modes",
                    factor_key,
                )
                grid_factor = _get_factor(
                    factors,
                    "electricity",
                    "grid_average",
                )
                return (
                    float(user_input.distance_km_per_day)
                    * energy_kwh_per_km
                    * grid_factor
                    * DAYS_PER_YEAR
                )

            factor = _get_factor(
                factors,
                "transport",
                "modes",
                factor_key,
            )
        else:
            allowed_fuels = SUPPORTED_FUEL_OPTIONS_BY_CAR_CATEGORY.get(
                car_category,
                frozenset(),
            )

            if user_input.car_fuel not in SUPPORTED_CAR_FUELS:
                raise CarbonCalculationError(
                    "car_fuel must be 'petrol', 'diesel', or 'cng'."
                )

            if user_input.car_fuel not in allowed_fuels:
                raise CarbonCalculationError(
                    f"Fuel '{user_input.car_fuel}' is not supported for "
                    f"car category '{car_category}'."
                )

            factor_key = f"car_{car_category}_{user_input.car_fuel}"
            factor = _get_factor(
                factors,
                "transport",
                "modes",
                factor_key,
            )

    return float(user_input.distance_km_per_day) * factor * DAYS_PER_YEAR


def _require_positive_household_size(value: int) -> int:
    """Validate and return a positive household member count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise CarbonCalculationError(
            "household_size must be a positive integer."
        )

    if value <= 0:
        raise CarbonCalculationError(
            "household_size must be greater than zero."
        )

    return value


def calculate_electricity(
    user_input: CarbonInput,
    factors: dict[str, Any],
) -> float:
    """Calculate this person's annual share of household electricity CO2e.

    Formula:
        (household monthly kWh ÷ household size) × 12 × kg CO2e/kWh

    The estimator uses an equal-share allocation because no individual-level
    electricity metering is requested.
    """
    _require_finite_non_negative(
        user_input.electricity_kwh_per_month,
        "electricity_kwh_per_month",
    )
    household_size = _require_positive_household_size(
        user_input.household_size
    )

    factor = _get_factor(
        factors,
        "electricity",
        "grid_average",
    )

    personal_monthly_kwh = (
        float(user_input.electricity_kwh_per_month) / household_size
    )

    return personal_monthly_kwh * MONTHS_PER_YEAR * factor


def calculate_diet(
    user_input: CarbonInput,
    factors: dict[str, Any],
) -> float:
    """Calculate annual diet-related CO2e in kilograms."""
    category = user_input.diet_category

    try:
        categories = factors["diet"]["categories"]
    except (KeyError, TypeError) as exc:
        raise CarbonCalculationError(
            "Diet category configuration is missing."
        ) from exc

    if not isinstance(categories, dict) or category not in categories:
        raise CarbonCalculationError(
            f"Unsupported diet category: {category}"
        )

    daily_factor = _get_factor(
        factors,
        "diet",
        "categories",
        category,
    )

    return daily_factor * DAYS_PER_YEAR


def calculate_waste(
    user_input: CarbonInput,
    factors: dict[str, Any],
) -> float:
    """Calculate annual waste-related CO2e in kilograms.

    The methodology defines one explicit numeric recycling assumption:
    consistent recycling applies a 50% reduction. No numeric reduction is
    invented for "rarely" or "sometimes".
    """
    _require_finite_non_negative(
        user_input.waste_kg_per_day,
        "waste_kg_per_day",
    )

    recycling_habit = user_input.recycling_habit

    if recycling_habit not in SUPPORTED_RECYCLING_HABITS:
        raise CarbonCalculationError(
            "recycling_habit must be 'rarely', 'sometimes', "
            "or 'consistently'."
        )

    household_size = _require_positive_household_size(
        user_input.household_size
    )

    base_factor = _get_factor(
        factors,
        "waste",
        "base_factor",
    )

    personal_waste_kg_per_day = (
        float(user_input.waste_kg_per_day) / household_size
    )

    annual_waste_emissions = (
        personal_waste_kg_per_day
        * base_factor
        * DAYS_PER_YEAR
    )

    if recycling_habit == "consistently":
        reduction = _get_factor(
            factors,
            "waste",
            "recycling_reduction",
        )
        annual_waste_emissions *= 1 - reduction

    return annual_waste_emissions


def classify_footprint(total_kg_co2e: float) -> str:
    """Apply the project's documented Low/Medium/High classification.

    These thresholds are application-level assumptions, not universal
    scientific thresholds:
        < 2,000 kg/year  -> Low
        2,000–4,000      -> Medium
        > 4,000          -> High
    """
    _require_finite_non_negative(total_kg_co2e, "total_kg_co2e")

    if total_kg_co2e < 2_000:
        return "Low"

    if total_kg_co2e <= 4_000:
        return "Medium"

    return "High"


def calculate_carbon_footprint(
    user_input: CarbonInput,
    factors: dict[str, Any] | None = None,
) -> CarbonResult:
    """Calculate the complete annual lifestyle CO2e estimate.

    Shopping is intentionally excluded from the numerical calculation and
    remains available as context for the Granite recommendation layer.
    Household electricity and waste are converted to a per-person share using
    an equal-share household allocation.
    """
    if factors is None:
        factors = load_emission_factors()

    transport_kg = calculate_transport(user_input, factors)
    electricity_kg = calculate_electricity(user_input, factors)
    diet_kg = calculate_diet(user_input, factors)
    waste_kg = calculate_waste(user_input, factors)

    total_kg = (
        transport_kg
        + electricity_kg
        + diet_kg
        + waste_kg
    )

    total_tonnes = total_kg / KG_PER_TONNE
    classification = classify_footprint(total_kg)

    def percentage(value: float) -> float:
        if total_kg == 0:
            return 0.0
        return (value / total_kg) * 100

    return CarbonResult(
        total_kg_co2e=round(total_kg, 2),
        total_tonnes_co2e=round(total_tonnes, 3),
        transport=CategoryResult(
            kg_co2e=round(transport_kg, 2),
            percentage=round(percentage(transport_kg), 2),
        ),
        electricity=CategoryResult(
            kg_co2e=round(electricity_kg, 2),
            percentage=round(percentage(electricity_kg), 2),
        ),
        diet=CategoryResult(
            kg_co2e=round(diet_kg, 2),
            percentage=round(percentage(diet_kg), 2),
        ),
        waste=CategoryResult(
            kg_co2e=round(waste_kg, 2),
            percentage=round(percentage(waste_kg), 2),
        ),
        shopping_included=False,
        classification=classification,
    )
