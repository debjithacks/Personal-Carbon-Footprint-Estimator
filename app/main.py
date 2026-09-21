from __future__ import annotations

import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Project path configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Third-party imports
# ---------------------------------------------------------------------------

import plotly.graph_objects as go
import streamlit as st


# ---------------------------------------------------------------------------
# Application imports
# ---------------------------------------------------------------------------

from services.carbon_calculator import (
    CarbonCalculationError,
    CarbonInput,
    calculate_carbon_footprint,
    load_emission_factors,
)

from services.granite_service import (
    GraniteLocalError,
    GraniteLocalService,
)

from utils.constants import (
    APP_TITLE,
    CAR_CATEGORY_OPTIONS,
    CAR_FUEL_OPTIONS_BY_CATEGORY,
    CLASSIFICATION_DISCLOSURE,
    DIET_OPTIONS,
    FOOTPRINT_DISCLOSURE,
    RECYCLING_OPTIONS,
    SHOPPING_OPTIONS,
    TRANSPORT_OPTIONS,
    TWO_WHEELER_OPTIONS,
)


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Widget/session-state keys
# ---------------------------------------------------------------------------

FORM_WIDGET_KEYS = (
    "transport_mode",
    "distance_km_per_day",
    "car_category",
    "car_fuel",
    "two_wheeler_type",
    "household_size",
    "electricity_kwh_per_month",
    "diet_category",
    "waste_kg_per_day",
    "recycling_habit",
    "shopping_habit",
)

RESULT_SESSION_KEYS = (
    "carbon_result",
    "carbon_input",
    "granite_advice",
    "granite_error",
)


def reset_application_state() -> None:
    """Reset calculated output and force a completely fresh form."""

    # Clear calculated output and AI state.
    for key in RESULT_SESSION_KEYS:
        st.session_state.pop(key, None)

    # Streamlit widget state is tied to the widget key. Incrementing the
    # version makes all widgets receive new keys on the next rerun, forcing
    # them back to their declared defaults (blank for this form).
    current_version = st.session_state.get("form_version", 0)
    st.session_state["form_version"] = current_version + 1


