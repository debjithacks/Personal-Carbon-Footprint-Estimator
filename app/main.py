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
    CAR_FUEL_OPTIONS,
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

        .ai-card {
            padding: 1.15rem;
            border-radius: 0.75rem;
            border: 1px solid rgba(128, 128, 128, 0.20);
            background: rgba(128, 128, 128, 0.04);
            line-height: 1.6;
        }

        .ai-card-title {
            font-weight: 650;
            margin-bottom: 0.6rem;
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
# Main input form
# ---------------------------------------------------------------------------

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
            index=0,
            help=(
                "Choose the transport mode you use most for your "
                "typical daily travel."
            ),
        )

    transport_mode = TRANSPORT_OPTIONS[transport_label]

    with col2:
        distance_km_per_day = st.number_input(
            "Average distance per day (km)",
            min_value=0.0,
            max_value=1000.0,
            value=5.0,
            step=0.5,
            help=(
                "Approximate distance travelled per day using your "
                "selected transport mode."
            ),
        )

    car_category = None
    car_fuel = None
    two_wheeler_type = None

    if transport_mode == "car":

        st.markdown("**Car Details**")

        car_col1, car_col2 = st.columns(2)

        with car_col1:
            car_category_label = st.selectbox(
                "Car type",
                options=list(CAR_CATEGORY_OPTIONS.keys()),
            )

            car_category = CAR_CATEGORY_OPTIONS[car_category_label]

        if car_category != "hybrid":

            with car_col2:
                car_fuel_label = st.selectbox(
                    "Fuel type",
                    options=list(CAR_FUEL_OPTIONS.keys()),
                )

                car_fuel = CAR_FUEL_OPTIONS[car_fuel_label]

    elif transport_mode == "two_wheeler":

        st.markdown("**Two-wheeler Details**")

        two_wheeler_label = st.selectbox(
            "Two-wheeler type",
            options=list(TWO_WHEELER_OPTIONS.keys()),
        )

        two_wheeler_type = TWO_WHEELER_OPTIONS[two_wheeler_label]

    # -----------------------------------------------------------------------
    # Electricity
    # -----------------------------------------------------------------------

    st.markdown("---")
    st.subheader("Electricity")

    electricity_kwh_per_month = st.number_input(
        "Average household electricity consumption per month (kWh)",
        min_value=0.0,
        max_value=10000.0,
        value=120.0,
        step=10.0,
        help=(
            "Use your electricity bill's monthly consumption when available. "
            "This is the electricity consumption associated with your estimate."
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
        index=list(DIET_OPTIONS.keys()).index("Vegetarian"),
    )

    diet_category = DIET_OPTIONS[diet_label]

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
            value=1.0,
            step=0.1,
            help="Approximate amount of waste generated per day.",
        )

    with waste_col2:
        recycling_label = st.selectbox(
            "Recycling habit",
            options=list(RECYCLING_OPTIONS.keys()),
            index=0,
        )

    recycling_habit = RECYCLING_OPTIONS[recycling_label]

    # -----------------------------------------------------------------------
    # Shopping
    # -----------------------------------------------------------------------

    st.markdown("---")
    st.subheader("Shopping and Consumption")

    shopping_label = st.selectbox(
        "How frequently do you buy new items?",
        options=list(SHOPPING_OPTIONS.keys()),
        index=1,
        help=(
            "This information is currently used as qualitative context only. "
            "It does not change the calculated CO₂e total."
        ),
    )

    shopping_habit = SHOPPING_OPTIONS[shopping_label]

    # -----------------------------------------------------------------------
    # Submit
    # -----------------------------------------------------------------------

    st.markdown("---")

    submitted = st.form_submit_button(
        "Calculate My Footprint",
        use_container_width=True,
        type="primary",
    )


# ---------------------------------------------------------------------------
# Calculation
# ---------------------------------------------------------------------------

if submitted:

    user_input = CarbonInput(
        transport_mode=transport_mode,
        distance_km_per_day=distance_km_per_day,
        car_category=car_category,
        car_fuel=car_fuel,
        two_wheeler_type=two_wheeler_type,
        electricity_kwh_per_month=electricity_kwh_per_month,
        diet_category=diet_category,
        waste_kg_per_day=waste_kg_per_day,
        recycling_habit=recycling_habit,
        shopping_habit=shopping_habit,
    )

    try:
        factors = get_emission_factors()

        result = calculate_carbon_footprint(
            user_input,
            factors,
        )

    except CarbonCalculationError as exc:
        st.error(f"Unable to calculate the footprint: {exc}")
        st.stop()

    # Store the deterministic result and input context.
    st.session_state["carbon_result"] = result
    st.session_state["carbon_input"] = user_input

    # Reset previous AI guidance whenever the user calculates a new result.
    st.session_state["granite_advice"] = None
    st.session_state["granite_error"] = None

    # -----------------------------------------------------------------------
    # Generate local AI guidance
    # -----------------------------------------------------------------------

    try:
        with st.spinner("Generating personalized guidance..."):

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

    st.markdown("---")

    st.markdown(
        '<div class="section-title">2. Your Estimated Footprint</div>',
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------------------------
    # KPI metrics
    # -----------------------------------------------------------------------

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

            st.write(f"**{category}**")

            st.progress(
                min(
                    max(category_percentage / 100.0, 0.0),
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
        '<div class="section-title">4. Methodology and Transparency</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="disclosure">{FOOTPRINT_DISCLOSURE}</div>',
        unsafe_allow_html=True,
    )

    st.caption(CLASSIFICATION_DISCLOSURE)

    with st.expander("View Your Input Summary"):

        st.write(
            {
                "Transport mode": input_data.transport_mode,
                "Distance per day (km)": input_data.distance_km_per_day,
                "Car category": input_data.car_category,
                "Car fuel": input_data.car_fuel,
                "Two-wheeler type": input_data.two_wheeler_type,
                "Electricity (kWh/month)": (
                    input_data.electricity_kwh_per_month
                ),
                "Diet": input_data.diet_category,
                "Waste (kg/day)": input_data.waste_kg_per_day,
                "Recycling": input_data.recycling_habit,
                "Shopping": input_data.shopping_habit,
            }
        )

    # -----------------------------------------------------------------------
    # Local AI guidance
    # -----------------------------------------------------------------------

    st.markdown("---")

    st.markdown(
        '<div class="section-title">5. Personalized AI Guidance</div>',
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

    if granite_advice is not None:

        st.markdown(
            '<div class="ai-card">',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="ai-card-title">Summary</div>',
            unsafe_allow_html=True,
        )

        st.write(
            granite_advice.summary
        )

        st.markdown(
            '<div class="ai-card-title">Recommended Actions</div>',
            unsafe_allow_html=True,
        )

        for index, action in enumerate(
            granite_advice.actions,
            start=1,
        ):
            st.write(
                f"{index}. {action}"
            )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

    elif granite_error:

        st.warning(
            "Personalized AI guidance is currently unavailable. "
            "The carbon footprint calculation remains available."
        )

        with st.expander("Technical details"):
            st.code(
                granite_error
            )

    else:

        st.info(
            "AI guidance was not generated for this result."
        )