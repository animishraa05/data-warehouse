# FoodFlow Analytics — End-to-End Connection Guide

## The Big Picture

```
GENERATE → EXTRACT → TRANSFORM → LOAD → QUERY → VISUALIZE
   │           │           │         │        │          │
   ▼           ▼           ▼         ▼        ▼          ▼
 CSV files  pandas     Clean DF   PostgreSQL  SQL     Streamlit
 (disk)     (RAM)      (RAM)      (disk)    queries    (browser)
```

Data 8 stages se guzra hai — har stage pe form change hota hai, location change hota hai. Ye document har connection ko trace karta hai.

---

## 1. Data Flow — Stage by Stage

### Stage 1: Data Generation

```
scripts/generate_data.py
    │
    ├── Faker(en_IN) — Indian locale se realistic names, cities, phones
    ├── numpy.random(seed=42) — Reproducible randomness
    │
    └──▶ data/raw/
         ├── customers.csv       (5,000 rows, 10 columns)
         ├── restaurants.csv     (200 rows, 9 columns)
         ├── menu_items.csv      (1,500 rows, 8 columns)
         ├── delivery_agents.csv (300 rows, 7 columns)
         ├── orders.csv          (80,000 rows, 10 columns)
         ├── order_items.csv     (~200,000 rows, 6 columns)
         └── payments.csv        (80,000 rows, 9 columns)
```

**Connection to Stage 2:** CSV files disk pe padi hain. ETL pipeline inhe read karegi.

---

### Stage 2: Extract

```
scripts/etl_pipeline.py → extract()
    │
    ├── pd.read_csv("data/raw/customers.csv")      → raw["customers"]
    ├── pd.read_csv("data/raw/restaurants.csv")    → raw["restaurants"]
    ├── pd.read_csv("data/raw/menu_items.csv")     → raw["menu_items"]
    ├── pd.read_csv("data/raw/delivery_agents.csv")→ raw["delivery_agents"]
    ├── pd.read_csv("data/raw/orders.csv")         → raw["orders"]
    ├── pd.read_csv("data/raw/order_items.csv")    → raw["order_items"]
    └── pd.read_csv("data/raw/payments.csv")       → raw["payments"]
```

**Input:** 7 CSV files (disk)  
**Output:** 7 pandas DataFrames (RAM)  
**Database involvement:** None.

**Connection to Stage 3:** Ye 7 DataFrames transform functions ko input jaayengi.

---

### Stage 3: Transform

```
Raw DataFrames (7)                     Clean DataFrames (7)
──────────────────                     ────────────────────
raw["customers"]      ──────────▶      dim_customer       (5,000 rows, 11 cols)
raw["restaurants"]    ──────────▶      dim_restaurant     (200 rows, 10 cols)
raw["menu_items"]     ──────────▶      dim_menu_item      (1,500 rows, 9 cols)
raw["delivery_agents"]──────────▶      dim_delivery_agent (300 rows, 8 cols)
(NEW, no CSV)         ──────────▶      dim_date           (731 rows, 13 cols)
raw["orders"]         ──────────┐
     +                         merge +  ──────────▶       fact_orders        (80,000 rows, 18 cols)
raw["payments"]         ──────────┘
raw["order_items"]      ──────────▶      fact_order_items   (~200K rows, 8 cols)
```

**What transform does to each:**

| Source | Transformation | Output |
|---|---|---|
| customers | Dedup → strip → title case → lowercase email → compute tenure_days → assign customer_segment | dim_customer |
| restaurants | Dedup → strip → title case → rating_band via pd.cut | dim_restaurant |
| menu_items | Dedup → price_band via pd.cut | dim_menu_item |
| delivery_agents | Dedup → strip → title case → compute experience_days → assign performance_tier | dim_delivery_agent |
| (code) | pd.date_range → extract day/month/year/week → mark holidays → mark peak season | dim_date |
| orders + payments | Dedup both → merge on order_id → parse timestamp → attach date_id → fill nulls → create is_delivered/is_cancelled flags → assign time_of_day band | fact_orders |
| order_items | Dedup → merge with fact_orders to get date_id + customer_id → rename line_total to revenue | fact_order_items |

**Input:** 7 raw DataFrames (RAM)  
**Output:** 7 clean DataFrames (RAM)  
**Database involvement:** None.

