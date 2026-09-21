# Personal Carbon Footprint Estimator

A privacy-friendly Streamlit application that estimates an individual's
annual lifestyle carbon footprint in CO₂e and uses a locally running IBM
Granite model to generate personalized sustainability guidance.

## Overview

The application combines deterministic carbon calculations with local
generative AI.

The Python calculation engine is responsible for all numerical analysis.
IBM Granite does not calculate, modify, or reinterpret the numerical
footprint. It receives the calculated result and lifestyle context and
generates concise, personalized sustainability recommendations.

## Architecture

```text
User Input
    ↓
Input Validation
    ↓
Deterministic Carbon Calculator
    ↓
Annual CO₂e + Category Breakdown
    ↓
Largest Contributor Determined by Python
    ↓
Local IBM Granite via Ollama
    ↓
Validated Personalized Guidance
```

## Numeric Categories

The numerical footprint contains four categories:

- Transport
- Electricity
- Diet
- Waste

Shopping and consumption habits are collected as qualitative context only.
They are not included in the numerical CO₂e calculation because the project
methodology does not establish a defensible India-specific numeric factor.

## AI Architecture

IBM Granite runs locally through Ollama.

```text
Runtime: Ollama
Model: granite4.2:3b-q4_K_M
Endpoint: http://localhost:11434
```

The AI layer is deliberately separated from the numerical calculation.

Python determines:

- Total annual CO₂e
- Category-level CO₂e
- Category percentages
- Largest contributor
- Low / Medium / High classification

Granite generates:

- A short explanation
- Three personalized sustainability actions

The generated response is validated in Python before it is displayed.

## Responsible AI

The project follows several responsible AI principles:

- Numerical results are deterministic and calculated outside the language model.
- Granite receives already-calculated values rather than calculating the
  footprint itself.
- User diet preferences are explicitly respected.
- Contradictory dietary recommendations are rejected.
- Nutrition, medical, health, and fitness advice is outside the AI scope.
- Unsupported absolute environmental claims are rejected.
- Shopping is not assigned a fabricated numeric emission factor.
- The estimate is clearly presented as indicative rather than a complete
  life-cycle assessment.
- No user account or database is required for the core workflow.
- The local AI architecture avoids sending the user's lifestyle data to a
  cloud inference service.

## Methodology

Emission factors are stored in:

```text
data/emission_factors.json
```

This file is the single source of truth for the numeric emission factors used
by the calculation engine.

The methodology contains:

- India-specific transport factors where available
- Indian electricity grid factors
- A documented international diet proxy
- A documented India-specific waste-management proxy
- An explicitly disclosed recycling assumption
- Qualitative-only shopping context

The resulting estimate should be interpreted as an indicative lifestyle
estimate, not a complete life-cycle assessment.

## Requirements

- Python 3.10+
- Ollama
- IBM Granite model running locally through Ollama

## Local Setup

### 1. Create and activate a virtual environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Install Ollama

Install Ollama separately on the local machine.

Verify:

```powershell
ollama --version
```

### 4. Pull the Granite model

```powershell
ollama pull granite4.2:3b-q4_K_M
```

Verify:

```powershell
ollama list
```

You should see:

```text
granite4.2:3b-q4_K_M
```

### 5. Start the application

```powershell
streamlit run app\main.py
```

The application will open in the browser.

## Testing

Run the complete automated test suite:

```powershell
pytest -q
```

The test suite covers:

- Carbon calculation correctness
- Input validation
- Category breakdowns
- Largest-contributor selection
- Granite prompt construction
- Granite response validation
- Diet compatibility
- Invalid AI response handling

A separate manual test is available for real local Granite inference:

```powershell
python -m tests.test_granite_local
```

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
├── README.md
├── requirements.txt
└── requirements-dev.txt
```

## Limitations

This application provides an indicative estimate.

It is not a complete life-cycle assessment.

Some categories use documented proxies or assumptions. In particular:

- Diet uses an international research proxy.
- Waste uses an India-specific city-level proxy.
- Recycling reduction is an explicitly disclosed assumption.
- Shopping is qualitative-only.
- Low / Medium / High is a project-defined classification.
- AI recommendations are advisory and do not represent measured carbon
  savings.

## Privacy

The application does not require a user account or database for the core
workflow.

The current AI architecture runs IBM Granite locally through Ollama, so the
lifestyle inputs used to generate recommendations remain in the local
application workflow rather than being sent to a cloud AI API.

## License

Add the license selected for the project before publication.