import json

import pytest

from services.carbon_calculator import (
    CarbonCalculationError,
    CarbonInput,
    calculate_carbon_footprint,
    classify_footprint,
    load_emission_factors,
)


@pytest.fixture
def factors():
    return load_emission_factors()


def make_user(**overrides):
    defaults = {
        "transport_mode": "walking",
        "distance_km_per_day": 0,
        "electricity_kwh_per_month": 0,
        "diet_category": "vegan",
        "waste_kg_per_day": 0,
        "recycling_habit": "rarely",
    }
    defaults.update(overrides)
    return CarbonInput(**defaults)


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mode", "expected_factor"),
    [
        ("walking", 0.0),
        ("cycling", 0.0),
        ("bus", 0.015161),
    ],
)
def test_transport_basic_modes(factors, mode, expected_factor):
    result = calculate_carbon_footprint(
        make_user(
            transport_mode=mode,
            distance_km_per_day=10,
        ),
        factors,
    )

    assert result.transport.kg_co2e == pytest.approx(
        10 * expected_factor * 365,
        abs=0.01,
    )


@pytest.mark.parametrize(
    ("two_wheeler_type", "expected_factor"),
    [
        ("standard", 0.0387),
        ("premium", 0.0458),
    ],
)
def test_two_wheeler_modes(factors, two_wheeler_type, expected_factor):
    result = calculate_carbon_footprint(
        make_user(
            transport_mode="two_wheeler",
            distance_km_per_day=10,
            two_wheeler_type=two_wheeler_type,
        ),
        factors,
    )

    assert result.transport.kg_co2e == pytest.approx(
        10 * expected_factor * 365,
        abs=0.01,
    )


@pytest.mark.parametrize(
    ("category", "fuel", "expected_factor"),
    [
        ("small", "petrol", 0.111),
        ("small", "cng", 0.068),
        ("hatchback", "petrol", 0.140),
        ("hatchback", "diesel", 0.126),
        ("sedan", "petrol", 0.153),
        ("sedan", "diesel", 0.141),
        ("suv", "petrol", 0.213),
        ("suv", "diesel", 0.220),
    ],
)
def test_car_modes(factors, category, fuel, expected_factor):
    result = calculate_carbon_footprint(
        make_user(
            transport_mode="car",
            distance_km_per_day=10,
            car_category=category,
            car_fuel=fuel,
        ),
        factors,
    )

    assert result.transport.kg_co2e == pytest.approx(
        10 * expected_factor * 365,
        abs=0.01,
    )


def test_electric_car_mode_uses_battery_energy_proxy_and_grid_factor(factors):
    result = calculate_carbon_footprint(
        make_user(
            transport_mode="car",
            distance_km_per_day=10,
            car_category="electric",
            car_fuel=None,
        ),
        factors,
    )

    expected = 10 * 0.106 * 0.710 * 365
    assert result.transport.kg_co2e == pytest.approx(
        expected,
        abs=0.01,
    )


def test_hybrid_car_mode(factors):
    result = calculate_carbon_footprint(
        make_user(
            transport_mode="car",
            distance_km_per_day=10,
            car_category="hybrid",
        ),
        factors,
    )

    assert result.transport.kg_co2e == pytest.approx(
        10 * 0.103 * 365,
        abs=0.01,
    )


# ---------------------------------------------------------------------------
# Electricity
# ---------------------------------------------------------------------------


def test_electricity_calculation(factors):
    result = calculate_carbon_footprint(
        make_user(electricity_kwh_per_month=100),
        factors,
    )

    assert result.electricity.kg_co2e == pytest.approx(
        100 * 12 * 0.710,
        abs=0.01,
    )


def test_household_electricity_is_allocated_equally(factors):
    result = calculate_carbon_footprint(
        make_user(
            electricity_kwh_per_month=400,
            household_size=4,
        ),
        factors,
    )

    assert result.electricity.kg_co2e == pytest.approx(
        100 * 12 * 0.710,
        abs=0.01,
    )


def test_zero_electricity_produces_zero_emissions(factors):
    result = calculate_carbon_footprint(
        make_user(electricity_kwh_per_month=0),
        factors,
    )

    assert result.electricity.kg_co2e == 0


