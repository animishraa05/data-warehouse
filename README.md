# FoodFlow Analytics — Data Warehouse & ETL Pipeline

A star-schema OLAP data warehouse for a simulated Indian food delivery company (think Swiggy/Zomato lite). End-to-end pipeline: synthetic data generation → ETL → PostgreSQL warehouse → analytical SQL queries → ML order volume forecasting → interactive dashboards — orchestrated daily by Apache Airflow.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Docker Compose                               │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────────┐   │
│  │  generate_   │───▶│  etl_        │───▶│  PostgreSQL 15      │   │
│  │  data.py     │    │  pipeline.py │    │  (foodflow_dw)      │   │
│  └──────────────┘    └──────────────┘    │                     │   │
│                                          │  Star Schema:       │   │
│  ┌──────────────┐                        │  5 dims + 2 facts   │   │
│  │  ml_forecast │◀──┐                    │  + 1 aggregate      │   │
│  └──────────────┘   │                    └──────────┬──────────┘   │
│                     │                               │              │
│  ┌──────────────┐   │              ┌────────────────┼──────────┐   │
│  │  analytical_ │   │              │                │          │   │
│  │  queries.sql │   │     ┌────────▼─────┐  ┌──────▼──────┐   │   │
│  └──────────────┘   │     │  Streamlit   │  │  Metabase   │   │   │
│                     │     │  Dashboard   │  │  BI Tool    │   │   │
│  data/raw/*.csv ◀───┘     │  :8501       │  │  :3000      │   │   │
│                            └──────────────┘  └─────────────┘   │   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Airflow 2.8.4 (daily @ 03:00 IST) — :8080             │   │
│  │  data_quality → etl → aggregates → forecast → notify    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- 4 GB RAM minimum

### One-Command Run

```bash
chmod +x run_all.sh && ./run_all.sh
```

This generates data, starts the database, runs ETL, generates the ML forecast, runs tests, and launches the interactive dashboard — all in one shot.

### Manual Step-by-Step

#### 1. Generate Synthetic Data

```bash
pip install -r requirements.txt
python scripts/generate_data.py
```

Creates 7 CSV files in `data/raw/` (~290K total rows).

#### 2. Start the Data Warehouse

```bash
docker compose up -d
```

| Service | URL | Credentials |
|---|---|---|
| PostgreSQL | `localhost:5433` | dw_user / secret |
| Airflow | `http://localhost:8080` | admin / admin |
| Metabase | `http://localhost:3000` | Set up on first visit |
| Streamlit | `http://localhost:8501` | No auth (dev) |

Schema auto-initialises on first container creation.

#### 3. Run the ETL Pipeline

```bash
# Standalone (one-shot)
python scripts/etl_pipeline.py
```

#### 4. Run ML Forecast

```bash
python scripts/ml_forecast.py
```

#### 5. Run Tests

```bash
pip install pytest
pytest tests/ -v
```

#### 6. Launch Dashboard

```bash
pip install streamlit plotly
streamlit run scripts/dashboard_app.py
```

#### 7. Teardown

```bash
docker compose down          # stop (data persists)
docker compose down -v       # stop + delete all data
```

---

## Data Model — Star Schema

### Dimension Tables

| Table | Rows | Grain | Key Features |
|---|---|---|---|
| `dim_date` | ~731 | 1 row per day | Indian holidays, weekend flags, peak season |
| `dim_customer` | 5,000 | 1 per customer | Segments: Premium-Loyal, Regular-New, etc. |
| `dim_restaurant` | 200 | 1 per restaurant | Rating bands, cuisine type |
| `dim_menu_item` | 1,500 | 1 per menu item | Price bands, category |
| `dim_delivery_agent` | 300 | 1 per agent | Performance tiers, vehicle type |

### Fact Tables

| Table | Rows | Grain | Measures |
|---|---|---|---|
| `fact_orders` | 80,000 | 1 per order | net_total, delivery_time, distance, is_delivered, is_cancelled |
| `fact_order_items` | ~200K | 1 per line item | quantity, unit_price, revenue |

### Additional Tables

| Table | Purpose |
|---|---|
| `agg_monthly_revenue` | Pre-aggregated monthly revenue by city + cuisine |
| `ml_order_forecast` | 30-day order volume predictions with confidence bounds |
| `ml_model_metrics` | Model evaluation (MAPE, MAE, RMSE) per forecast run |

---

## Dashboards

### Streamlit Dashboard (`:8501`)

Interactive Python-built dashboard with **10 pages**:

| Page | What it shows |
|---|---|
| **📊 Overview** | KPI strip, order status pie, platform bar, revenue trend, data model summary |
| **💰 Revenue** | Monthly revenue line chart + MoM growth bar chart |
| **🏆 Restaurants** | Top 10 by revenue, city breakdown, scatter plot |
| **👥 Customers** | Customer segment pie, CLV bar chart, distribution table |
| **🍔 Menu Items** | Top items by revenue, category breakdown |
| **❌ Cancellations** | Cancellation rate by city, scatter: volume vs rate |
| **⏰ Demand Patterns** | Day × Hour heatmap of delivered orders |
| **🚴 Delivery Agents** | Leaderboard bar chart, performance tier box plots |
| **📈 RFM Segmentation** | Segment bar chart + frequency vs monetary scatter with segment labels |
| **🔮 ML Forecast** | 30-day forecast with confidence bands, MAPE/MAE/RMSE metrics |

### Metabase BI (`:3000`)

Professional BI tool for ad-hoc querying:

1. Open `http://localhost:3000` and complete the setup wizard
2. Add PostgreSQL database:
   - Host: `foodflow_postgres` (or `localhost` if connecting from outside Docker)
   - Port: `5432` (or `5433` from host)
   - Database: `foodflow_dw`
   - User: `dw_user` / Password: `secret`
3. Use the **SQL Editor** to paste queries from `02_analytical_queries.sql`
4. Convert any query result to a chart and add to a dashboard

---

## Analytical Queries

| Query | Purpose | Technique |
|---|---|---|
| **Q1** | Monthly Revenue Trend | CTEs, LAG window function, MoM growth % |
| **Q2** | Top 10 Restaurants | GROUP BY, aggregates, delivery success rate |
| **Q3** | Customer Lifetime Value | LEFT JOIN, NTILE(4) quartile ranking, CLV tiers |
| **Q4** | Top 10 Menu Items | Multi-table JOIN, revenue by item |
| **Q5** | Cancellation Analysis | GROUP BY with HAVING filter, cancellation rate % |
| **Q6** | Hourly Demand Pattern | day_name × order_hour cross-tabulation |
| **Q7** | Agent Performance | Deliveries count, avg time, total value |
| **Q8** | RFM Segmentation | NTILE(5) scoring, 9-segment classification |
| **Q9** | Year-over-Year Revenue | Annual aggregation |
| **Q10** | Platform Distribution | Orders and revenue by platform |
| **Q11** | Aggregate Table Population | INSERT with ON CONFLICT upsert |

---

## ML Forecasting

| Property | Value |
|---|---|
| **Model** | Facebook Prophet |
| **Target** | Daily order volume |
| **Horizon** | 30 days |
| **Features** | `is_weekend` regressor, weekly + yearly seasonality |
| **Evaluation** | MAPE, MAE, RMSE (in-sample fit) |
| **Output** | `ml_order_forecast` table + `outputs/plots/forecast_plot.png` |

---

## ETL Pipeline

### Airflow DAG: `foodflow_daily_etl`

```
data_quality_check >> run_etl_pipeline >> refresh_aggregates >> ml_order_volume_forecast >> notify_success
```

Schedule: Daily at 03:00 IST. Trigger manually from Airflow UI.

### Transform Logic

Each dimension table is deduplicated, strings normalised, and derived features added:

- **dim_customer**: `tenure_days`, `customer_segment` (Premium-Loyal / Premium-New / Regular-Loyal / Regular-New)
- **dim_restaurant**: `rating_band` (Poor / Average / Good / Excellent)
- **dim_menu_item**: `price_band` (Budget / Affordable / Mid-Range / Premium)
- **dim_delivery_agent**: `experience_days`, `performance_tier`
- **dim_date**: Generated programmatically with Indian holidays and seasonal flags
- **fact_orders**: Merged orders + payments, `date_id` surrogate, derived flags and `time_of_day` bands
- **fact_order_items**: Bridge table linking orders to menu items with revenue

---

## Tests

```bash
pytest tests/ -v
```

| Test Class | Coverage |
|---|---|
| `TestTransformCustomers` | Deduplication, string normalisation, tenure_days, segmentation, required columns |
| `TestTransformRestaurants` | Rating bands, name normalisation |
| `TestTransformMenuItems` | Price bands |
| `TestTransformAgents` | Performance tiers, experience days |
| `TestBuildDimDate` | Date range, date_id format, weekend/holiday flags, required columns |
| `TestDataIntegrity` | Null key checks, boolean dtypes, numeric dtypes |

---

## Project Structure

```
foodflow/
├── 01_schema_ddl.sql            # PostgreSQL DDL — star schema
├── 02_analytical_queries.sql    # 11 analytical SQL queries
├── docker-compose.yml           # Infrastructure orchestration
├── foodflow_daily_etl.py        # Airflow DAG definition (root)
├── requirements.txt             # Python dependencies (pinned)
├── .env.example                 # Environment variable template
├── run_all.sh                   # End-to-end run script
├── README.md                    # This file
│
├── airflow/
│   └── dags/
│       └── foodflow_daily_etl.py  # DAG (copy here for Airflow discovery)
│
├── data/
│   └── raw/                       # Source CSVs
│
├── outputs/
│   └── plots/
│       └── forecast_plot.png      # Generated by ml_forecast.py
│
├── scripts/
│   ├── generate_data.py           # Synthetic data generator
│   ├── etl_pipeline.py            # Core ETL: extract → transform → load
│   ├── ml_forecast.py             # Prophet forecasting + evaluation
│   └── dashboard_app.py           # Streamlit interactive dashboard
│
└── tests/
    ├── __init__.py
    └── test_etl.py                # Unit tests for transform functions
```

---

## Configuration

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | PostgreSQL hostname |
| `DB_PORT` | `5433` | Host port (container uses 5432) |
| `DB_NAME` | `foodflow_dw` | Database name |
| `DB_USER` | `dw_user` | Database user |
| `DB_PASS` | `secret` | Database password |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL 15 (Alpine) |
| ETL | Python 3.10+, pandas 2.2.3, SQLAlchemy 2.0.27 |
| Orchestration | Apache Airflow 2.8.4 (LocalExecutor) |
| ML Forecasting | Facebook Prophet 1.1.5 |
| Dashboards | Streamlit + Plotly, Metabase |
| Testing | pytest |
| Data Generation | Faker 23.3.0 (en_IN locale) |
| Infrastructure | Docker Compose v3.9 |

---

## Design Decisions

- **SCD Type 1** on all dimensions — acceptable for academic scope
- **Full REPLACE** ETL — fine for ~80K rows, does not scale to millions
- **Degenerate dimensions** (`status`, `platform`, `method`) kept in fact table
- **0/1 integer flags** for `is_delivered`/`is_cancelled` — easy `SUM()` aggregation
- **Indian locale** — en_IN Faker, INR currency, Indian cities, Indian holidays

---

## Known Limitations

1. ETL is full-replace, not incremental
2. No transaction wrapping around ETL load
3. SCD Type 1 only — historical dimension changes lost
4. ML model has only in-sample evaluation (no holdout set)
5. `tqdm`, `loguru`, `scikit-learn` in requirements.txt but unused
