# Market-Implied Metrics Web Application

A comprehensive dashboard for visualizing market-implied metrics, focusing on the Japanese market. This application provides insights into Bank of Japan (BoJ) rate probabilities, corporate default risks, and other key financial indicators, all presented in a premium, Bloomberg-inspired user interface.

## Features

- **BoJ Rate Probabilities**:
  - Visualizes the probability of Bank of Japan rate hikes or cuts.
  - Calculates implied rates based on market data (OIS rates).
  - Displays probabilities for "No Change", "Hike (+25bps)", and "Cut (-25bps)".

- **Corporation Default Probabilities**:
  - Calculates and displays default probabilities (PD) for major Japanese corporations.
  - Utilizes JSDA bond market data to estimate credit spreads and hazard rates.
  - Ranks issuers by risk (5-year PD).

- **Bloomberg-like UI**:
  - A dark-themed, data-centric user interface designed for financial professionals.
  - Features high-contrast colors (amber, green, red) for clear data visualization.
  - Responsive and dynamic layout.

## Tech Stack

- **Backend**: Python, Flask
- **Frontend**: Jinja2 Templates, HTML5, CSS3, Chart.js
- **Data Processing**: Pandas, NumPy
- **Dependency Management**: uv

## Installation

This project uses `uv` for dependency management.

1. **Install uv**:
    If you haven't installed `uv` yet, follow the instructions [here](https://github.com/astral-sh/uv).

2. **Clone the repository**:

    ```bash
    git clone <repository-url>
    cd market-implications
    ```

3. **Install dependencies**:

    ```bash
    uv sync
    ```

## Usage

### Running the Development Server

To start the web application locally:

```bash
uv run app/main.py
```

The application will be available at `http://localhost:8000`.

### Updating Data

The application relies on market data stored in `data/market_data.json`. This data is typically updated via a scheduled job (e.g., GitHub Actions), but you can trigger updates manually if the scripts are available (check `.github/workflows` for details).

## Project Structure

- **`app/`**: Contains the main Flask application (`main.py`) and route definitions.
- **`metrics/`**: Core logic for financial calculations (`calculations.py`, `credit.py`).
- **`data/`**: Stores raw and processed market data (JSON, CSV).
- **`templates/`**: HTML templates for the frontend.
- **`static/`**: Static assets (CSS, JavaScript, images).
- **`.github/`**: CI/CD workflows for automated data updates.
