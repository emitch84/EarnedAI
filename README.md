# EarnedAI

EarnedAI is a portfolio-grade Streamlit application that demonstrates **Project Controls Intelligence** without reliance on LLMs or external cloud providers. It focuses on pure data analytics, Earned Value Management (EVM), and explainable anomaly detection for project management.

## Features

-   **Synthetic Data Generation**: Creates realistic project datasets including tasks, schedules, budgets, and actuals.
-   **EVM Engine**: Calculates core metrics:
    -   Planned Value (PV), Earned Value (EV), Actual Cost (AC)
    -   Cost Performance Index (CPI) & Schedule Performance Index (SPI)
    -   Estimate at Completion (EAC) & Variance at Completion (VAC)
-   **Explainable Anomaly Detection**: Rule-based statistical engine that scours project data for risks (e.g., "CPI < 0.85") and provides human-readable explanations.
-   **Interactive Dashboard**:
    -   High-level KPI cards.
    -   Performance Matrix (CPI vs SPI scatter plot).
    -   Risk Inspector with drill-down details.

## Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the Streamlit app locally:

```bash
streamlit run streamlit_app.py
```

## Structure

-   `streamlit_app.py`: Entry point for the UI.
-   `src/data_generator.py`: Generates randomized but logic-consistent project data.
-   `src/evm_engine.py`: Contains the math for EVM calculations.
-   `src/anomaly_detection.py`: Logic for flagging and explaining risky tasks.

## Deployment

This app is ready for **Streamlit Community Cloud**. 
1. Push to GitHub.
2. Connect Streamlit Cloud to the repo.
3. Deploy!

---
**Author**: Eric Mitch
**License**: MIT