# ---------------------------------------------------------------------------
# Custom styling
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
        .main {
            padding-top: 1.5rem;
        }

        .hero-title {
            font-size: 2.4rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
        }

        .hero-subtitle {
            font-size: 1.05rem;
            color: #6b7280;
            line-height: 1.6;
            margin-bottom: 1.5rem;
        }

        .section-title {
            font-size: 1.35rem;
            font-weight: 650;
            margin-top: 1.25rem;
            margin-bottom: 0.75rem;
        }

        .disclosure {
            font-size: 0.82rem;
            color: #6b7280;
            line-height: 1.6;
        }

        .result-card {
            padding: 1rem;
            border-radius: 0.75rem;
            border: 1px solid rgba(128, 128, 128, 0.20);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Cached services
# ---------------------------------------------------------------------------

@st.cache_resource
def get_emission_factors() -> dict:
    """Load the project's single source of truth for emission factors."""
    return load_emission_factors()


@st.cache_resource
def get_granite_service() -> GraniteLocalService:
    """Create and cache the local IBM Granite service."""
    return GraniteLocalService()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="hero-title">Personal Carbon Footprint Estimator</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-subtitle">
        Estimate your annual lifestyle CO₂e from everyday activities and
        understand which categories contribute most to your footprint.
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:

    st.header("About")

    st.write(
        "This tool provides an indicative annual lifestyle CO₂e estimate "
        "using documented emission factors, proxies, and assumptions."
    )

    st.markdown("---")

    st.subheader("Included Categories")

    st.write("Transport")
    st.write("Electricity")
    st.write("Diet")
    st.write("Waste")

    st.subheader("Additional Context")

    st.write("Shopping and consumption habits")

    st.markdown("---")

    st.caption(
        "Shopping habits are used as qualitative context and do not change "
        "the numerical CO₂e total."
    )


# ---------------------------------------------------------------------------
# Main input section
# ---------------------------------------------------------------------------

# Versioned widget keys are used so Reset can force Streamlit to recreate
# every input widget from its blank/default state.
form_version = st.session_state.get("form_version", 0)

st.markdown(
    '<div class="section-title">1. Your Lifestyle Information</div>',
    unsafe_allow_html=True,
)


with st.form("carbon_footprint_form"):

    # -----------------------------------------------------------------------
    # Transport
    # -----------------------------------------------------------------------

    st.subheader("Transport")

    col1, col2 = st.columns(2)

    with col1:

        transport_label = st.selectbox(
            "Primary transport mode",
            options=list(TRANSPORT_OPTIONS.keys()),
            index=None,
            placeholder="Select a transport mode",
            key=f"transport_mode_{form_version}",
            help=(
                "Choose the transport mode you use most for your "
                "typical daily travel."
            ),
        )

    transport_mode = (
        TRANSPORT_OPTIONS[transport_label]
        if transport_label is not None
        else None
    )

    with col2:

        distance_km_per_day = st.number_input(
            "Average distance per day (km)",
            min_value=0.0,
            max_value=1000.0,
            value=None,
            step=0.5,
            key=f"distance_km_per_day_{form_version}",
            placeholder="Enter distance",
            help=(
                "Approximate distance travelled per day using your "
                "selected transport mode."
            ),
        )

    # -----------------------------------------------------------------------
    # Initialize conditional transport fields
    # -----------------------------------------------------------------------

    car_category = None
    car_fuel = None
    two_wheeler_type = None

    car_category_label = None
    car_fuel_label = None
    two_wheeler_label = None

    # -----------------------------------------------------------------------
    # Car
    # -----------------------------------------------------------------------

    if transport_mode == "car":

        st.markdown("**Car Details**")

        car_col1, car_col2 = st.columns(2)

        with car_col1:

            car_category_label = st.selectbox(
                "Car type",
                options=list(CAR_CATEGORY_OPTIONS.keys()),
                index=None,
                placeholder="Select car type",
                key=f"car_category_{form_version}",
            )

            if car_category_label is not None:
                car_category = CAR_CATEGORY_OPTIONS[car_category_label]

        if (
            car_category is not None
            and car_category in CAR_FUEL_OPTIONS_BY_CATEGORY
        ):

            with car_col2:

                fuel_options = CAR_FUEL_OPTIONS_BY_CATEGORY[car_category]

                car_fuel_label = st.selectbox(
                    "Fuel type",
                    options=list(fuel_options.keys()),
                    index=None,
                    placeholder="Select fuel type",
                    key=f"car_fuel_{form_version}",
                )

                if car_fuel_label is not None:
                    car_fuel = fuel_options[car_fuel_label]

        elif car_category == "hybrid":

            st.caption(
                "Hybrid vehicles use the documented India-specific hybrid "
                "emission factor; no separate fuel selection is required."
            )

        elif car_category == "electric":

            st.caption(
                "Electric-car transport emissions are estimated from a BEE "
                "reported private EV energy-use proxy multiplied by the CEA "
                "Indian grid factor. Charging losses are not separately modeled."
            )

    # -----------------------------------------------------------------------
    # Two-wheeler
    # -----------------------------------------------------------------------

    elif transport_mode == "two_wheeler":

        st.markdown("**Two-wheeler Details**")

        two_wheeler_label = st.selectbox(
            "Two-wheeler type",
            options=list(TWO_WHEELER_OPTIONS.keys()),
            index=None,
            placeholder="Select two-wheeler type",
            key=f"two_wheeler_type_{form_version}",
        )

        if two_wheeler_label is not None:
            two_wheeler_type = TWO_WHEELER_OPTIONS[two_wheeler_label]

    # -----------------------------------------------------------------------
    # Household electricity
    # -----------------------------------------------------------------------

    st.markdown("---")

    st.subheader("Household electricity")

    household_col1, household_col2 = st.columns(2)

    with household_col1:

        household_size = st.number_input(
            "People in household",
            min_value=1,
            max_value=20,
            value=None,
            step=1,
            format="%d",
            key=f"household_size_{form_version}",
            placeholder="Enter household size",
            help=(
                "Household electricity and waste are divided equally by this "
                "household size to estimate your personal share."
            ),
        )

    with household_col2:

        electricity_kwh_per_month = st.number_input(
            "Average household electricity consumption per month (kWh)",
            min_value=0.0,
            max_value=10000.0,
            value=None,
            step=10.0,
            key=f"electricity_kwh_per_month_{form_version}",
            placeholder="Enter monthly household use",
            help=(
                "Use your electricity bill's monthly consumption when available. "
                "The estimator divides this household total equally across "
                "household members."
            ),
        )

    # -----------------------------------------------------------------------
    # Diet
    # -----------------------------------------------------------------------

    st.markdown("---")

    st.subheader("Diet")

    diet_label = st.selectbox(
        "Typical diet pattern",
        options=list(DIET_OPTIONS.keys()),
        index=None,
        placeholder="Select a diet pattern",
        key=f"diet_category_{form_version}",
    )

    diet_category = (
        DIET_OPTIONS[diet_label]
        if diet_label is not None
        else None
    )

    # -----------------------------------------------------------------------
    # Waste
    # -----------------------------------------------------------------------

    st.markdown("---")

    st.subheader("Waste")

    waste_col1, waste_col2 = st.columns(2)

    with waste_col1:

        waste_kg_per_day = st.number_input(
            "Approximate household waste per day (kg)",
            min_value=0.0,
            max_value=100.0,
            value=None,
            step=0.1,
            key=f"waste_kg_per_day_{form_version}",
            placeholder="Enter daily household waste",
            help=(
                "Approximate amount of household waste generated per day. "
                "The estimator divides this equally across household members."
            ),
        )

    with waste_col2:

        recycling_label = st.selectbox(
            "Recycling habit",
            options=list(RECYCLING_OPTIONS.keys()),
            index=None,
            placeholder="Select recycling habit",
            key=f"recycling_habit_{form_version}",
        )

    recycling_habit = (
        RECYCLING_OPTIONS[recycling_label]
        if recycling_label is not None
        else None
    )

    # -----------------------------------------------------------------------
    # Shopping
    # -----------------------------------------------------------------------

    st.markdown("---")

    st.subheader("Shopping and Consumption")

    shopping_label = st.selectbox(
        "How frequently do you buy new items?",
        options=list(SHOPPING_OPTIONS.keys()),
        index=None,
        placeholder="Select shopping habit",
        key=f"shopping_habit_{form_version}",
        help=(
            "This information is currently used as qualitative context only. "
            "It does not change the calculated CO₂e total."
        ),
    )

    shopping_habit = (
        SHOPPING_OPTIONS[shopping_label]
        if shopping_label is not None
        else None
    )

    # -----------------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------------

    st.markdown("---")

    action_col1, action_col2 = st.columns([4, 1])

    with action_col1:

        calculate_pressed = st.form_submit_button(
            "Calculate My Footprint",
            use_container_width=True,
            type="primary",
        )

    with action_col2:

        reset_pressed = st.form_submit_button(
            "Reset",
            use_container_width=True,
            type="secondary",
            help="Clear all inputs, results, and AI guidance.",
            on_click=reset_application_state,
        )


# ---------------------------------------------------------------------------
# Calculation
# ---------------------------------------------------------------------------

if calculate_pressed:

    missing_fields: list[str] = []

    # -----------------------------------------------------------------------
    # Required transport fields
    # -----------------------------------------------------------------------

    if transport_label is None:
        missing_fields.append("Primary transport mode")

    if distance_km_per_day is None:
        missing_fields.append("Average distance per day")

    if transport_mode == "car":

        if car_category is None:
            missing_fields.append("Car type")

        elif (
            car_category in CAR_FUEL_OPTIONS_BY_CATEGORY
            and car_fuel is None
        ):
            missing_fields.append("Fuel type")

    if (
        transport_mode == "two_wheeler"
        and two_wheeler_type is None
    ):
        missing_fields.append("Two-wheeler type")

    # -----------------------------------------------------------------------
    # Required household fields
    # -----------------------------------------------------------------------

    if household_size is None:
        missing_fields.append("People in household")

    if electricity_kwh_per_month is None:
        missing_fields.append(
            "Household electricity consumption"
        )

    # -----------------------------------------------------------------------
    # Required lifestyle fields
    # -----------------------------------------------------------------------

    if diet_category is None:
        missing_fields.append("Typical diet pattern")

    if waste_kg_per_day is None:
        missing_fields.append("Household waste per day")

    if recycling_habit is None:
        missing_fields.append("Recycling habit")

    if shopping_habit is None:
        missing_fields.append("Shopping habit")

    # -----------------------------------------------------------------------
    # Validation response
    # -----------------------------------------------------------------------

    if missing_fields:

        # Do not show stale results after an invalid new calculation attempt.
        for key in RESULT_SESSION_KEYS:
            st.session_state.pop(key, None)

        st.warning(
            "Please complete all required fields before calculating: "
            + ", ".join(missing_fields)
            + "."
        )

        st.stop()

    # -----------------------------------------------------------------------
    # Build validated calculator input
    # -----------------------------------------------------------------------

    user_input = CarbonInput(
        transport_mode=transport_mode,
        distance_km_per_day=distance_km_per_day,
        car_category=car_category,
        car_fuel=car_fuel,
        two_wheeler_type=two_wheeler_type,
        electricity_kwh_per_month=electricity_kwh_per_month,
        household_size=int(household_size),
        diet_category=diet_category,
        waste_kg_per_day=waste_kg_per_day,
        recycling_habit=recycling_habit,
        shopping_habit=shopping_habit,
    )

    # -----------------------------------------------------------------------
    # Deterministic calculation
    # -----------------------------------------------------------------------

    try:

        factors = get_emission_factors()

        result = calculate_carbon_footprint(
            user_input,
            factors,
        )

    except CarbonCalculationError as exc:

        st.error(
            f"Unable to calculate the footprint: {exc}"
        )

        st.stop()

    # -----------------------------------------------------------------------
    # Store deterministic result
    # -----------------------------------------------------------------------

    st.session_state["carbon_result"] = result
    st.session_state["carbon_input"] = user_input

    # Reset previous AI guidance.
    st.session_state["granite_advice"] = None
    st.session_state["granite_error"] = None

    # -----------------------------------------------------------------------
    # Generate local IBM Granite guidance
    # -----------------------------------------------------------------------

    try:

        with st.spinner(
            "Generating personalized guidance..."
        ):

            granite_service = get_granite_service()

            advice = granite_service.generate_recommendations(
                total_kg_co2e=result.total_kg_co2e,
                classification=result.classification,
                category_breakdown={
                    "transport": result.transport.kg_co2e,
                    "electricity": result.electricity.kg_co2e,
                    "diet": result.diet.kg_co2e,
                    "waste": result.waste.kg_co2e,
                },
                habit_context={
                    "transport_mode": user_input.transport_mode,
                    "car_category": (
                        user_input.car_category
                        or "not_applicable"
                    ),
                    "car_fuel": (
                        user_input.car_fuel
                        or "not_applicable"
                    ),
                    "diet_category": user_input.diet_category,
                    "recycling_habit": user_input.recycling_habit,
                    "shopping_habit": user_input.shopping_habit,
                },
            )

        st.session_state["granite_advice"] = advice

    except GraniteLocalError as exc:

        st.session_state["granite_advice"] = None
        st.session_state["granite_error"] = str(exc)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

if "carbon_result" in st.session_state:

    result = st.session_state["carbon_result"]

    input_data = st.session_state["carbon_input"]

    # -----------------------------------------------------------------------
    # Estimated footprint
    # -----------------------------------------------------------------------

    st.markdown("---")

    st.markdown(
        '<div class="section-title">2. Your Estimated Footprint</div>',
        unsafe_allow_html=True,
    )

    metric_col1, metric_col2, metric_col3 = st.columns(3)

    with metric_col1:

        st.metric(
            "Annual CO₂e",
            f"{result.total_kg_co2e:,.0f} kg",
        )

    with metric_col2:

        st.metric(
            "Annual Footprint",
            f"{result.total_tonnes_co2e:.2f} t",
        )

    with metric_col3:

        st.metric(
            "Classification",
            result.classification,
        )

    st.info(
        f"Your estimated annual lifestyle footprint is "
        f"**{result.total_tonnes_co2e:.2f} tonnes CO₂e**."
    )

    # -----------------------------------------------------------------------
    # Category breakdown
    # -----------------------------------------------------------------------

    st.markdown(
        '<div class="section-title">3. Category Breakdown</div>',
        unsafe_allow_html=True,
    )

    category_names = [
        "Transport",
        "Electricity",
        "Diet",
        "Waste",
    ]

    category_values = [
        result.transport.kg_co2e,
        result.electricity.kg_co2e,
        result.diet.kg_co2e,
        result.waste.kg_co2e,
    ]

    category_percentages = [
        result.transport.percentage,
        result.electricity.percentage,
        result.diet.percentage,
        result.waste.percentage,
    ]

    chart_col1, chart_col2 = st.columns(2)

    # -----------------------------------------------------------------------
    # Donut chart
    # -----------------------------------------------------------------------

    with chart_col1:

        figure = go.Figure(
            data=[
                go.Pie(
                    labels=category_names,
                    values=category_values,
                    hole=0.45,
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "%{value:.1f} kg CO₂e<br>"
                        "%{percent}<extra></extra>"
                    ),
                )
            ]
        )

        figure.update_layout(
            title="CO₂e Contribution by Category",
            margin={
                "l": 10,
                "r": 10,
                "t": 50,
                "b": 10,
            },
            legend={
                "orientation": "h",
                "y": -0.1,
            },
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )

    # -----------------------------------------------------------------------
    # Category progress bars
    # -----------------------------------------------------------------------

    with chart_col2:

        breakdown_rows = {
            "Transport": [
                result.transport.kg_co2e,
                result.transport.percentage,
            ],
            "Electricity": [
                result.electricity.kg_co2e,
                result.electricity.percentage,
            ],
            "Diet": [
                result.diet.kg_co2e,
                result.diet.percentage,
            ],
            "Waste": [
                result.waste.kg_co2e,
                result.waste.percentage,
            ],
        }

        for category, values in breakdown_rows.items():

            category_kg = values[0]
            category_percentage = values[1]

            st.write(
                f"**{category}**"
            )

            st.progress(
                min(
                    max(
                        category_percentage / 100.0,
                        0.0,
                    ),
                    1.0,
                )
            )

            st.caption(
                f"{category_kg:,.1f} kg CO₂e · "
                f"{category_percentage:.1f}%"
            )

    # -----------------------------------------------------------------------
    # Methodology and transparency
    # -----------------------------------------------------------------------

    st.markdown("---")

    st.markdown(
        '<div class="section-title">'
        "4. Methodology and Transparency"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="disclosure">'
        f"{FOOTPRINT_DISCLOSURE}"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.caption(
        CLASSIFICATION_DISCLOSURE
    )

    st.caption(
        "Household electricity and waste are allocated equally across "
        "household members. EV transport uses a BEE-reported energy-use "
        "proxy multiplied by the CEA grid factor; charging losses are "
        "not separately modeled."
    )

    with st.expander(
        "View Your Input Summary"
    ):

        st.write(
            {
                "Transport mode": input_data.transport_mode,
                "Distance per day (km)": (
                    input_data.distance_km_per_day
                ),
                "Car category": (
                    input_data.car_category
                ),
                "Car fuel": (
                    input_data.car_fuel
                ),
                "Two-wheeler type": (
                    input_data.two_wheeler_type
                ),
                "Household size": (
                    input_data.household_size
                ),
                "Household electricity (kWh/month)": (
                    input_data.electricity_kwh_per_month
                ),
                "Personal electricity share (kWh/month)": (
                    input_data.electricity_kwh_per_month
                    / input_data.household_size
                ),
                "Diet": (
                    input_data.diet_category
                ),
                "Household waste (kg/day)": (
                    input_data.waste_kg_per_day
                ),
                "Personal waste share (kg/day)": (
                    input_data.waste_kg_per_day
                    / input_data.household_size
                ),
                "Recycling": (
                    input_data.recycling_habit
                ),
                "Shopping": (
                    input_data.shopping_habit
                ),
            }
        )

    # -----------------------------------------------------------------------
    # Local AI guidance
    # -----------------------------------------------------------------------

    st.markdown("---")

    st.markdown(
        '<div class="section-title">'
        "5. Personalized AI Guidance"
        "</div>",
        unsafe_allow_html=True,
    )

    st.caption(
        "Generated locally using IBM Granite. "
        "The AI does not calculate or modify the numerical CO₂e result."
    )

    granite_advice = st.session_state.get(
        "granite_advice"
    )

    granite_error = st.session_state.get(
        "granite_error"
    )

    # -----------------------------------------------------------------------
    # Successful AI response
    # -----------------------------------------------------------------------

    if granite_advice is not None:

        with st.container(border=True):

            st.markdown(
                "**Summary**"
            )

            st.write(
                granite_advice.summary
            )

            st.markdown(
                "**Recommended Actions**"
            )

            for index, action in enumerate(
                granite_advice.actions,
                start=1,
            ):

                st.write(
                    f"{index}. {action}"
                )

    # -----------------------------------------------------------------------
    # AI unavailable
    # -----------------------------------------------------------------------

    elif granite_error:

        st.warning(
            "Personalized AI guidance is currently unavailable. "
            "The carbon footprint calculation remains available."
        )

        with st.expander(
            "Technical details"
        ):

            st.code(
                granite_error
            )

    # -----------------------------------------------------------------------
    # No AI response
    # -----------------------------------------------------------------------

    else:

        st.info(
            "AI guidance was not generated for this result."
        )