# Personal Carbon Footprint Estimator

A privacy-friendly Streamlit application that estimates a user's annual personal carbon footprint from everyday lifestyle inputs and uses local IBM Granite to generate personalized sustainability guidance.

The application is designed as a responsible-AI prototype for sustainability education and awareness. Numerical carbon calculations are performed deterministically in Python using documented emission factors and assumptions. IBM Granite is used only for natural-language explanation and personalized action suggestions.

> **Important:** This is an indicative estimate based on published emission factors, documented proxies, and stated assumptions. It is not a complete life-cycle assessment (LCA).

---

## Overview

The Personal Carbon Footprint Estimator helps users understand how different lifestyle categories contribute to their estimated annual greenhouse-gas emissions.

The application calculates emissions from:

- Transport
- Household electricity
- Diet
- Waste

Shopping behavior is collected as qualitative context for the AI guidance but is **not included in the numerical carbon calculation** because the project does not use an unsupported per-item or per-spend emission factor.

The project also demonstrates responsible use of generative AI by keeping all numerical calculations outside the LLM.

---

## Architecture

```text
User Input
    │
    ▼
Input Validation
    │
    ▼
Deterministic Carbon Calculator
    │
    ├── Transport CO₂e
    ├── Electricity CO₂e
    ├── Diet CO₂e
    └── Waste CO₂e
    │
    ▼
Annual CO₂e + Category Breakdown
    │
    ▼
Largest Contributor Determined by Python
    │
    ▼
Local IBM Granite via Ollama
    │
    ▼
Validated Personalized Guidance
```

### Design Principle

The system follows a **deterministic-first architecture**:

- Python calculates all numerical values.
- Emission factors are stored in `data/emission_factors.json`.
- The LLM does not calculate or modify carbon values.
- Python determines the largest contributing category.
- Granite converts the calculated information into a short explanation and practical actions.
- The application validates the generated response before displaying it.

---

## Numeric Categories

### 1. Transport

The application supports:

- Walking
- Cycling
- Public bus
- Two-wheelers
- Cars
- Hybrid vehicles
- Electric vehicles

For cars, the interface supports only documented vehicle/fuel combinations.

Transport calculations use annual distance and documented India-specific road-transport factors where available.

Electric vehicles use a documented electricity-consumption proxy combined with the selected grid-emission factor.

EV charging electricity is **not added again** to household electricity to avoid double counting.

### 2. Household Electricity

Annual household electricity consumption is calculated from monthly electricity usage.

The project uses an India-specific grid emission factor from the Central Electricity Authority (CEA).

If household size is greater than one, household electricity emissions are allocated equally per person.

### 3. Diet

The estimator uses dietary categories as an annualized proxy:

- High meat
- Medium meat
- Low meat
- Pescatarian
- Vegetarian
- Vegan

The diet factors are based on published research and are used as a documented proxy rather than as an India-specific food life-cycle database.

### 4. Waste

Waste emissions are estimated from daily household waste generation.

The model includes a recycling behavior input.

The current methodology applies a **50% reduction assumption only for consistently recycled waste**. This is explicitly treated as a project assumption rather than a universal scientific recycling factor.

### 5. Shopping

Shopping behavior is collected for qualitative AI guidance.

It is intentionally excluded from the numerical footprint because the project does not claim an unsupported India-specific shopping emission factor.

---

## AI Architecture

The project uses **IBM Granite locally through Ollama**.

### Local AI Stack

- Model: `granite4.2:3b-q4_K_M`
- Runtime: Ollama
- Endpoint: `http://localhost:11434`
- Python client: `ollama`

No cloud AI API key is required.

### What Python Does

Python is responsible for:

- Calculating category emissions
- Calculating total annual emissions
- Calculating category percentages
- Identifying the largest contributor
- Assigning the project-defined footprint classification
- Validating the AI response

### What Granite Does

Granite is responsible for:

- Explaining the user's largest contributor
- Producing a short summary
- Generating three practical sustainability actions
- Using the user's lifestyle context to personalize the wording

Granite is **not** responsible for:

- Calculating CO₂e
- Selecting emission factors
- Changing numerical results
- Creating unsupported emission factors
- Providing medical, nutrition, or fitness advice

---

## Responsible AI

The project follows several responsible-AI principles.

### Transparency

The application explains that the result is an estimate based on documented emission factors, proxies, and assumptions.

### Deterministic Numerical Calculation

All carbon numbers are calculated by Python instead of the LLM.

This reduces the risk of hallucinated numerical results.

### Privacy

The application does not require:

- User accounts
- A cloud database
- Personal profiles
- Cloud LLM inference

The Granite model runs locally through Ollama.

### Data Minimization

Only the lifestyle information required for the estimation and guidance is collected.

### Dietary Safety

Dietary categories are used only for carbon-footprint estimation.

The AI is instructed not to turn dietary information into:

- Medical advice
- Nutrition prescriptions
- Health claims
- Fitness recommendations

### Contradictory Recommendations

The AI response is validated so that recommendations should remain consistent with the user's selected dietary category.

For example, a vegetarian user should not receive a recommendation to increase meat consumption.

### No Unsupported Shopping Factor

Shopping behavior is used as qualitative context rather than inventing a numerical carbon factor.

### Human Understanding

The application presents the estimate as an awareness and educational tool rather than an exact measurement.

---

## Methodology

The methodology is maintained in:

```text
data/emission_factors.json
```

This file acts as the project's **single source of truth** for emission factors, source notes, proxies, and assumptions.

### Electricity