# ---------------------------------------------------------------------------
# Diet
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("category", "expected_daily_factor"),
    [
        ("high_meat", 7.19),
        ("medium_meat", 5.63),
        ("low_meat", 4.67),
        ("pescatarian", 3.91),
        ("vegetarian", 3.81),
        ("vegan", 2.89),
    ],
)
def test_all_diet_categories(factors, category, expected_daily_factor):
    result = calculate_carbon_footprint(
        make_user(diet_category=category),
        factors,
    )

    assert result.diet.kg_co2e == pytest.approx(
        expected_daily_factor * 365,
        abs=0.01,
    )


# ---------------------------------------------------------------------------
# Waste
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "recycling_habit",
    ["rarely", "sometimes"],
)
def test_non_consistent_recycling_does_not_apply_unsupported_reduction(
    factors,
    recycling_habit,
):
    result = calculate_carbon_footprint(
        make_user(
            waste_kg_per_day=1,
            recycling_habit=recycling_habit,
        ),
        factors,
    )

    assert result.waste.kg_co2e == pytest.approx(365, abs=0.01)


def test_consistent_recycling_applies_documented_50_percent_assumption(
    factors,
):
    result = calculate_carbon_footprint(
        make_user(
            waste_kg_per_day=1,
            recycling_habit="consistently",
        ),
        factors,
    )

    assert result.waste.kg_co2e == pytest.approx(
        1.0 * 0.50 * 365,
        abs=0.01,
    )


def test_household_waste_is_allocated_equally(factors):
    result = calculate_carbon_footprint(
        make_user(
            waste_kg_per_day=4,
            household_size=4,
        ),
        factors,
    )

    assert result.waste.kg_co2e == pytest.approx(365, abs=0.01)


def test_zero_waste_produces_zero_waste_emissions(factors):
    result = calculate_carbon_footprint(
        make_user(waste_kg_per_day=0),
        factors,
    )

    assert result.waste.kg_co2e == 0


# ---------------------------------------------------------------------------
# Shopping
# ---------------------------------------------------------------------------


def test_shopping_does_not_affect_numeric_total(factors):
    base = make_user(
        electricity_kwh_per_month=100,
        waste_kg_per_day=1,
        shopping_habit="rarely_buys_new_items",
    )
    frequent = make_user(
        electricity_kwh_per_month=100,
        waste_kg_per_day=1,
        shopping_habit="buys_frequently",
    )

    result_base = calculate_carbon_footprint(base, factors)
    result_frequent = calculate_carbon_footprint(frequent, factors)

    assert result_base.total_kg_co2e == result_frequent.total_kg_co2e
    assert result_base.shopping_included is False
    assert result_frequent.shopping_included is False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("distance_km_per_day", -1),
        ("electricity_kwh_per_month", -1),
        ("waste_kg_per_day", -1),
        ("household_size", 0),
        ("household_size", -1),
    ],
)
def test_negative_numeric_inputs_are_rejected(factors, field, value):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(**{field: value}),
            factors,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("distance_km_per_day", float("nan")),
        ("distance_km_per_day", float("inf")),
        ("electricity_kwh_per_month", float("nan")),
        ("electricity_kwh_per_month", float("-inf")),
        ("waste_kg_per_day", float("nan")),
    ],
)
def test_non_finite_numeric_inputs_are_rejected(factors, field, value):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(**{field: value}),
            factors,
        )


def test_boolean_numeric_input_is_rejected(factors):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(distance_km_per_day=True),
            factors,
        )


def test_invalid_transport_mode_is_rejected(factors):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(transport_mode="train"),
            factors,
        )


def test_two_wheeler_requires_valid_type(factors):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(
                transport_mode="two_wheeler",
                two_wheeler_type=None,
            ),
            factors,
        )


def test_invalid_two_wheeler_type_is_rejected(factors):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(
                transport_mode="two_wheeler",
                two_wheeler_type="electric",
            ),
            factors,
        )


def test_car_requires_category(factors):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(
                transport_mode="car",
                car_category=None,
            ),
            factors,
        )


def test_invalid_car_category_is_rejected(factors):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(
                transport_mode="car",
                car_category="truck",
            ),
            factors,
        )


def test_non_hybrid_car_requires_valid_fuel(factors):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(
                transport_mode="car",
                car_category="sedan",
                car_fuel=None,
            ),
            factors,
        )


def test_electric_car_does_not_require_petrol_diesel_or_cng_fuel(factors):
    result = calculate_carbon_footprint(
        make_user(
            transport_mode="car",
            distance_km_per_day=10,
            car_category="electric",
            car_fuel=None,
        ),
        factors,
    )

    assert result.transport.kg_co2e > 0


