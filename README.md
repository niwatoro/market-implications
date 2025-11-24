# Market-Implied Metrics Web Application

A comprehensive dashboard for visualizing market-implied metrics, focusing on the Japanese market. This application provides insights into Bank of Japan (BoJ) rate probabilities, corporate default risks, and other key financial indicators, all presented in a premium, Bloomberg-inspired user interface.

## Installation

This project uses `uv` for dependency management.

1. **Install uv**:
    If you haven't installed `uv` yet, follow the instructions [here](https://github.com/astral-sh/uv).

2. **Clone the repository**:

    ```bash
    git clone https://github.com/niwatoro/market-implications.git
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

## Theory

### Rate Hike/Cut Probability

Assume that the next monetary policy decision is scheduled in $D_\text{pre}$. Let $r_\text{post}$ denote the OIS rate with maturity $D_\text{pre}+D_\text{post}$ days. The current one-day rate is denoted by $r_\text{pre}$ and the one-day rate that will prevail after the policy decision is represented by the random variable $r$.

Here, $r_\text{post}$, interpreted as the average rate over the entire period $[0,D_\text{pre}+D_\text{post}]$, can be written as:

$$r_\text{post}={r_\text{pre}D_\text{pre}+\mathbb E[r]D_\text{post}\over D_\text{pre}+D_\text{post}}.$$

Solving this expression for $\mathbb E[r]$ yields:

$$\mathbb E[r]={r_\text{post}(D_\text{pre}+D_\text{post})-r_\text{pre}D_\text{pre}\over D_\text{post}}.$$

Suppose further that a central bank hikes/cuts the policy rate by $\Delta$, so that the post-decision rate is $r_\text{pre}+\Delta$. Thus, the probability $p$ of a rate hike/cut is given by:

$$p={\mathbb E[r]-r_\text{pre}\over\Delta}.$$

### Probability of Default

Consider a corporate bond with yield $y_\text{corp}$. Let $y_\text{gov}$ denote the yield of a government bond with the same maturity. The spread $s$ is given by:

$$s=y_\text{corp}-y_\text{gov}.$$

Let $R$ be the recovery rate, which is set uniformly to 10% from [historical data](https://www.bloomberg.co.jp/news/articles/2023-11-14/S43427T0AFB401).

The harzard rate $\lambda$ can then be written as:

$$\lambda={s\over 1-R}.$$

Assuming a constant hazard rate, the probability of default $PD$ over a time horizon $T$ is given by:

$$PD(T) = 1-\exp(-\lambda T).$$

In practice, even for the same issuer, yields--and hence hazard rates--can differ across maturities. For simplicity, however, the hazard rate for each issuer is approximated by its average maturities.