**Connection to Stage 4:** Ye clean DataFrames ab PostgreSQL mein likhe jaayenge.

---

### Stage 4: Load

```
Clean DataFrames (RAM)          Connection Path              PostgreSQL (disk)
─────────────────────           ──────────────               ─────────────────
dim_customer     ──to_sql──▶    pandas                        dim_date          (731 rows)
dim_restaurant   ──to_sql──▶       │                         dim_customer      (5,000 rows)
dim_menu_item    ──to_sql──▶       ▼                         dim_restaurant    (200 rows)
dim_delivery_... ──to_sql──▶    SQLAlchemy                    dim_menu_item     (1,500 rows)
dim_date         ──to_sql──▶       │                         dim_delivery_agent (300 rows)
fact_orders      ──to_sql──▶       ▼                         fact_orders       (80,000 rows)
fact_order_items ──to_sql──▶    psycopg2 (PostgreSQL driver)  fact_order_items  (~200K rows)
                                    │
                                    ▼
                              TCP connection
                              localhost:5433
```

**Load order (must follow dependency):**

1. `dim_date` — independent, no foreign keys
2. `dim_customer` — independent, no foreign keys
3. `dim_restaurant` — independent, no foreign keys
4. `dim_menu_item` — depends on dim_restaurant (FK: restaurant_id)
5. `dim_delivery_agent` — independent, no foreign keys
6. `fact_orders` — depends on all 5 dimensions (FKs: customer_id, restaurant_id, agent_id, date_id)
7. `fact_order_items` — depends on fact_orders (FK: order_id)

**After load:**
```
apply_indexes()
    │
    ├── CREATE INDEX idx_fact_orders_customer    ON fact_orders(customer_id)
    ├── CREATE INDEX idx_fact_orders_restaurant  ON fact_orders(restaurant_id)
    ├── CREATE INDEX idx_fact_orders_date        ON fact_orders(date_id)
    ├── CREATE INDEX idx_fact_orders_agent       ON fact_orders(agent_id)
    ├── CREATE INDEX idx_fact_oi_item            ON fact_order_items(item_id)
    ├── CREATE INDEX idx_fact_oi_order           ON fact_order_items(order_id)
    └── CREATE INDEX idx_dim_date_ym             ON dim_date(year, month)
```

**Input:** 7 clean DataFrames (RAM)  
**Output:** 7 tables in PostgreSQL (disk) + indexes  
**Connection mechanism:** pandas → SQLAlchemy → psycopg2 → TCP → PostgreSQL

**Connection to Stage 5:** Ab database mein data hai. SQL queries chal sakti hain.

---

### Stage 5: Analytical Queries

```
Terminal / psql / Metabase
    │
    ├── 02_analytical_queries.sql (11 queries)
    │
    ▼
PostgreSQL Query Engine
    │
    ├── Parse SQL
    ├── Build query plan (kaunse indexes use karne hain)
    ├── Execute plan (disk → buffer pool → compute)
    │
    └──▶ Result set
         year | month | revenue | mom_growth
         2023 | 1     | 10,00,000 | NULL
         2023 | 2     | 12,00,000 | 20.00%
         ...
```

**Query → Tables used mapping:**

| Query | Tables Touched | Indexes Used |
|---|---|---|
| Q1 (Monthly Revenue) | fact_orders, dim_date | idx_fo_date, idx_dd_yearmonth |
| Q2 (Top Restaurants) | fact_orders, dim_restaurant | idx_fo_restaurant |
| Q3 (CLV) | dim_customer, fact_orders | idx_fo_customer |
| Q4 (Top Items) | fact_order_items, dim_menu_item, dim_restaurant | idx_foi_item |
| Q5 (Cancellations) | fact_orders, dim_restaurant | idx_fo_restaurant, idx_dr_city |
| Q6 (Hourly Demand) | fact_orders, dim_date | idx_fo_date |
| Q7 (Agent Performance) | fact_orders, dim_delivery_agent | idx_fo_agent |
| Q8 (RFM) | dim_customer, fact_orders | idx_fo_customer, idx_dc_city_seg |
| Q9 (YoY Revenue) | fact_orders, dim_date | idx_fo_date, idx_dd_yearmonth |
| Q10 (Platform) | fact_orders | idx_fo_status |
| Q11 (Aggregate) | fact_orders, dim_date, dim_restaurant | idx_fo_date, idx_fo_restaurant, idx_dr_city |