def test_hybrid_does_not_require_petrol_or_diesel_fuel(factors):
    result = calculate_carbon_footprint(
        make_user(
            transport_mode="car",
            distance_km_per_day=10,
            car_category="hybrid",
            car_fuel=None,
        ),
        factors,
    )

    assert result.transport.kg_co2e == pytest.approx(
        10 * 0.103 * 365,
        abs=0.01,
    )


def test_small_car_does_not_accept_diesel(factors):
    with pytest.raises(CarbonCalculationError, match="not supported"):
        calculate_carbon_footprint(
            make_user(
                transport_mode="car",
                car_category="small",
                car_fuel="diesel",
            ),
            factors,
        )


def test_hybrid_or_electric_does_not_accept_separate_fuel(factors):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(
                transport_mode="car",
                car_category="electric",
                car_fuel="petrol",
            ),
            factors,
        )

    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(
                transport_mode="car",
                car_category="hybrid",
                car_fuel="petrol",
            ),
            factors,
        )


def test_invalid_car_fuel_is_rejected(factors):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(
                transport_mode="car",
                car_category="sedan",
                car_fuel="hybrid",
            ),
            factors,
        )


def test_invalid_diet_category_is_rejected(factors):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(diet_category="carnivore"),
            factors,
        )


def test_invalid_recycling_habit_is_rejected(factors):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(recycling_habit="always"),
            factors,
        )


# ---------------------------------------------------------------------------
# Result integrity and classification
# ---------------------------------------------------------------------------


def test_total_equals_sum_of_categories(factors):
    result = calculate_carbon_footprint(
        make_user(
            transport_mode="car",
            distance_km_per_day=10,
            car_category="hatchback",
            car_fuel="petrol",
            electricity_kwh_per_month=100,
            diet_category="vegetarian",
            waste_kg_per_day=1,
            recycling_habit="rarely",
        ),
        factors,
    )

    category_sum = (
        result.transport.kg_co2e
        + result.electricity.kg_co2e
        + result.diet.kg_co2e
        + result.waste.kg_co2e
    )

    assert result.total_kg_co2e == pytest.approx(category_sum, abs=0.02)


def test_total_tonnes_conversion(factors):
    result = calculate_carbon_footprint(
        make_user(electricity_kwh_per_month=100),
        factors,
    )

    assert result.total_tonnes_co2e == pytest.approx(
        result.total_kg_co2e / 1000,
        abs=0.001,
    )


def test_percentage_breakdown_sums_to_100(factors):
    result = calculate_carbon_footprint(
        make_user(
            transport_mode="car",
            distance_km_per_day=10,
            car_category="hatchback",
            car_fuel="petrol",
            electricity_kwh_per_month=100,
            diet_category="vegetarian",
            waste_kg_per_day=1,
        ),
        factors,
    )

    total_percentage = (
        result.transport.percentage
        + result.electricity.percentage
        + result.diet.percentage
        + result.waste.percentage
    )

    assert total_percentage == pytest.approx(100, abs=0.1)


@pytest.mark.parametrize(
    ("total", "expected"),
    [
        (0, "Low"),
        (1999.99, "Low"),
        (2000, "Medium"),
        (4000, "Medium"),
        (4000.01, "High"),
    ],
)
def test_project_classification_boundaries(total, expected):
    assert classify_footprint(total) == expected


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), -1],
)
def test_classification_rejects_invalid_totals(value):
    with pytest.raises(CarbonCalculationError):
        classify_footprint(value)


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------


def test_missing_factor_file_is_rejected(tmp_path):
    missing_file = tmp_path / "missing.json"

    with pytest.raises(CarbonCalculationError, match="not found"):
        load_emission_factors(missing_file)


def test_invalid_factor_json_is_rejected(tmp_path):
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{invalid", encoding="utf-8")

    with pytest.raises(CarbonCalculationError, match="Invalid JSON"):
        load_emission_factors(invalid_file)


def test_non_object_factor_json_is_rejected(tmp_path):
    invalid_file = tmp_path / "array.json"
    invalid_file.write_text(json.dumps([]), encoding="utf-8")

    with pytest.raises(CarbonCalculationError, match="JSON object"):
        load_emission_factors(invalid_file)


def test_non_integer_household_size_is_rejected(factors):
    with pytest.raises(CarbonCalculationError):
        calculate_carbon_footprint(
            make_user(household_size=2.5),
            factors,
        )
