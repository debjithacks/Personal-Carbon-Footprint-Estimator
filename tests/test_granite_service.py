from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.granite_service import (
    GraniteAdvice,
    GraniteLocalResponseError,
    GraniteLocalService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service():
    """Return a local Granite service instance."""
    return GraniteLocalService()


@pytest.fixture
def category_breakdown():
    """Standard deterministic category breakdown."""
    return {
        "transport": 620.0,
        "electricity": 2050.0,
        "diet": 550.0,
        "waste": 163.0,
    }


@pytest.fixture
def habit_context():
    """Standard lifestyle context."""
    return {
        "transport_mode": "Car",
        "diet_category": "vegetarian",
        "recycling_habit": "rarely",
        "shopping_habit": "buys_frequently",
    }


# ---------------------------------------------------------------------------
# Largest contributor
# ---------------------------------------------------------------------------

def test_largest_contributor_is_determined_by_python(
    service,
    category_breakdown,
):
    category, value = service.largest_contributor(
        category_breakdown
    )

    assert category == "electricity"
    assert value == 2050.0


def test_largest_contributor_rejects_empty_breakdown(service):
    with pytest.raises(GraniteLocalResponseError):
        service.largest_contributor({})


def test_largest_contributor_rejects_negative_values(service):
    with pytest.raises(GraniteLocalResponseError):
        service.largest_contributor(
            {
                "transport": -1.0,
                "electricity": 100.0,
            }
        )


def test_largest_contributor_rejects_non_numeric_values(service):
    with pytest.raises(GraniteLocalResponseError):
        service.largest_contributor(
            {
                "transport": "100",
                "electricity": 200.0,
            }
        )


# ---------------------------------------------------------------------------
# Prompt personalization
# ---------------------------------------------------------------------------

def test_vegetarian_prompt_blocks_meat_recommendation(
    service,
    category_breakdown,
):
    prompt = service.build_prompt(
        total_kg_co2e=3383.0,
        classification="Medium",
        category_breakdown=category_breakdown,
        habit_context={
            "transport_mode": "Car",
            "diet_category": "vegetarian",
            "recycling_habit": "rarely",
            "shopping_habit": "buys_frequently",
        },
    )

    assert "DO NOT recommend reducing meat consumption" in prompt
    assert "DO NOT assume the user eats meat" in prompt


def test_vegan_prompt_blocks_meat_and_dairy(
    service,
    category_breakdown,
):
    prompt = service.build_prompt(
        total_kg_co2e=3383.0,
        classification="Medium",
        category_breakdown=category_breakdown,
        habit_context={
            "transport_mode": "Car",
            "diet_category": "vegan",
            "recycling_habit": "rarely",
            "shopping_habit": "buys_frequently",
        },
    )

    assert "DO NOT recommend reducing meat or dairy consumption" in prompt
    assert "DO NOT assume the user consumes animal products" in prompt


def test_pescatarian_prompt_blocks_meat_recommendation(
    service,
    category_breakdown,
):
    prompt = service.build_prompt(
        total_kg_co2e=3383.0,
        classification="Medium",
        category_breakdown=category_breakdown,
        habit_context={
            "transport_mode": "Car",
            "diet_category": "pescatarian",
            "recycling_habit": "rarely",
            "shopping_habit": "buys_frequently",
        },
    )

    assert "DO NOT recommend reducing meat consumption" in prompt


def test_prompt_contains_python_determined_largest_contributor(
    service,
    category_breakdown,
    habit_context,
):
    prompt = service.build_prompt(
        total_kg_co2e=3383.0,
        classification="Medium",
        category_breakdown=category_breakdown,
        habit_context=habit_context,
    )

    assert "Electricity: 2050.00 kg CO2e" in prompt
    assert "Python says the largest contributor is" in prompt


# ---------------------------------------------------------------------------
# Response validation
# ---------------------------------------------------------------------------

def test_valid_response_is_parsed():
    response = """
SUMMARY: Electricity is your largest estimated contributor at 2050.00 kg CO2e. Reducing unnecessary electricity use could have the greatest impact on the estimated footprint.
ACTION 1: Review your electricity use and identify the highest-consuming appliances.
ACTION 2: Reduce unnecessary use of high-consumption appliances where practical.
ACTION 3: Improve everyday recycling habits by sorting waste consistently.
""".strip()

    advice = GraniteLocalService.validate_response(
        response,
        diet_category="vegetarian",
    )

    assert isinstance(advice, GraniteAdvice)
    assert len(advice.actions) == 3
    assert "Electricity" in advice.summary
    assert advice.actions[0]
    assert advice.actions[1]
    assert advice.actions[2]


def test_missing_summary_is_rejected():
    response = """
ACTION 1: Reduce unnecessary electricity use.
ACTION 2: Improve recycling habits.
ACTION 3: Buy fewer unnecessary items.
""".strip()

    with pytest.raises(GraniteLocalResponseError):
        GraniteLocalService.validate_response(response)


def test_wrong_number_of_actions_is_rejected():
    response = """
SUMMARY: Electricity is the largest contributor.
ACTION 1: Reduce unnecessary electricity use.
ACTION 2: Improve recycling habits.
""".strip()

    with pytest.raises(GraniteLocalResponseError):
        GraniteLocalService.validate_response(response)


def test_placeholder_summary_is_rejected():
    response = """
SUMMARY: This is the largest contributor.
ACTION 1: Reduce electricity use.
ACTION 2: Improve recycling habits.
ACTION 3: Buy fewer unnecessary items.
""".strip()

    with pytest.raises(GraniteLocalResponseError):
        GraniteLocalService.validate_response(response)


def test_placeholder_action_is_rejected():
    response = """
SUMMARY: Electricity is the largest contributor to the footprint.
ACTION 1: This is the practical action.
ACTION 2: Improve recycling habits.
ACTION 3: Buy fewer unnecessary items.
""".strip()

    with pytest.raises(GraniteLocalResponseError):
        GraniteLocalService.validate_response(response)


# ---------------------------------------------------------------------------
# Diet compatibility validation
# ---------------------------------------------------------------------------

def test_vegetarian_meat_recommendation_is_rejected():
    response = """
SUMMARY: Diet is an important contributor to the estimated footprint.
ACTION 1: Reduce meat consumption and choose more plant-based meals.
ACTION 2: Reduce food waste through better meal planning.
ACTION 3: Prefer seasonal foods where practical.
""".strip()

    with pytest.raises(GraniteLocalResponseError):
        GraniteLocalService.validate_response(
            response,
            diet_category="vegetarian",
        )


def test_pescatarian_meat_recommendation_is_rejected():
    response = """
SUMMARY: Diet is an important contributor to the estimated footprint.
ACTION 1: Reduce meat consumption and choose more plant-based meals.
ACTION 2: Reduce food waste through better meal planning.
ACTION 3: Prefer seasonal foods where practical.
""".strip()

    with pytest.raises(GraniteLocalResponseError):
        GraniteLocalService.validate_response(
            response,
            diet_category="pescatarian",
        )


def test_vegan_dairy_recommendation_is_rejected():
    response = """
SUMMARY: Diet is an important contributor to the estimated footprint.
ACTION 1: Reduce dairy consumption.
ACTION 2: Reduce food waste through better meal planning.
ACTION 3: Prefer seasonal foods where practical.
""".strip()

    with pytest.raises(GraniteLocalResponseError):
        GraniteLocalService.validate_response(
            response,
            diet_category="vegan",
        )


def test_vegetarian_compatible_actions_are_accepted():
    response = """
SUMMARY: Diet is an important contributor to the estimated footprint.
ACTION 1: Reduce food waste through meal planning and better storage.
ACTION 2: Prefer seasonal and locally available vegetarian foods where practical.
ACTION 3: Choose products with less packaging when shopping.
""".strip()

    advice = GraniteLocalService.validate_response(
        response,
        diet_category="vegetarian",
    )

    assert len(advice.actions) == 3


# ---------------------------------------------------------------------------
# Ollama response integration test with a mock client
# ---------------------------------------------------------------------------

def test_generate_recommendations_parses_mocked_ollama_response(
    service,
    category_breakdown,
    habit_context,
):
    mocked_content = """
SUMMARY: Electricity is the largest contributor at 2050.00 kg CO2e. Reducing unnecessary electricity use could have the greatest impact on the estimated footprint.
ACTION 1: Review electricity consumption and identify high-use appliances.
ACTION 2: Reduce unnecessary use of high-consumption appliances where practical.
ACTION 3: Improve recycling habits by sorting waste more consistently.
""".strip()

    service.client = MagicMock()

    service.client.chat.return_value = SimpleNamespace(
        message=SimpleNamespace(
            content=mocked_content
        )
    )

    advice = service.generate_recommendations(
        total_kg_co2e=3383.0,
        classification="Medium",
        category_breakdown=category_breakdown,
        habit_context=habit_context,
    )

    service.client.chat.assert_called_once()

    assert isinstance(advice, GraniteAdvice)
    assert len(advice.actions) == 3
    assert "Electricity" in advice.summary