**Connection to Stage 6:** Query results dashboard ya report mein jaate hain.

---

### Stage 6: ML Forecast

```
PostgreSQL                         Python (RAM)                     PostgreSQL
──────────                         ────────────                     ──────────
                                    │
fact_orders                         │
    │                               │
    │ SELECT full_date AS ds,       │
    │ COUNT(order_id) AS y          │
    │ WHERE status='Delivered'      │
    │ GROUP BY full_date            │
    │                               │
    └──▶ ~730 rows ──────────────▶ │  df (pandas DataFrame)
                                    │
                                    │  Prophet.fit(df)        ← Train
                                    │  Prophet.predict(30d)   ← Forecast
                                    │  evaluate_model()       ← MAPE/MAE/RMSE
                                    │  save_plot()            ← PNG file
                                    │
                                    ├──▶ ml_order_forecast    (30 rows)
                                    │   forecast_date, predicted_orders,
                                    │   lower_bound, upper_bound
                                    │
                                    └──▶ ml_model_metrics     (1 row appended)
                                        evaluated_at, mape, mae, rmse
```

**Connection path:**
```
PostgreSQL ──SQLAlchemy──▶ ml_forecast.py (Python) ──SQLAlchemy──▶ PostgreSQL
    (read)                                                             (write)
```

**Connection to Stage 7:** `ml_order_forecast` table dashboard mein display hoti hai.

---

### Stage 7: Dashboard (Streamlit)

```
User Browser                    Streamlit Server                 PostgreSQL
────────────                    ────────────────                 ──────────
                                    │
http://localhost:8501               │
    │                               │
    ▼                               │
Render HTML/JS                      │
    ▲                               │
    │                               │
    │◀── Plotly chart (JSON) ────── │
                                    │
                                    │  @st.cache_data(ttl=300)
                                    │  check cache → miss
                                    │
                                    │  SQL query:
                                    │  "SELECT ... FROM fact_orders ..."
                                    │
                                    │◀── Result DataFrame ────── │
                                    │
                                    │  px.line/px.bar/px.pie
                                    │  (Plotly figure)
                                    │
                                    │  Convert to JSON/HTML
                                    │
                                    └──▶ Send to browser
```

**Dashboard page → SQL query → tables used:**

| Page | Queries | Tables |
|---|---|---|
| 📊 Overview | KPI strip + status pie + platform bar + revenue trend | fact_orders, dim_date |
| 💰 Revenue | Monthly revenue + MoM growth | fact_orders, dim_date |
| 🏆 Restaurants | Top 10 by revenue | fact_orders, dim_restaurant |
| 👥 Customers | Segment pie + CLV top 20 | dim_customer, fact_orders |
| 🍔 Menu Items | Top 10 by revenue | fact_order_items, dim_menu_item, dim_restaurant |
| ❌ Cancellations | Cancellation rate by city | fact_orders, dim_restaurant |
| ⏰ Demand | Day × Hour heatmap | fact_orders, dim_date |
| 🚴 Agents | Leaderboard + box plots | fact_orders, dim_delivery_agent |
| 📈 RFM | 9-segment classification | dim_customer, fact_orders |
| 🔮 ML Forecast | Predictions + confidence bands | ml_order_forecast, ml_model_metrics |

**Connection path:**
```
Browser ──HTTP──▶ Streamlit ──SQLAlchemy──▶ PostgreSQL
                      │
                      └── Plotly ──JSON──▶ Browser
```

---

