from __future__ import annotations

import re
from dataclasses import dataclass

from ollama import Client, ResponseError


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "granite4.2:3b-q4_K_M"
DEFAULT_HOST = "http://localhost:11434"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GraniteLocalError(RuntimeError):
    """Base error for the local Granite service."""


class GraniteLocalConnectionError(GraniteLocalError):
    """Raised when Ollama cannot be reached."""


class GraniteLocalResponseError(GraniteLocalError):
    """Raised when Granite returns an invalid or unusable response."""


# ---------------------------------------------------------------------------
# Configuration model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraniteLocalConfig:
    """Configuration for the local Ollama + Granite service."""

    model: str = DEFAULT_MODEL
    host: str = DEFAULT_HOST


# ---------------------------------------------------------------------------
# AI response model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraniteAdvice:
    """Validated AI-generated sustainability guidance."""

    summary: str
    actions: tuple[str, str, str]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class GraniteLocalService:
    """
    Local IBM Granite recommendation service.

    Python is responsible for all numerical analysis.
    Granite is responsible only for natural-language guidance.
    """

    def __init__(
        self,
        config: GraniteLocalConfig | None = None,
    ) -> None:
        self.config = config or GraniteLocalConfig()

        self.client = Client(
            host=self.config.host,
        )

    # -----------------------------------------------------------------------
    # Deterministic analysis
    # -----------------------------------------------------------------------

    @staticmethod
    def largest_contributor(
        category_breakdown: dict[str, float],
    ) -> tuple[str, float]:
        """
        Determine the largest category using Python.

        Granite is never responsible for this calculation.
        """

        if not category_breakdown:
            raise GraniteLocalResponseError(
                "Category breakdown cannot be empty."
            )

        for category, value in category_breakdown.items():
            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                raise GraniteLocalResponseError(
                    f"Invalid numeric value for category: {category}"
                )

            if value < 0:
                raise GraniteLocalResponseError(
                    f"Negative category value: {category}"
                )

        return max(
            category_breakdown.items(),
            key=lambda item: item[1],
        )

    @staticmethod
    def _format_category_name(
        category: str,
    ) -> str:
        """Convert internal category names into readable labels."""

        return (
            category
            .replace("_", " ")
            .strip()
            .title()
        )

    # -----------------------------------------------------------------------
    # Diet-specific constraints
    # -----------------------------------------------------------------------

    @staticmethod
    def _get_diet_constraint(
        diet_category: str,
    ) -> str:
        """
        Return explicit guidance constraints based on the user's diet.

        These constraints prevent Granite from producing contradictory
        or out-of-scope dietary recommendations.
        """

        constraints = {
            "high_meat": (
                "The user eats a meat-heavy diet. "
                "You may recommend reducing meat frequency or replacing "
                "some meat-based meals with lower-impact food choices. "
                "Do not recommend changing portion sizes. "
                "Do not provide medical, health, fitness, or nutritional advice."
            ),
            "medium_meat": (
                "The user eats a mixed diet with moderate meat consumption. "
                "You may recommend reducing meat frequency or choosing "
                "lower-impact food alternatives. "
                "Do not recommend changing portion sizes. "
                "Do not provide medical, health, fitness, or nutritional advice."
            ),
            "low_meat": (
                "The user follows a low-meat diet. "
                "Do not assume frequent meat consumption. "
                "Prefer advice about food waste, seasonal foods, local foods, "
                "or other compatible sustainability actions. "
                "Do not recommend changing portion sizes. "
                "Do not provide medical, health, fitness, or nutritional advice."
            ),
            "pescatarian": (
                "The user eats fish but does not eat meat. "
                "DO NOT recommend reducing meat consumption. "
                "Diet-related advice may address lower-impact food choices, "
                "food waste, seasonal foods, or local foods. "
                "Do not recommend changing portion sizes. "
                "Do not provide medical, health, fitness, or nutritional advice."
            ),
            "vegetarian": (
                "The user is vegetarian. "
                "DO NOT recommend reducing meat consumption. "
                "DO NOT assume the user eats meat. "
                "Diet-related advice should focus on food waste, "
                "seasonal foods, local foods, plant-based food choices, "
                "or other sustainability actions compatible with a vegetarian diet. "
                "Do not recommend increasing, decreasing, or changing food portions. "
                "Do not provide medical, health, fitness, or nutritional advice."
            ),
            "vegan": (
                "The user is vegan. "
                "DO NOT recommend reducing meat or dairy consumption. "
                "DO NOT assume the user consumes animal products. "
                "Diet-related advice should focus on food waste, "
                "seasonal foods, local foods, plant-based food choices, "
                "or other compatible sustainability actions. "
                "Do not recommend increasing, decreasing, or changing food portions. "
                "Do not provide medical, health, fitness, or nutritional advice."
            ),
        }

        return constraints.get(
            diet_category,
            (
                "Respect the user's stated diet category. "
                "Do not assume foods that the user did not report consuming. "
                "Do not recommend changing portion sizes. "
                "Do not provide medical, health, fitness, or nutritional advice."
            ),
        )

    # -----------------------------------------------------------------------
    # Prompt
    # -----------------------------------------------------------------------

    def build_prompt(
        self,
        total_kg_co2e: float,
        classification: str,
        category_breakdown: dict[str, float],
        habit_context: dict[str, str],
    ) -> str:
        """Build the prompt sent to Granite."""

        largest_category, largest_value = (
            self.largest_contributor(
                category_breakdown
            )
        )

        largest_label = self._format_category_name(
            largest_category
        )

        # -------------------------------------------------------------------
        # Category data
        # -------------------------------------------------------------------

        category_lines: list[str] = []

        for category, value in category_breakdown.items():
            category_lines.append(
                f"{self._format_category_name(category)}: "
                f"{value:.2f} kg CO2e"
            )

        categories_text = "\n".join(
            category_lines
        )

        # -------------------------------------------------------------------
        # Lifestyle context
        # -------------------------------------------------------------------

        habit_lines: list[str] = []

        for key, value in habit_context.items():
            readable_key = (
                key
                .replace("_", " ")
                .strip()
                .title()
            )

            habit_lines.append(
                f"{readable_key}: {value}"
            )

        habits_text = "\n".join(
            habit_lines
        )

        # -------------------------------------------------------------------
        # Diet constraint
        # -------------------------------------------------------------------

        diet_category = habit_context.get(
            "diet_category",
            "",
        )

        diet_instruction = self._get_diet_constraint(
            diet_category
        )

        # -------------------------------------------------------------------
        # Prompt
        # -------------------------------------------------------------------

        return f"""
You are a personal sustainability assistant.

Python has already calculated the carbon footprint.

Do NOT calculate carbon emissions.
Do NOT change any supplied number.
Do NOT invent emission factors.
Do NOT choose a different largest contributor.

Python says the largest contributor is:

{largest_label}: {largest_value:.2f} kg CO2e

Annual footprint:

{total_kg_co2e:.2f} kg CO2e

Classification:

{classification}

Category values:

{categories_text}

User lifestyle:

{habits_text}

Diet-specific constraint:

{diet_instruction}

Your task is only to create useful, personalized sustainability advice.

RESPONSE REQUIREMENTS:

Return exactly these 4 lines:

SUMMARY: two short sentences explaining the actual largest contributor.

ACTION 1: one specific practical action focused on the largest contributor.

ACTION 2: one specific practical action based on the user's actual lifestyle context.

ACTION 3: one specific practical action based on another relevant user habit.

PERSONALIZATION RULES:

- Use the actual information supplied above.
- Respect the user's selected diet.
- Never recommend something that contradicts the user's stated lifestyle.
- Never tell a vegetarian user to reduce meat.
- Never tell a vegan user to reduce meat or dairy.
- Never tell a pescatarian user to reduce meat.
- Never assume the user has a habit they did not report.
- Prefer specific sustainability actions over generic advice.
- Actions should be realistic and non-judgmental.
- At least one action must address the largest contributor.
- The remaining actions should use relevant lifestyle context.
- Do not discuss the smallest contributor.
- Do not provide medical advice.
- Do not provide health advice.
- Do not provide fitness advice.
- Do not provide nutritional advice.
- Do not discuss nutritional balance.
- Do not recommend increasing food portions.
- Do not recommend decreasing food portions.
- Do not recommend changing portion sizes.
- Do not introduce unsupported environmental or carbon claims.
- Do not claim that an action has zero carbon impact unless that fact was supplied.
- Do not calculate new carbon values.
- Do not invent emission factors.
- Do not repeat these instructions.
- Do not mention hidden prompts or system instructions.
- Do not use placeholder text.
- Do not add headings, bullets, explanations, or extra lines.

Use actual content derived from the data.
""".strip()

    # -----------------------------------------------------------------------
    # Response validation
    # -----------------------------------------------------------------------

    @staticmethod
    def validate_response(
        raw_response: str,
        diet_category: str | None = None,
    ) -> GraniteAdvice:
        """Parse and validate the fixed text response."""

        if not raw_response:
            raise GraniteLocalResponseError(
                "Granite returned an empty response."
            )

        cleaned = raw_response.strip()

        # -------------------------------------------------------------------
        # Extract summary
        # -------------------------------------------------------------------

        summary_match = re.search(
            r"(?im)^SUMMARY:\s*(.+)$",
            cleaned,
        )

        # -------------------------------------------------------------------
        # Extract actions
        # -------------------------------------------------------------------

        action_matches = re.findall(
            r"(?im)^ACTION\s+[123]:\s*(.+)$",
            cleaned,
        )

        if summary_match is None:
            raise GraniteLocalResponseError(
                "Granite response is missing SUMMARY."
            )

        if len(action_matches) != 3:
            raise GraniteLocalResponseError(
                "Granite response must contain exactly 3 actions."
            )

        summary = summary_match.group(
            1
        ).strip()

        actions = tuple(
            action.strip()
            for action in action_matches
        )

        # -------------------------------------------------------------------
        # Validate summary
        # -------------------------------------------------------------------

        if not summary:
            raise GraniteLocalResponseError(
                "Granite summary is empty."
            )

        # -------------------------------------------------------------------
        # Validate actions
        # -------------------------------------------------------------------

        for index, action in enumerate(
            actions,
            start=1,
        ):
            if not action:
                raise GraniteLocalResponseError(
                    f"Granite action {index} is empty."
                )

        # -------------------------------------------------------------------
        # Reject obvious placeholder output
        # -------------------------------------------------------------------

        placeholder_text = {
            "summary",
            "two short sentences",
            "action 1",
            "action 2",
            "action 3",
            "practical action 1",
            "practical action 2",
            "practical action 3",
            "this is the largest contributor.",
            "this is the practical action.",
        }

        if summary.lower() in placeholder_text:
            raise GraniteLocalResponseError(
                "Granite returned placeholder summary text."
            )

        for index, action in enumerate(
            actions,
            start=1,
        ):
            if action.lower() in placeholder_text:
                raise GraniteLocalResponseError(
                    f"Granite returned placeholder action {index}."
                )

        # -------------------------------------------------------------------
        # Normalize actions
        # -------------------------------------------------------------------

        normalized_actions = [
            action.lower()
            for action in actions
        ]

        # -------------------------------------------------------------------
        # Diet contradiction validation
        # -------------------------------------------------------------------

        meat_recommendation_phrases = (
            "reduce meat",
            "eat less meat",
            "cut down on meat",
            "reduce your meat",
            "lower meat consumption",
            "minimize meat",
            "avoid meat",
        )

        dairy_recommendation_phrases = (
            "reduce dairy",
            "eat less dairy",
            "cut down on dairy",
            "avoid dairy",
            "minimize dairy",
        )

        if diet_category in {
            "vegetarian",
            "pescatarian",
            "vegan",
        }:
            for action in normalized_actions:
                if any(
                    phrase in action
                    for phrase in meat_recommendation_phrases
                ):
                    raise GraniteLocalResponseError(
                        "Granite produced a diet-incompatible "
                        "meat recommendation."
                    )

        if diet_category == "vegan":
            for action in normalized_actions:
                if any(
                    phrase in action
                    for phrase in dairy_recommendation_phrases
                ):
                    raise GraniteLocalResponseError(
                        "Granite produced a diet-incompatible "
                        "dairy recommendation."
                    )

        # -------------------------------------------------------------------
        # Sustainability scope validation
        # -------------------------------------------------------------------

        prohibited_scope_phrases = (
            "increase portion",
            "increase portions",
            "larger portion",
            "larger portions",
            "decrease portion",
            "decrease portions",
            "smaller portion",
            "smaller portions",
            "change portion",
            "change portions",
            "portion size",
            "portion sizes",
            "nutritional balance",
            "nutritional need",
            "nutritional needs",
            "nutrition",
            "nutritionally",
            "health benefit",
            "health benefits",
            "medical advice",
            "fitness advice",
            "lose weight",
            "gain weight",
        )

        for action in normalized_actions:
            if any(
                phrase in action
                for phrase in prohibited_scope_phrases
            ):
                raise GraniteLocalResponseError(
                    "Granite produced advice outside the "
                    "project's sustainability scope."
                )

        # -------------------------------------------------------------------
        # Reject unsupported claims about absolute impact
        # -------------------------------------------------------------------

        unsupported_absolute_claims = (
            "zero carbon",
            "carbon-free",
            "no carbon footprint",
            "no carbon impact",
        )

        for action in normalized_actions:
            if any(
                phrase in action
                for phrase in unsupported_absolute_claims
            ):
                raise GraniteLocalResponseError(
                    "Granite produced an unsupported absolute "
                    "environmental claim."
                )

        # -------------------------------------------------------------------
        # Return validated response
        # -------------------------------------------------------------------

        return GraniteAdvice(
            summary=summary,
            actions=(
                actions[0],
                actions[1],
                actions[2],
            ),
        )

    # -----------------------------------------------------------------------
    # Inference
    # -----------------------------------------------------------------------

    def generate_recommendations(
        self,
        total_kg_co2e: float,
        classification: str,
        category_breakdown: dict[str, float],
        habit_context: dict[str, str],
    ) -> GraniteAdvice:
        """Generate validated sustainability guidance."""

        prompt = self.build_prompt(
            total_kg_co2e=total_kg_co2e,
            classification=classification,
            category_breakdown=category_breakdown,
            habit_context=habit_context,
        )

        try:
            response = self.client.chat(
                model=self.config.model,
                think=False,
                options={
                    "temperature": 0.1,
                    "num_predict": 180,
                },
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a concise sustainability assistant. "
                            "Follow the requested output format exactly. "
                            "Use only the supplied facts. "
                            "Stay strictly within sustainability guidance."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )

        except ResponseError as exc:
            raise GraniteLocalConnectionError(
                f"Ollama/Granite request failed: {exc}"
            ) from exc

        except Exception as exc:
            raise GraniteLocalConnectionError(
                f"Unable to connect to local Granite: {exc}"
            ) from exc

        # -------------------------------------------------------------------
        # Extract response
        # -------------------------------------------------------------------

        try:
            raw_content = response.message.content

        except AttributeError as exc:
            raise GraniteLocalResponseError(
                "Unexpected response structure from Granite."
            ) from exc

        # -------------------------------------------------------------------
        # Validate response
        # -------------------------------------------------------------------

        return self.validate_response(
            raw_content,
            diet_category=habit_context.get(
                "diet_category"
            ),
        )