The project uses the Central Electricity Authority (CEA) grid-emission factor:

- **0.710 kg CO₂e/kWh**
- Source: CEA Version 21.0
- Period: FY2024-25 provisional factor

### Transport

India-specific road-transport factors are used where available, based on the India GHG Program / WRI / TERI / CII road-transport emission-factor work.

Examples include factors for:

- Bus
- Two-wheelers
- Petrol cars
- Diesel cars
- Hybrid vehicles
- CNG small cars

### Electric Vehicles

The project uses a documented representative EV electricity-consumption proxy:

- **0.106 kWh/km**

This is combined with the selected electricity grid factor.

The value is a documented project proxy and is **not presented as a universal efficiency value for every EV**.

### Diet

Dietary factors are based on the published research of Scarborough et al. (2014).

The factors are used as a proxy because the project does not have a complete India-specific food life-cycle inventory.

### Waste

The project uses an India-based waste-emission proxy of approximately:

- **1.0 kg CO₂e/kg waste**

The current value is based on an approximately 0.998 kg CO₂e/kg estimate from a Mumbai waste study and is rounded for implementation.

The recycling reduction applied for consistent recycling is a **project assumption** and should not be interpreted as a universal recycling emission factor.

### Shopping

No numerical shopping emission factor is used.

This avoids introducing an unsupported estimate based on spending or item counts.

---

## Household Allocation

The application asks for household size.

Household electricity and waste emissions are allocated equally among household members.

This is an allocation assumption for the estimator and does not represent a full household life-cycle assessment.

---

## Footprint Classification

The application uses project-defined annual thresholds:

- **Low:** below 2,000 kg CO₂e/year
- **Medium:** 2,000–4,000 kg CO₂e/year
- **High:** above 4,000 kg CO₂e/year

These categories are **project-defined labels**, not universal scientific standards.

---

## Requirements

- Python 3.10+
- Streamlit 1.63.0
- Plotly 6.x
- Ollama
- IBM Granite local model
- Git

The project does not require:

- React
- Node.js
- MongoDB
- LangChain
- Vector databases
- Docker
- Cloud AI API keys

---

## Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/debjithacks/Personal-Carbon-Footprint-Estimator.git
cd Personal-Carbon-Footprint-Estimator
```

### 2. Create a Virtual Environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

For development and testing:

```powershell
pip install -r requirements-dev.txt
```

### 4. Install Ollama

Install Ollama on your system and make sure the Ollama service is running.

Verify:

```powershell
ollama --version
```

### 5. Pull the Granite Model

```powershell
ollama pull granite4.2:3b-q4_K_M
```

Verify that the model is available:

```powershell
ollama list
```

### 6. Run the Application

```powershell
streamlit run app/main.py
```

The application will open in the browser.

---

## Testing

Run the complete automated test suite:

```powershell
pytest -q
```

The current automated test suite contains **87 tests** covering the deterministic calculator and Granite integration/validation behavior.

Example successful result:

```text
87 passed
```

The local Granite integration can also be tested with:

```powershell
python -m tests.test_granite_local
```

This verifies that the local IBM Granite model is reachable through Ollama and can generate guidance from Python-calculated results.

---

## User Interface

The Streamlit interface provides:

1. Transport selection
2. Daily travel distance
3. Vehicle category/fuel where applicable
4. Household size
5. Monthly electricity consumption
6. Dietary category
7. Daily waste generation
8. Recycling behavior
9. Shopping behavior
10. Carbon-footprint calculation
11. Category breakdown visualization
12. Largest contributor
13. Local Granite-generated explanation
14. Three personalized sustainability actions

The application also provides a reset option so the user can clear the current estimation and start again.

---

## Project Structure

```text
Personal Carbon Footprint Estimator/
│
├── app/
│   └── main.py
│
├── data/
│   └── emission_factors.json
│
├── services/
│   ├── __init__.py
│   ├── carbon_calculator.py
│   └── granite_service.py
│
├── tests/
│   ├── __init__.py
│   ├── test_calculator.py
│   ├── test_granite_local.py
│   └── test_granite_service.py
│
├── utils/
│   └── constants.py
│
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
└── requirements-dev.txt
```

---

## Privacy

The application is designed to work locally.

No account or cloud database is required.

The Granite model runs locally through Ollama, so lifestyle inputs used for the AI explanation do not need to be sent to a third-party hosted LLM API.

The project also avoids storing user lifestyle information as a persistent user profile.

---

## Limitations

This project is an educational and awareness-oriented estimator.

It does not provide:

- A certified carbon footprint
- A complete life-cycle assessment
- A complete India-specific food emission database
- A complete India-specific shopping emission database
- Vehicle-specific real-world fuel/electricity consumption for every model
- Universal scientific thresholds for Low/Medium/High classification

Emission factors and assumptions should be reviewed and updated when better, more relevant data becomes available.

---

## Responsible Use

The estimator should be used to understand relative lifestyle contributors and identify possible areas for lower-carbon choices.

Results should not be interpreted as an audited environmental inventory or a precise measurement of an individual's complete climate impact.

The application intentionally prioritizes:

- Transparent assumptions
- Reproducible calculations
- Local AI
- Data minimization
- Clear separation between deterministic calculations and generative AI

---

## SDG Alignment

The project primarily supports:

- **SDG 12 — Responsible Consumption and Production**
- **SDG 13 — Climate Action**

It supports sustainability awareness by helping users understand how everyday consumption and lifestyle patterns relate to estimated greenhouse-gas emissions.

---

## License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for the full license text.