## 2. Docker Container Connections

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Docker Network                               │
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐    ┌────────────────┐ │
│  │ foodflow_postgres│    │foodflow_airflow_db│    │metabase_db     │ │
│  │ Port: 5432       │    │ Port: 5432        │    │ Port: 5432     │ │
│  │ Host Map: 5433   │    │ (internal only)   │    │ (internal only)│ │
│  │                  │    │                   │    │                │ │
│  │ Receives writes: │    │ Receives writes:  │    │ Receives writes│ │
│  │ - etl_pipeline.py│    │ - Airflow internal│    │ - Metabase     │ │
│  │ - ml_forecast.py │    │   state           │    │   internal     │ │
│  │                  │    │                   │    │                │ │
│  │ Receives reads:  │    └────────┬──────────┘    └───────┬────────┘ │
│  │ - dashboard_app  │             │                       │          │
│  │ - SQL queries    │             │                       │          │
│  │ - Metabase       │             ▼                       ▼          │
│  │                  │    ┌──────────────────┐    ┌────────────────┐ │
│  │ Schema init:     │    │ foodflow_airflow │    │ foodflow_metabase│ │
│  │ 01_schema_ddl.sql│    │ Port: 8080       │    │ Port: 3000     │ │
│  │ (first run only) │    │ (host: 8080)     │    │ (host: 3000)   │ │
│  └──────────────────┘    │                  │    │                │ │
         ▲                  │ Reads DAGs from: │    │ Connects to:   │ │
         │                  │ airflow/dags/    │    │ foodflow_postgres││
         │                  │                  │    │                │ │
         │                  │ Executes scripts:│    │ Reads from:    │ │
         │                  │ etl_pipeline.py  │    │ warehouse      │ │
         │                  │ ml_forecast.py   │    │ tables         │ │
         └──────────────────┴──────────────────┴────┴────────────────┘ │
                         │                                    │
                         ▼                                    ▼
              Volumes: dags, scripts,        Volumes: metabase_data,
                       data, outputs          metabase_db_data
```

### Connection Details

| From | To | How | Address |
|---|---|---|---|
| etl_pipeline.py (host) | foodflow_postgres | SQLAlchemy + psycopg2 | `localhost:5433` |
| ml_forecast.py (host) | foodflow_postgres | SQLAlchemy + psycopg2 | `localhost:5433` |
| dashboard_app.py (host) | foodflow_postgres | SQLAlchemy + psycopg2 | `localhost:5433` |
| foodflow_airflow (container) | foodflow_postgres | psycopg2 via PostgresOperator | `postgres:5432` |
| foodflow_airflow (container) | foodflow_airflow_db | psycopg2 | `airflow-db:5432` |
| foodflow_metabase (container) | foodflow_postgres | JDBC | `postgres:5432` |
| foodflow_metabase (container) | foodflow_metabase_db | JDBC | `metabase-db:5432` |
| Browser (host) | foodflow_airflow | HTTP | `localhost:8080` |
| Browser (host) | foodflow_metabase | HTTP | `localhost:3000` |
| Browser (host) | dashboard_app (Streamlit) | HTTP | `localhost:8501` |

### Why Different Addresses?

**Host machine se** PostgreSQL = `localhost:5433` (port mapped from container's 5432).

**Airflow container se** PostgreSQL = `postgres:5432` (Docker service name, internal port).

**Reason:** Container ke andar `localhost` = khud wo container. PostgreSQL alag container mein hai. Docker network mein containers ek dusre ko service name se resolve karte hain (built-in DNS).

---

## 3. Airflow DAG → Pipeline Connection

```
Clock → 03:00 IST (21:30 UTC daily)
    │
    ▼
Airflow Scheduler (inside foodflow_airflow container)
    │
    ├── Reads DAG file: airflow/dags/foodflow_daily_etl.py
    ├── Creates DAG run
    │
    ▼
