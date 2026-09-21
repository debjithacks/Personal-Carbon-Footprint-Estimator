from services.granite_service import GraniteLocalService


def main() -> None:
    service = GraniteLocalService()

    category_breakdown = {
        "transport": 620.0,
        "electricity": 2050.0,
        "diet": 550.0,
        "waste": 163.0,
    }

    habit_context = {
        "transport_mode": "Car",
        "diet_category": "Vegetarian",
        "recycling_habit": "Rarely",
        "shopping_habit": "Buys frequently",
    }

    print("Testing local IBM Granite...")
    print(f"Model: {service.config.model}")
    print()

    category, value = service.largest_contributor(
        category_breakdown
    )

    print("Largest contributor determined by Python:")
    print(f"{category}: {value:.2f} kg CO2e")
    print()

    print("Sending request to Granite...")
    print()

    advice = service.generate_recommendations(
        total_kg_co2e=3383.0,
        classification="Medium",
        category_breakdown=category_breakdown,
        habit_context=habit_context,
    )

    print("=" * 70)
    print("GRANITE RESPONSE")
    print("=" * 70)

    print()
    print("SUMMARY:")
    print(advice.summary)

    print()
    print("ACTIONS:")

    for index, action in enumerate(advice.actions, start=1):
        print(f"{index}. {action}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()