Task 1: data_quality_check
    │
    ├── Type: PythonOperator (runs inside Airflow container)
    ├── Reads: data/raw/*.csv (mounted volume: ./data → /opt/airflow/foodflow/data)
    ├── Checks: File exists? Row count >= threshold?
    ├── ✅ Pass → Task 2
    ├── ❌ Fail → Stop pipeline, email alert
    │
    ▼
Task 2: run_etl_pipeline
    │
    ├── Type: BashOperator (runs inside Airflow container)
    ├── Command: cd /opt/airflow/foodflow && python scripts/etl_pipeline.py
    ├── Scripts location: mounted volume (./scripts → /opt/airflow/foodflow/scripts)
    ├── Data location: mounted volume (./data → /opt/airflow/foodflow/data)
    ├── DB connection: DB_HOST=postgres, DB_PORT=5432 (container-internal)
    ├── What it does: Extract → Transform → Load → PostgreSQL
    ├── ✅ Pass → Task 3
    ├── ❌ Fail → Retry (2 attempts, 5 min delay) → then email alert
    │
    ▼
Task 3: refresh_aggregates
    │
    ├── Type: PostgresOperator (direct SQL on foodflow_postgres)
    ├── Connection: foodflow_postgres (Airflow Connection, defined in docker-compose.yml)
    ├── SQL: TRUNCATE + INSERT INTO agg_monthly_revenue
    ├── What it does: Pre-computes monthly summary for BI performance
    ├── ✅ Pass → Task 4
    │
    ▼
Task 4: ml_order_volume_forecast
    │
    ├── Type: BashOperator (runs inside Airflow container)
    ├── Command: cd /opt/airflow/foodflow && python scripts/ml_forecast.py
    ├── What it does: Prophet trains → predicts 30 days → writes to ml_order_forecast + ml_model_metrics
    ├── Output: outputs/plots/forecast_plot.png (mounted volume)
    ├── ✅ Pass → Task 5
    │
    ▼
Task 5: notify_success
    │
    ├── Type: PythonOperator (runs inside Airflow container)
    ├── Sends: HTML email to analytics@foodflow.in
    └── DAG Complete ✅
```

### Volume Mounts in Airflow Container

| Host Path | Container Path | Purpose |
|---|---|---|
| `./airflow/dags` | `/opt/airflow/dags` | DAG files (Airflow auto-discovers .py files here) |
| `./scripts` | `/opt/airflow/foodflow/scripts` | ETL + ML pipeline scripts |
| `./data` | `/opt/airflow/foodflow/data` | Raw CSV source data |
| `./outputs` | `/opt/airflow/foodflow/outputs` | Generated plots and forecasts |

---

## 4. File-to-Table Mapping

### DDL → Tables

```
01_schema_ddl.sql
    │
    ├── CREATE TABLE dim_date          ──▶ dim_date
    ├── CREATE TABLE dim_customer      ──▶ dim_customer
    ├── CREATE TABLE dim_restaurant    ──▶ dim_restaurant
    ├── CREATE TABLE dim_menu_item     ──▶ dim_menu_item
    ├── CREATE TABLE dim_delivery_agent──▶ dim_delivery_agent
    ├── CREATE TABLE fact_orders       ──▶ fact_orders
    ├── CREATE TABLE fact_order_items  ──▶ fact_order_items
    ├── CREATE INDEX ... (13 indexes)  ──▶ Performance indexes
    └── CREATE TABLE agg_monthly_revenue ──▶ agg_monthly_revenue
```

### ETL → Tables

```
scripts/etl_pipeline.py
    │
    ├── build_dim_date()          ──▶ dim_date (731 rows)
    ├── transform_customers()     ──▶ dim_customer (5,000 rows)
    ├── transform_restaurants()   ──▶ dim_restaurant (200 rows)
    ├── transform_menu_items()    ──▶ dim_menu_item (1,500 rows)
    ├── transform_agents()        ──▶ dim_delivery_agent (300 rows)
    ├── transform_orders()        ──▶ fact_orders (80,000 rows)
    └── transform_order_items()   ──▶ fact_order_items (~200K rows)
```

### SQL Queries → Tables

```
02_analytical_queries.sql
    │
    ├── Q1 (Monthly Revenue)     ──▶ fact_orders + dim_date
    ├── Q2 (Top Restaurants)     ──▶ fact_orders + dim_restaurant
    ├── Q3 (CLV)                 ──▶ dim_customer + fact_orders
    ├── Q4 (Top Items)           ──▶ fact_order_items + dim_menu_item + dim_restaurant
    ├── Q5 (Cancellations)       ──▶ fact_orders + dim_restaurant
    ├── Q6 (Hourly Demand)       ──▶ fact_orders + dim_date
    ├── Q7 (Agent Performance)   ──▶ fact_orders + dim_delivery_agent
    ├── Q8 (RFM Segmentation)    ──▶ dim_customer + fact_orders
    ├── Q9 (YoY Revenue)         ──▶ fact_orders + dim_date
    ├── Q10 (Platform)           ──▶ fact_orders
    └── Q11 (Aggregate)          ──▶ fact_orders + dim_date + dim_restaurant
                                   ──▶ writes to agg_monthly_revenue
```

### ML → Tables

```
scripts/ml_forecast.py
    │
    ├── Reads: fact_orders + dim_date (aggregated daily counts)
    ├── Writes: ml_order_forecast (30 rows, full replace)
    └── Writes: ml_model_metrics (1 row per run, append)
```

### Dashboard → Tables

```
scripts/dashboard_app.py
    │
    ├── Overview page        ──▶ fact_orders, dim_date
    ├── Revenue page         ──▶ fact_orders, dim_date
    ├── Restaurants page     ──▶ fact_orders, dim_restaurant
    ├── Customers page       ──▶ dim_customer, fact_orders
    ├── Menu Items page      ──▶ fact_order_items, dim_menu_item, dim_restaurant
    ├── Cancellations page   ──▶ fact_orders, dim_restaurant
    ├── Demand page          ──▶ fact_orders, dim_date
    ├── Agents page          ──▶ fact_orders, dim_delivery_agent
    ├── RFM page             ──▶ dim_customer, fact_orders
    └── ML Forecast page     ──▶ ml_order_forecast, ml_model_metrics
```

### Tests → Functions

```
tests/test_etl.py
    │
    ├── TestTransformCustomers (7 tests)    ──▶ transform_customers()
    ├── TestTransformRestaurants (2 tests)  ──▶ transform_restaurants()
    ├── TestTransformMenuItems (1 test)     ──▶ transform_menu_items()
    ├── TestTransformAgents (2 tests)       ──▶ transform_agents()
    ├── TestBuildDimDate (5 tests)          ──▶ build_dim_date()
    └── TestDataIntegrity (3 tests)         ──▶ All transform functions
```

---

## 5. The Complete Journey of One Order

Let's trace `ORD0000001` through every stage:

```
STAGE 1: GENERATE (generate_data.py)
┌───────────────────────────────────────────────────────────────┐
│ Faker + numpy create one order:                               │
│   order_id=ORD0000001, customer_id=CUST00001,                 │
│   restaurant_id=REST0001, agent_id=AGT0001,                   │
│   timestamp=2023-03-15 13:22:45, status=Delivered             │
│                                                               │
│ Also creates matching payment in payments.csv:                │
│   order_id=ORD0000001, method=UPI, gross_total=450.00,        │
│   discount_amount=45.00, delivery_fee=30.00, net_total=435.00│
│                                                               │
│ Written to: orders.csv + payments.csv (disk)                  │
└───────────────────────────────────────────────────────────────┘
    │
    ▼
STAGE 2: EXTRACT (etl_pipeline.py → extract)
┌───────────────────────────────────────────────────────────────┐
│ pd.read_csv("orders.csv") → row found in DataFrame            │
│ pd.read_csv("payments.csv") → matching row found              │
│ Both in RAM, untouched                                        │
└───────────────────────────────────────────────────────────────┘
    │
    ▼
STAGE 3: TRANSFORM (etl_pipeline.py → transform_orders)
┌───────────────────────────────────────────────────────────────┐
│ orders.merge(payments) → one combined row:                    │
│   order_id=ORD0000001, customer_id=CUST00001,                 │
│   restaurant_id=REST0001, agent_id=AGT0001,                   │
│   order_timestamp=2023-03-15 13:22:45,                        │
│   method=UPI, gross_total=450.00,                             │
│   discount_amount=45.00, delivery_fee=30.00, net_total=435.00 │
│                                                               │
│ Derived fields added:                                         │
│   order_hour = 13                                             │
│   order_date = "2023-03-15"                                   │
│   date_id = 20230315  (looked up from dim_date mapping)       │
│   is_delivered = 1  (status == "Delivered")                   │
│   is_cancelled = 0  (status != "Cancelled")                   │
│   time_of_day = "Lunch"  (hour 13 falls in [11,14) bin)       │
└───────────────────────────────────────────────────────────────┘
    │
    ▼
STAGE 4: LOAD (etl_pipeline.py → load)
┌───────────────────────────────────────────────────────────────┐
│ df.to_sql("fact_orders", con=engine, if_exists="replace",     │
│           chunksize=5000, method="multi")                     │
│                                                               │
│ INSERT INTO fact_orders VALUES (...)                          │
│                                                               │
│ Written to: PostgreSQL foodflow_dw.fact_orders (disk)         │
└───────────────────────────────────────────────────────────────┘
    │
    ▼
STAGE 5: ANALYTICS (02_analytical_queries.sql)
┌───────────────────────────────────────────────────────────────┐
│ Q1: This order contributes to March 2023 revenue (₹435)       │
│ Q2: This order contributes to REST0001's total revenue        │
│ Q3: This order contributes to CUST00001's lifetime value      │
│ Q6: This order appears in Wednesday × 13:00 cell in heatmap   │
│ Q7: This order contributes to AGT0001's delivery count        │
└───────────────────────────────────────────────────────────────┘
    │
    ▼
STAGE 6: ML FORECAST (ml_forecast.py)
┌───────────────────────────────────────────────────────────────┐
│ SQL query: SELECT full_date, COUNT(*) WHERE status='Delivered'│
│ Result: 2023-03-15 count includes this order (+1)             │
│ Prophet uses this as one data point in training               │
│ Forecast output may be slightly affected by this order        │
└───────────────────────────────────────────────────────────────┘
    │
    ▼
STAGE 7: DASHBOARD (dashboard_app.py)
┌───────────────────────────────────────────────────────────────┐
│ Overview page: total_orders count includes this order         │
│ Overview page: net_revenue includes ₹435                      │
│ Revenue page: March 2023 bar includes ₹435                    │
│ Restaurants page: REST0001's bar includes ₹435                │
│ Customers page: CUST00001's CLV includes ₹435                 │
│ Demand page: Wed×13 heatmap cell includes +1                  │
│ Agents page: AGT0001's delivery count includes +1             │
└───────────────────────────────────────────────────────────────┘
    │
    ▼
STAGE 8: AIRFLOW (foodflow_daily_etl DAG)
┌───────────────────────────────────────────────────────────────┐
│ Daily 03:00 IST:                                              │
│   Task 1: data_quality_check → orders.csv exists ✅            │
│   Task 2: ETL re-run → this order re-loaded (replace)          │
│   Task 3: agg_monthly_revenue refreshed → March 2023 updated   │
│   Task 4: ML forecast retrained → this order in training data  │
│   Task 5: Email sent → "ETL Success"                           │
└───────────────────────────────────────────────────────────────┘
```

---

## 6. Data Size at Each Stage

```
Stage              │ Where    │ Size        │ Rows
───────────────────┼──────────┼─────────────┼──────────
generate_data.py   │ disk     │ ~22 MB      │ ~290,000
extract()          │ RAM      │ ~50 MB      │ ~290,000
transform()        │ RAM      │ ~80 MB      │ ~288,440
load()             │ disk (DB)│ ~100 MB*    │ ~288,440
analytical queries │ RAM      │ < 1 MB      │ < 1,000 (results)
ML training        │ RAM      │ ~1 MB       │ ~730
ML output          │ disk (DB)│ < 1 KB      │ 31 (30 forecast + 1 metric)
Dashboard query    │ RAM      │ < 100 KB    │ < 1,000
Dashboard render   │ browser  │ < 1 MB      │ Charts
```

*Includes indexes and PostgreSQL overhead.

---

## 7. Component Summary — One Line Each

| File/Component | What It Does | What It Reads From | What It Writes To |
|---|---|---|---|
| `generate_data.py` | Creates synthetic data | Nothing (seeds from 42) | `data/raw/*.csv` (disk) |
| `01_schema_ddl.sql` | Defines database structure | Nothing | PostgreSQL tables + indexes |
| `etl_pipeline.py` | Cleans data and loads to DB | `data/raw/*.csv` (disk) | PostgreSQL tables (disk) |
| `02_analytical_queries.sql` | Answers business questions | PostgreSQL tables | Terminal output (results) |
| `ml_forecast.py` | Predicts future order volume | PostgreSQL (fact_orders) | PostgreSQL (ml_order_forecast + ml_model_metrics) + `outputs/plots/forecast_plot.png` |
| `dashboard_app.py` | Shows interactive charts | PostgreSQL tables | Browser (HTML/JS) |
| `foodflow_daily_etl.py` | Automates the pipeline | `data/raw/*.csv` (via Airflow) | PostgreSQL + email |
| `docker-compose.yml` | Runs all services | `01_schema_ddl.sql`, `airflow/dags/`, `scripts/`, `data/`, `outputs/` | Docker containers |
| `test_etl.py` | Validates transform logic | Nothing (creates own fixtures) | Terminal output (pass/fail) |
