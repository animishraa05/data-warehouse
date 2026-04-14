# FoodFlow Analytics — Comprehensive Project Report

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Context and Objectives](#2-project-context-and-objectives)
3. [Business Domain Model](#3-business-domain-model)
4. [System Architecture](#4-system-architecture)
5. [Infrastructure Layer](#5-infrastructure-layer)
6. [Data Generation Engine](#6-data-generation-engine)
7. [Data Warehouse Schema (DDL)](#7-data-warehouse-schema-ddl)
8. [Dimension Tables — Deep Dive](#8-dimension-tables--deep-dive)
9. [Fact Tables — Deep Dive](#9-fact-tables--deep-dive)
10. [Aggregate Tables](#10-aggregate-tables)
11. [ETL Pipeline — Extract](#11-etl-pipeline--extract)
12. [ETL Pipeline — Transform](#12-etl-pipeline--transform)
13. [ETL Pipeline — Load](#13-etl-pipeline--load)
14. [Apache Airflow Orchestration](#14-apache-airflow-orchestration)
15. [Analytical SQL Queries](#15-analytical-sql-queries)
16. [Machine Learning Forecasting](#16-machine-learning-forecasting)
17. [Model Evaluation Metrics](#17-model-evaluation-metrics)
18. [Interactive Dashboard (Streamlit)](#18-interactive-dashboard-streamlit)
19. [Metabase BI Integration](#19-metabase-bi-integration)
20. [Testing Strategy](#20-testing-strategy)
21. [Docker Compose Infrastructure](#21-docker-compose-infrastructure)
22. [Project Structure and File Map](#22-project-structure-and-file-map)
23. [Configuration and Environment Variables](#23-configuration-and-environment-variables)
24. [Dependencies and Package Management](#24-dependencies-and-package-management)
25. [Design Decisions and Rationale](#25-design-decisions-and-rationale)
26. [Known Limitations](#26-known-limitations)
27. [Future Enhancements](#27-future-enhancements)
28. [Performance Characteristics](#28-performance-characteristics)
29. [Data Quality and Validation](#29-data-quality-and-validation)
30. [Deployment and Operations](#30-deployment-and-operations)
31. [Appendix — Full SQL Queries](#31-appendix--full-sql-queries)

---

## 1. Executive Summary

FoodFlow Analytics is a complete, end-to-end data warehouse and analytics platform designed for the Indian food delivery market. It simulates the full data stack of a food delivery company operating at the scale of companies like Swiggy or Zomato, albeit with synthetic data rather than real production traffic.

The project encompasses every layer of a modern data engineering pipeline:

- **Synthetic data generation**: 7 interconnected datasets totalling ~290,000 rows, generated with the Faker library using the `en_IN` (Indian) locale for realistic names, cities, phone numbers, and cultural context.
- **Star schema data warehouse**: A properly normalised OLAP-optimised schema in PostgreSQL 15 with 5 dimension tables, 2 fact tables, and 1 aggregate table, all with performance indexes and foreign key constraints.
- **ETL pipeline**: A Python-based extract-transform-load pipeline using pandas and SQLAlchemy that reads CSV source files, applies data cleaning and feature engineering, and loads the transformed data into the warehouse.
- **Orchestration**: An Apache Airflow DAG that schedules and monitors the entire pipeline daily, with data quality checks, error handling, and email notifications.
- **Analytical queries**: 11 production-grade SQL queries covering revenue trends, customer lifetime value, RFM segmentation, cancellation analysis, hourly demand patterns, and agent performance — using advanced window functions, CTEs, and windowed aggregations.
- **Machine learning**: A Facebook Prophet time-series model that forecasts 30-day order volume with weekend regressors, weekly and yearly seasonality, and provides evaluation metrics (MAPE, MAE, RMSE).
- **Interactive dashboards**: Two dashboard options — a Streamlit app with 10 interactive pages using Plotly charts, and a Metabase BI tool for ad-hoc SQL querying with chart generation.
- **Testing**: 20 unit tests covering transformation logic, data integrity, and boundary conditions.
- **Infrastructure as code**: Docker Compose orchestration for all services (PostgreSQL, Airflow, Metabase) with health checks and persistent volumes.

This report documents every single component, decision, and implementation detail of the project.

---

## 2. Project Context and Objectives

### 2.1 Why This Project Exists

FoodFlow Analytics is designed as an academic/portfolio-grade project that demonstrates competence in data engineering, analytics, and machine learning. It serves as a proof-of-concept for a complete data platform — from raw data ingestion to production dashboards — in a domain that is immediately understandable: food delivery.

### 2.2 Primary Objectives

1. **Demonstrate star schema design**: Build a proper Kimball-style dimensional model with clearly defined grains, surrogate keys, and relationship integrity.
2. **Implement a working ETL pipeline**: Create a repeatable, automated data transformation pipeline that converts raw source data into a structured warehouse.
3. **Enable business intelligence**: Provide analytical queries that answer real business questions — revenue trends, customer value, operational efficiency, demand patterns.
4. **Add predictive analytics**: Implement time-series forecasting to show that the data stack can look forward, not just backward.
5. **Automate with orchestration**: Use Apache Airflow to demonstrate production-grade pipeline scheduling, monitoring, and alerting.
6. **Visualise with dashboards**: Provide interactive, visual analytics that stakeholders can use without writing SQL.
7. **Ensure quality through testing**: Validate transformation logic with unit tests.

### 2.3 Scope and Scale

| Metric | Value |
|---|---|
| Total datasets generated | 7 |
| Total rows across all datasets | ~290,000 |
| Date range covered | 2023-01-01 to 2024-12-31 (2 years) |
| Cities modelled | 10 Indian cities |
| Restaurants | 200 |
| Menu items | 1,500 |
| Customers | 5,000 |
| Delivery agents | 300 |
| Orders | 80,000 |
| Order line items | ~200,000 |
| Dimension tables | 5 |
| Fact tables | 2 |
| Aggregate tables | 1 |
| Analytical SQL queries | 11 |
| Dashboard pages | 10 |
| Unit tests | 20 |
| Docker services | 5 (PostgreSQL DW, Airflow DB, Airflow, Metabase DB, Metabase) |

### 2.4 Target Market Context

The project is specifically designed for the Indian food delivery market:
- All names, cities, and phone numbers use the `en_IN` Faker locale
- Currency is in Indian Rupees (INR)
- Indian public holidays are marked in the date dimension (Republic Day, Independence Day, Gandhi Jayanti, Diwali)
- Festive/winter season flag covers October–January (peak ordering season in India)
- Payment methods reflect Indian preferences: UPI (40%), Credit Card (20%), Debit Card (15%), Cash on Delivery (15%), Wallet (10%)
- Cuisine types include North Indian, South Indian, Biryani alongside international options
- Order timestamps are biased toward lunch (12–14) and dinner (19–22) hours, matching real Indian food ordering behaviour

---

## 3. Business Domain Model

### 3.1 Entity Relationships

The food delivery business model involves the following key entities and their relationships:

```
Customer ───────┐
                │
Restaurant ─────┼──── Order ──── OrderItem ──── MenuItem
                │                 │
Delivery Agent ─┘                 │
                                  │
                                Payment
```

**Narrative of relationships:**
- A **Customer** places **Orders** through the platform. Each order belongs to exactly one customer.
- An **Order** is fulfilled by one **Restaurant**, which provides one or more **Menu Items**.
- An **Order** contains one or more **Order Items** (line items), each linking to a specific **Menu Item**.
- A **Delivery Agent** is assigned to deliver each **Order**.
- An **Order** generates exactly one **Payment** record, capturing the financial transaction.
- A **Restaurant** offers many **Menu Items** (approximately 7–8 per restaurant on average).

### 3.2 Business Events and Processes

1. **Customer Registration**: A new customer signs up, creating a record in `dim_customer` with their city, age group, gender, and premium status.
2. **Restaurant Onboarding**: A restaurant joins the platform, creating a record in `dim_restaurant` with its cuisine type, rating, and preparation time.
3. **Order Placement**: A customer places an order via App-Android, App-iOS, or Web, selecting items from a restaurant.
4. **Order Preparation**: The restaurant prepares the items (tracked via `avg_prep_time_min`).
5. **Order Delivery**: A delivery agent picks up and delivers the order (tracked via `delivery_time_min` and `distance_km`).
6. **Payment Processing**: The payment is processed via UPI, Credit Card, Debit Card, COD, or Wallet.
7. **Order Completion**: The order is either Delivered, Cancelled, or Refunded.

### 3.3 Key Business Questions Answered

The project answers these business questions through its analytical queries and dashboards:
- How is revenue trending month-over-month? Is it growing or declining?
- Which restaurants are our top performers by revenue?
- What is the lifetime value of each customer? Who are our most valuable customers?
- Which menu items generate the most revenue?
- What is the cancellation rate by city and cuisine type? Where should we focus improvement?
- When do customers order most? What are the peak hours and days?
- How are delivery agents performing? Who are our top performers?
- How can we segment customers using Recency-Frequency-Monetary (RFM) analysis?
- How does order volume vary by platform (App vs Web)?
- What is the forecasted order volume for the next 30 days?

---

## 4. System Architecture

### 4.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Docker Compose Environment                   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    DATA GENERATION LAYER                     │   │
│  │                                                              │   │
│  │  scripts/generate_data.py                                    │   │
│  │  └─ Uses Faker (en_IN), numpy, pandas                        │   │
│  │  └─ Generates 7 CSVs into data/raw/                          │   │
│  └──────────────────────────────┬──────────────────────────────┘   │
│                                 │                                  │
│                                 ▼                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    EXTRACT TRANSFORM LOAD                     │   │
│  │                                                              │   │
│  │  scripts/etl_pipeline.py                                     │   │
│  │  ├─ EXTRACT: Read 7 CSVs from data/raw/                      │   │
│  │  ├─ TRANSFORM: Clean, deduplicate, feature engineer           │   │
│  │  └─ LOAD: Bulk insert into PostgreSQL via SQLAlchemy          │   │
│  └──────────────────────────────┬──────────────────────────────┘   │
│                                 │                                  │
│                                 ▼                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   DATA WAREHOUSE (OLAP)                      │   │
│  │                                                              │   │
│  │  PostgreSQL 15 (foodflow_dw)                                 │   │
│  │  ├─ dim_date (731 rows)                                      │   │
│  │  ├─ dim_customer (5,000 rows)                                │   │
│  │  ├─ dim_restaurant (200 rows)                                │   │
│  │  ├─ dim_menu_item (1,500 rows)                               │   │
│  │  ├─ dim_delivery_agent (300 rows)                            │   │
│  │  ├─ fact_orders (80,000 rows)                                │   │
│  │  ├─ fact_order_items (~200K rows)                            │   │
│  │  ├─ agg_monthly_revenue (~2K rows)                           │   │
│  │  └─ ml_order_forecast (30 rows)                              │   │
│  └──────────┬───────────────────────────────────┬──────────────┘   │
│             │                                   │                  │
│    ┌────────▼────────┐              ┌───────────▼─────────────┐   │
│    │  ANALYTICS      │              │  ML FORECASTING         │   │
│    │                 │              │                         │   │
│    │ 02_analytical_  │              │ scripts/ml_forecast.py  │   │
│    │ queries.sql     │              │ ├─ Prophet model        │   │
│    │ (11 queries)    │              │ ├─ MAPE/MAE/RMSE        │   │
│    └─────────────────┘              │ └─ Forecast plot + DW   │   │
│                                     └─────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                    DASHBOARD LAYER                         │   │
│  │                                                            │   │
│  │  Streamlit (:8501)          Metabase (:3000)               │   │
│  │  └─ 10 interactive pages   └─ Ad-hoc SQL + charts          │   │
│  │  └─ Plotly charts           └─ BI dashboard builder        │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                 ORCHESTRATION LAYER                        │   │
│  │                                                            │   │
│  │  Apache Airflow 2.8.4 (:8080)                              │   │
│  │  DAG: foodflow_daily_etl                                   │   │
│  │  Schedule: Daily at 03:00 IST                              │   │
│  │  Tasks: DQ check → ETL → Aggregates → Forecast → Notify    │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                   TESTING LAYER                            │   │
│  │                                                            │   │
│  │  tests/test_etl.py (20 unit tests)                         │   │
│  │  └─ Covers: dedup, normalisation, feature engineering      │   │
│  └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Data Flow

```
Source Systems          Data Engineering          Analytics & Consumption
    │                        │                           │
    │                        │                           │
    ▼                        ▼                           ▼
┌──────────┐          ┌──────────────┐          ┌──────────────────────┐
│ Raw CSVs │  ─────▶  │ ETL Pipeline │  ─────▶  │ PostgreSQL DW        │
│ (7 files)│          │ (pandas)     │          │ (star schema)        │
└──────────┘          └──────────────┘          └──────┬───────────────┘
                                                       │
                                              ┌────────┼────────┐
                                              ▼        ▼        ▼
                                         ┌────────┐ ┌──────┐ ┌──────┐
                                         │ SQL    │ │ ML   │ │ Dash │
                                         │ Queries│ │ Model│ │board │
                                         └────────┘ └──────┘ └──────┘
```

### 4.3 Control Flow (Orchestration)

```
Airflow Scheduler (daily @ 03:00 IST)
    │
    ▼
┌─────────────────┐    ┌──────────────┐    ┌────────────────┐    ┌──────────────┐    ┌──────────────┐
│ Data Quality    │───▶│ Run ETL      │───▶│ Refresh        │───▶│ ML Forecast  │───▶│ Notify       │
│ Check           │    │ Pipeline     │    │ Aggregates     │    │              │    │ Success      │
│ (PythonOperator)│    │ (BashOperator)│   │ (PostgresOp)   │    │ (BashOperator)│   │ (PythonOp)   │
└─────────────────┘    └──────────────┘    └────────────────┘    └──────────────┘    └──────────────┘
```

---

## 5. Infrastructure Layer

### 5.1 Docker Compose Services

The entire infrastructure is managed through a single `docker-compose.yml` file with 5 services:

#### 5.1.1 PostgreSQL Data Warehouse (`foodflow_postgres`)

- **Image**: `postgres:15-alpine`
- **Container name**: `foodflow_postgres`
- **Host port**: `5433` (mapped to container port `5432`)
- **Database**: `foodflow_dw`
- **User**: `dw_user`
- **Password**: `secret`
- **Volumes**:
  - `postgres_data`: Persistent volume for database data
  - `./01_schema_ddl.sql` → `/docker-entrypoint-initdb.d/01_schema.sql`: Auto-executes the DDL on first container creation
- **Health check**: `pg_isready -U dw_user -d foodflow_dw` every 10 seconds

The schema initialization script runs only once — on the very first container creation when the data volume is empty. Subsequent `docker-compose up` commands (without `-v`) reuse the existing volume and do NOT re-run the DDL.

#### 5.1.2 Airflow Metadata Database (`foodflow_airflow_db`)

- **Image**: `postgres:15-alpine`
- **Container name**: `foodflow_airflow_db`
- **Database**: `airflow`
- **User**: `airflow`
- **Password**: `airflow`
- **Volumes**: `airflow_db_data` — persistent volume for Airflow's internal state (DAG runs, task history, connection configs)
- **Health check**: `pg_isready -U airflow` every 10 seconds

This is a separate PostgreSQL instance dedicated to Airflow's own metadata. It is not shared with the data warehouse database to maintain separation of concerns.

#### 5.1.3 Apache Airflow (`foodflow_airflow`)

- **Image**: `apache/airflow:2.8.4`
- **Container name**: `foodflow_airflow`
- **Host port**: `8080` (Airflow Web UI)
- **Executor**: `LocalExecutor` (single-process, suitable for development)
- **Command**: Multi-step startup:
  1. `pip install pandas numpy sqlalchemy psycopg2-binary faker prophet` — installs pipeline dependencies
  2. `airflow db init` — initialises Airflow's metadata tables
  3. `airflow users create` — creates admin user (admin/admin)
  4. `airflow scheduler &` — starts the scheduler in background
  5. `airflow webserver` — starts the web UI in foreground
- **Environment variables**:
  - `AIRFLOW_CONN_FOODFLOW_POSTGRES`: PostgreSQL connection string for the DAG's PostgresOperator tasks
  - `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`: Database connection parameters for Python scripts running inside the container
- **Volume mounts**:
  - `./airflow/dags` → `/opt/airflow/dags`: DAG files (Airflow auto-discovers Python files here)
  - `./scripts` → `/opt/airflow/foodflow/scripts`: ETL and ML pipeline scripts
  - `./data` → `/opt/airflow/foodflow/data`: Raw CSV source data
  - `./outputs` → `/opt/airflow/foodflow/outputs`: Generated output files (plots, forecasts)

#### 5.1.4 Metabase Database (`foodflow_metabase_db`)

- **Image**: `postgres:15-alpine`
- **Container name**: `foodflow_metabase_db`
- **Database**: `metabase`
- **User**: `metabase`
- **Password**: `metabase_secret`
- **Volumes**: `metabase_db_data`
- **Health check**: `pg_isready -U metabase` every 10 seconds

#### 5.1.5 Metabase BI Tool (`foodflow_metabase`)

- **Image**: `metabase/metabase:v0.50.14`
- **Container name**: `foodflow_metabase`
- **Host port**: `3000`
- **Depends on**: `foodflow_postgres` (healthy) and `foodflow_metabase_db` (healthy)
- **Volumes**: `metabase_data` — persistent storage for Metabase application data
- **Environment variables**:
  - `MB_DB_TYPE`: postgres
  - `MB_DB_HOST`: metabase-db
  - `MB_DB_PORT`: 5432
  - `MB_DB_USER`: metabase
  - `MB_DB_PASS`: metabase_secret
  - `MB_DB_DBNAME`: metabase

### 5.2 Service Dependency Chain

```
foodflow_postgres ──────────────────────────┬──▶ foodflow_airflow
                                            │
foodflow_airflow_db ────────────────────────┼──▶ foodflow_airflow
                                            │
foodflow_postgres ──────────────────────────┤
foodflow_metabase_db ───────────────────────┼──▶ foodflow_metabase
```

### 5.3 Port Allocation

| Service | Host Port | Container Port | Protocol |
|---|---|---|---|
| PostgreSQL DW | 5433 | 5432 | TCP |
| Airflow Web UI | 8080 | 8080 | TCP |
| Metabase | 3000 | 3000 | TCP |
| Airflow DB | — | 5432 | Internal only |
| Metabase DB | — | 5432 | Internal only |

---

## 6. Data Generation Engine

### 6.1 Overview

The synthetic data generator (`scripts/generate_data.py`) is a Python script that uses the Faker library with the `en_IN` locale to produce realistic, culturally appropriate Indian food delivery data. All random seeds are fixed (`random.seed(42)`, `np.random.seed(42)`) to ensure reproducibility — every run generates the exact same dataset.

### 6.2 Generation Configuration

| Parameter | Value | Rationale |
|---|---|---|
| `N_CUSTOMERS` | 5,000 | Realistic customer base for a mid-size food delivery operation |
| `N_RESTAURANTS` | 200 | ~40 restaurants per major city across 10 cities |
| `N_MENU_ITEMS` | 1,500 | ~7.5 items per restaurant on average |
| `N_DELIVERY_AGENTS` | 300 | ~1.5 agents per restaurant, realistic agent-to-restaurant ratio |
| `N_ORDERS` | 80,000 | ~110 orders per day over 730 days, realistic for a growing platform |
| `START_DATE` | 2023-01-01 | Clean 2-year window |
| `END_DATE` | 2024-12-31 | End of the dataset period |

### 6.3 Reference Data

#### Cities (10)
Mumbai, Delhi, Bengaluru, Hyderabad, Chennai, Kolkata, Pune, Ahmedabad, Jaipur, Indore

These are India's top 10 food delivery markets, covering metros (Mumbai, Delhi, Bengaluru), tier-1 cities (Hyderabad, Chennai, Kolkata, Pune), and emerging markets (Ahmedabad, Jaipur, Indore).

#### Cuisine Types (10)
North Indian, South Indian, Chinese, Italian, Continental, Fast Food, Biryani, Desserts, Beverages, Snacks

#### Menu Categories (7)
Starters, Main Course, Breads, Rice, Beverages, Desserts, Combos

#### Order Status Distribution
- **Delivered**: ~67% (4 out of 6 entries in the selection array)
- **Cancelled**: ~17% (1 out of 6)
- **Refunded**: ~17% (1 out of 6)

This distribution matches real-world food delivery industry benchmarks where approximately two-thirds of orders are successfully delivered.

#### Payment Method Distribution
- **UPI**: 40% (dominant in India due to BHIM UPI infrastructure)
- **Credit Card**: 20%
- **Debit Card**: 15%
- **Cash on Delivery**: 15% (still significant in Indian markets)
- **Wallet**: 10% (PayTM, PhonePe, etc.)

### 6.4 Data Generation Process

#### Step 1: Customers (5,000 rows)

Each customer record includes:
- `customer_id`: Sequential ID (CUST00001 to CUST05000)
- `full_name`: Generated by Faker (Indian names like "Rajesh Kumar", "Priya Sharma")
- `email`: Faker-generated email addresses
- `phone`: Indian phone numbers (Faker `en_IN` locale)
- `city`: Random selection from 10 cities (uniform distribution)
- `registration_date`: Between 2021-01-01 and 2022-12-31 (all customers registered before the order period starts)
- `age_group`: Weighted distribution — 25-34 (35%), 18-24 (25%), 35-44 (20%), 45-54 (12%), 55+ (8%)
- `gender`: Male (55%), Female (42%), Other (3%)
- `is_premium`: 18% premium, 82% regular

#### Step 2: Restaurants (200 rows)

Each restaurant record includes:
- `restaurant_id`: Sequential ID (REST0001 to REST0200)
- `name`: Faker company name + "Kitchen" suffix
- `city`: Random from 10 cities
- `cuisine_type`: Random from 10 cuisine types
- `rating`: Uniform distribution from 2.5 to 5.0
- `total_reviews`: Random integer from 50 to 5,000
- `avg_prep_time_min`: Random integer from 15 to 50 minutes
- `is_veg_only`: 20% vegetarian-only restaurants
- `onboarded_date`: Between 2020-01-01 and 2022-12-31

#### Step 3: Menu Items (1,500 rows)

Each menu item includes:
- `item_id`: Sequential ID (ITEM00001 to ITEM01500)
- `restaurant_id`: Random assignment to existing restaurants
- `item_name`: Generated from Faker's business-sounding phrases (e.g., "Integrated Chicken Curry")
- `category`: Random from 7 menu categories
- `price`: Uniform distribution from ₹50 to ₹600
- `is_available`: 92% available, 8% unavailable
- `is_veg`: 55% vegetarian, 45% non-vegetarian
- `calories`: Random integer from 100 to 900

#### Step 4: Delivery Agents (300 rows)

Each agent record includes:
- `agent_id`: Sequential ID (AGT0001 to AGT0300)
- `name`: Faker-generated Indian names
- `city`: Random from 10 cities
- `vehicle`: Bike (65%), Scooter (30%), Bicycle (5%)
- `rating`: Uniform distribution from 3.0 to 5.0 (all agents meet minimum quality threshold)
- `joined_date`: Between 2021-01-01 and 2022-12-31

#### Step 5: Orders (80,000 rows)

This is the most complex generation step. Each order includes:
- `order_id`: Sequential ID (ORD0000001 to ORD0080000)
- `customer_id`: Random assignment from existing customers
- `restaurant_id`: Random assignment from existing restaurants
- `agent_id`: Random assignment from existing agents
- `order_timestamp`: Generated with a **realistic time-of-day bias**:
  - Hour weights: `[1,1,1,1,1,1,2,3,4,5,6,8,10,10,8,6,5,6,8,10,10,8,5,2]`
  - This creates peaks at lunch hours (12–14) and dinner hours (19–22)
  - Low activity at night (0–5 AM), moderate morning activity (6–11 AM)
- `delivery_time_min`: Random integer from 20 to 75 minutes
- `distance_km`: Uniform distribution from 0.5 to 15.0 km
- `status`: Delivered (67%), Cancelled (17%), Refunded (17%)
- `discount_pct`: 0% (40%), 5% (15%), 10% (20%), 15% (10%), 20% (10%), 25% (5%)
- `platform`: App-Android (45%), App-iOS (35%), Web (20%)

#### Step 6: Order Items (~200,000 rows)

For each of the 80,000 orders:
- Number of items per order: weighted distribution — 1 item (20%), 2 items (35%), 3 items (25%), 4 items (15%), 5 items (5%)
- Items are randomly sampled from the 1,500 menu items
- Each line item includes quantity (1 = 65%, 2 = 25%, 3 = 10%)
- `line_total` = quantity × unit_price
- `order_item_id`: Sequential ID (OI00000001 onwards)

#### Step 7: Payments (80,000 rows)

Payment records are derived from order items:
- `gross_total`: Sum of all `line_total` values for the order (aggregated from order_items)
- `discount_amount`: gross_total × discount_pct / 100
- `delivery_fee`: Random uniform from ₹20 to ₹60
- `net_total`: gross_total - discount_amount + delivery_fee
- For cancelled orders, `net_total` is set to 0
- `method`: UPI (40%), Credit Card (20%), Debit Card (15%), COD (15%), Wallet (10%)
- Payment `status`: "Success" for delivered orders, "Refunded" for cancelled/refunded orders

---

## 7. Data Warehouse Schema (DDL)

### 7.1 Schema Design Principles

The schema follows the **Kimball dimensional modelling** methodology (star schema), optimised for Online Analytical Processing (OLAP) workloads:

1. **Fact tables at the centre**: Contain measurable business events (orders, order items)
2. **Dimension tables around**: Provide context for facts (who, what, where, when)
3. **Denormalised dimensions**: Each dimension is self-contained — no need to JOIN dimensions to get related information
4. **Surrogate keys on dim_date**: Integer-based `date_id` (YYYYMMDD) for fast range scans instead of DATE type comparisons
5. **Degenerate dimensions**: Attributes like `status`, `platform`, `method` that don't warrant separate dimension tables are kept directly in the fact table
6. **Binary flags as integers**: `is_delivered` and `is_cancelled` stored as SMALLINT (0/1) instead of BOOLEAN for easy `SUM()` aggregation
7. **Foreign key constraints**: All dimension references are enforced at the database level
8. **Performance indexes**: Composite and single-column indexes on all FK columns and frequently filtered columns

### 7.2 Table Creation Order

Tables are created in dependency order — dimensions first, then facts. The DROP statements are in reverse order to handle foreign key constraints:

```
DROP: fact_order_items → fact_orders → dim_date → dim_customer → dim_restaurant → dim_menu_item → dim_delivery_agent
CREATE: dim_date → dim_customer → dim_restaurant → dim_menu_item → dim_delivery_agent → fact_orders → fact_order_items
```

### 7.3 Complete Table Index Summary

| Table | Indexes |
|---|---|
| `dim_date` | PRIMARY KEY (date_id), UNIQUE (full_date), idx_dd_yearmonth (year, month) |
| `dim_customer` | PRIMARY KEY (customer_id), idx_dc_city_seg (city, customer_segment) |
| `dim_restaurant` | PRIMARY KEY (restaurant_id), idx_dr_city (city) |
| `dim_menu_item` | PRIMARY KEY (item_id), FK to dim_restaurant(restaurant_id) |
| `dim_delivery_agent` | PRIMARY KEY (agent_id) |
| `fact_orders` | PRIMARY KEY (order_id), idx_fo_customer, idx_fo_restaurant, idx_fo_agent, idx_fo_date, idx_fo_status, idx_fo_date_status |
| `fact_order_items` | PRIMARY KEY (order_item_id), idx_foi_order, idx_foi_item, idx_foi_date |

---

## 8. Dimension Tables — Deep Dive

### 8.1 dim_date (Calendar Dimension)

**Grain**: One row per calendar day  
**Row count**: 731 (2023-01-01 through 2024-12-31, inclusive)  
**Primary key**: `date_id` (INTEGER, YYYYMMDD format)

| Column | Type | Description | Example |
|---|---|---|---|
| `date_id` | INTEGER | Surrogate key | 20240115 |
| `full_date` | DATE | Actual date value | 2024-01-15 |
| `day` | SMALLINT | Day of month | 15 |
| `month` | SMALLINT | Month number | 1 |
| `month_name` | VARCHAR(10) | Month name | "January" |
| `quarter` | SMALLINT | Quarter (1–4) | 1 |
| `year` | SMALLINT | Year | 2024 |
| `week` | SMALLINT | ISO week number (1–53) | 3 |
| `day_of_week` | SMALLINT | 0=Monday, 6=Sunday | 0 (Monday) |
| `day_name` | VARCHAR(10) | Day name | "Monday" |
| `is_weekend` | BOOLEAN | Saturday or Sunday | FALSE |
| `is_holiday` | BOOLEAN | Indian public holiday | FALSE |
| `is_peak_season` | BOOLEAN | October–January (festive + winter) | TRUE (January) |

**Indian public holidays marked**:
- January 26 (Republic Day) — both 2023 and 2024
- August 15 (Independence Day) — both 2023 and 2024
- October 2 (Gandhi Jayanti) — both 2023 and 2024
- October 24 (Diwali 2023) / October 31 (Diwali 2024)

**Peak season logic**: Months 10, 11, 12, and 1 — covering India's festive season (Navratri, Diwali, Dussehra) and winter months, which typically see increased food ordering activity.

**Design note**: The `date_id` is stored as an INTEGER (not DATE) because integer range scans are faster in PostgreSQL for time-series queries. A query like `WHERE date_id BETWEEN 20240101 AND 20240131` performs better than `WHERE full_date >= '2024-01-01' AND full_date <= '2024-01-31'` on large datasets.

### 8.2 dim_customer (Customer Dimension)

**Grain**: One row per unique registered customer  
**Row count**: 5,000  
**Primary key**: `customer_id` (VARCHAR(10))  
**SCD Type**: Type 1 (overwrites on change)

| Column | Type | Description | Example |
|---|---|---|---|
| `customer_id` | VARCHAR(10) | Unique customer identifier | "CUST00001" |
| `full_name` | VARCHAR(100) | Customer's full name | "Rajesh Kumar" |
| `email` | VARCHAR(150) | Email address | "rajesh@gmail.com" |
| `phone` | VARCHAR(20) | Phone number | "+91 98765 43210" |
| `city` | VARCHAR(50) | Customer's city | "Mumbai" |
| `age_group` | VARCHAR(10) | Age bracket | "25-34" |
| `gender` | VARCHAR(10) | Gender identity | "Male", "Female", "Other" |
| `is_premium` | BOOLEAN | Premium subscriber status | TRUE |
| `registration_date` | DATE | When customer registered | 2022-06-15 |
| `tenure_days` | INTEGER | Days since registration (computed) | 930 |
| `customer_segment` | VARCHAR(20) | Derived segment label | "Premium-Loyal" |

**Customer Segmentation Logic** (computed in ETL):

| Condition | Segment |
|---|---|
| Premium AND tenure ≥ 365 days | "Premium-Loyal" |
| Premium AND tenure < 365 days | "Premium-New" |
| NOT Premium AND tenure ≥ 365 days | "Regular-Loyal" |
| NOT Premium AND tenure < 365 days | "Regular-New" (default) |

This segmentation enables analysis of customer behaviour based on both their subscription tier and loyalty (tenure), which is a standard approach in subscription-based business models.

### 8.3 dim_restaurant (Restaurant Dimension)

**Grain**: One row per partner restaurant  
**Row count**: 200  
**Primary key**: `restaurant_id` (VARCHAR(8))  
**SCD Type**: Type 1

| Column | Type | Description | Example |
|---|---|---|---|
| `restaurant_id` | VARCHAR(8) | Unique restaurant identifier | "REST0001" |
| `name` | VARCHAR(150) | Restaurant name | "Spice Kitchen" |
| `city` | VARCHAR(50) | Restaurant's city | "Mumbai" |
| `cuisine_type` | VARCHAR(50) | Primary cuisine | "North Indian" |
| `rating` | NUMERIC(3,1) | Customer rating (2.5–5.0) | 4.2 |
| `rating_band` | VARCHAR(15) | Rating category (computed) | "Good" |
| `total_reviews` | INTEGER | Number of reviews | 1,250 |
| `avg_prep_time_min` | SMALLINT | Average food prep time | 25 |
| `is_veg_only` | BOOLEAN | Vegetarian-only flag | FALSE |
| `onboarded_date` | DATE | When restaurant joined platform | 2022-05-10 |

**Rating Band Classification**:

| Rating Range | Band |
|---|---|
| 0.0 – 2.5 | "Poor" |
| 2.5 – 3.5 | "Average" |
| 3.5 – 4.2 | "Good" |
| 4.2 – 5.0 | "Excellent" |

These bands are defined using `pd.cut` with `right=True` (right-inclusive bins), meaning a rating of exactly 3.5 falls in "Average" (the bin (2.5, 3.5]).

### 8.4 dim_menu_item (Menu Item Dimension)

**Grain**: One row per menu offering  
**Row count**: 1,500  
**Primary key**: `item_id` (VARCHAR(9))

| Column | Type | Description | Example |
|---|---|---|---|
| `item_id` | VARCHAR(9) | Unique item identifier | "ITEM00001" |
| `restaurant_id` | VARCHAR(8) | FK to dim_restaurant | "REST0001" |
| `item_name` | VARCHAR(200) | Menu item name | "Butter Chicken" |
| `category` | VARCHAR(50) | Menu category | "Main Course" |
| `price` | NUMERIC(8,2) | Item price in INR | 250.00 |
| `price_band` | VARCHAR(15) | Price category (computed) | "Mid-Range" |
| `is_available` | BOOLEAN | Currently available | TRUE |
| `is_veg` | BOOLEAN | Vegetarian indicator | TRUE |
| `calories` | SMALLINT | Calorie count | 450 |

**Price Band Classification**:

| Price Range (₹) | Band |
|---|---|
| 0 – 100 | "Budget" |
| 100 – 200 | "Affordable" |
| 200 – 350 | "Mid-Range" |
| 350+ | "Premium" |

**Note**: The `restaurant_id` column creates a foreign key relationship to `dim_restaurant`, making this a "mini-dimension" that belongs to the restaurant hierarchy.

### 8.5 dim_delivery_agent (Delivery Agent Dimension)

**Grain**: One row per registered delivery partner  
**Row count**: 300  
**Primary key**: `agent_id` (VARCHAR(7))  
**SCD Type**: Type 1

| Column | Type | Description | Example |
|---|---|---|---|
| `agent_id` | VARCHAR(7) | Unique agent identifier | "AGT0001" |
| `name` | VARCHAR(100) | Agent's full name | "Suresh Yadav" |
| `city` | VARCHAR(50) | Agent's base city | "Mumbai" |
| `vehicle` | VARCHAR(20) | Delivery vehicle type | "Bike" |
| `rating` | NUMERIC(3,1) | Agent rating (3.0–5.0) | 4.5 |
| `performance_tier` | VARCHAR(20) | Performance category (computed) | "Good" |
| `experience_days` | INTEGER | Days since joining (computed) | 800 |
| `joined_date` | DATE | When agent joined platform | 2022-10-15 |

**Performance Tier Classification**:

| Rating Range | Tier |
|---|---|
| 0.0 – 3.5 | "Below Average" |
| 3.5 – 4.2 | "Average" |
| 4.2 – 4.7 | "Good" |
| 4.7 – 5.0 | "Top Performer" |

**Vehicle Distribution**: Bike (65%), Scooter (30%), Bicycle (5%) — reflecting the reality that most Indian food delivery agents use two-wheelers, with bikes being the most common due to speed and range.

---

## 9. Fact Tables — Deep Dive

### 9.1 fact_orders (Order-Level Fact)

**Grain**: One row per order  
**Row count**: 80,000  
**Primary key**: `order_id` (VARCHAR(11))

This is the central fact table of the star schema. Every business metric related to orders flows from this table.

#### Foreign Keys (4)

| Column | References | Purpose |
|---|---|---|
| `customer_id` | dim_customer(customer_id) | Who placed the order |
| `restaurant_id` | dim_restaurant(restaurant_id) | Which restaurant fulfilled it |
| `agent_id` | dim_delivery_agent(agent_id) | Who delivered it |
| `date_id` | dim_date(date_id) | When it happened (surrogate key) |

#### Degenerate Dimensions (5)

These are attributes that are part of the order event itself but don't warrant separate dimension tables:

| Column | Type | Values |
|---|---|---|
| `order_timestamp` | TIMESTAMP | Exact order time |
| `order_hour` | SMALLINT | Hour extracted from timestamp (0–23) |
| `time_of_day` | VARCHAR(15) | Night, Morning, Lunch, Afternoon, Dinner, Late Night |
| `platform` | VARCHAR(15) | App-iOS, App-Android, Web |
| `status` | VARCHAR(15) | Delivered, Cancelled, Refunded |

#### Binary Flags (2)

| Column | Type | Logic | Purpose |
|---|---|---|---|
| `is_delivered` | SMALLINT | 1 if status="Delivered", else 0 | Easy `SUM()` for delivered count |
| `is_cancelled` | SMALLINT | 1 if status="Cancelled", else 0 | Easy `SUM()` for cancelled count |

Storing these as SMALLINT (not BOOLEAN) allows queries like `SUM(is_delivered)` instead of `COUNT(*) FILTER (WHERE status = 'Delivered')`, which is both faster and more intuitive.

#### Measures (7)

| Column | Type | Unit | Description |
|---|---|---|---|
| `delivery_time_min` | SMALLINT | Minutes | Time from order to delivery |
| `distance_km` | NUMERIC(5,2) | Kilometers | Delivery distance |
| `discount_pct` | SMALLINT | Percentage | Discount applied (0–25) |
| `gross_total` | NUMERIC(10,2) | INR | Sum of all item prices before discount |
| `discount_amount` | NUMERIC(10,2) | INR | Monetary value of discount |
| `delivery_fee` | NUMERIC(7,2) | INR | Delivery charge |
| `net_total` | NUMERIC(10,2) | INR | gross_total - discount_amount + delivery_fee |

**Degenerate Dimension**: `method` (VARCHAR(25)) — payment method (UPI, Credit Card, Debit Card, Cash on Delivery, Wallet). This is a degenerate dimension because there are only 5 possible values and creating a separate dimension table would add no analytical value.

#### Time-of-Day Bands

| Hour Range | Label | Business Meaning |
|---|---|---|
| 0–5 | "Night" | Very late / early morning |
| 6–10 | "Morning" | Breakfast / early orders |
| 11–13 | "Lunch" | Lunch peak |
| 14–16 | "Afternoon" | Post-lunch lull |
| 17–19 | "Dinner" | Early dinner |
| 20–23 | "Late Night" | Late-night orders |

### 9.2 fact_order_items (Line-Item Fact)

**Grain**: One row per line item within an order  
**Row count**: ~200,409 (variable based on random generation)  
**Primary key**: `order_item_id` (VARCHAR(11))

This is a bridge/fact table that enables product-level analytics. While `fact_orders` tells us about the order as a whole, `fact_order_items` tells us which specific items were purchased.

#### Foreign Keys (4)

| Column | References | Purpose |
|---|---|---|
| `order_id` | fact_orders(order_id) | Which order this item belongs to |
| `item_id` | dim_menu_item(item_id) | Which menu item |
| `customer_id` | dim_customer(customer_id) | Denormalised from fact_orders for convenience |
| `date_id` | dim_date(date_id) | Denormalised from fact_orders for convenience |

#### Measures (3)

| Column | Type | Unit | Description |
|---|---|---|---|
| `quantity` | SMALLINT | Count | Number of units ordered |
| `unit_price` | NUMERIC(8,2) | INR | Price per unit |
| `revenue` | NUMERIC(10,2) | INR | quantity × unit_price |

**Denormalisation note**: `customer_id` and `date_id` are included in this table even though they could be obtained by joining through `order_id` → `fact_orders`. This is a deliberate denormalisation that simplifies queries — instead of a three-table join (fact_order_items → fact_orders → dim_date), analysts can query fact_order_items with date_id directly.

---

## 10. Aggregate Tables

### 10.1 agg_monthly_revenue

**Purpose**: Pre-aggregated summary table for BI performance. Instead of computing aggregations from 80,000 fact_orders rows every time, this table provides ~2,000 pre-computed rows.

**Primary key**: Composite (year, month, city, cuisine_type)  
**Approximate rows**: 2,064 (24 months × 10 cities × ~8.6 cuisine types per city on average)

| Column | Type | Description |
|---|---|---|
| `year` | SMALLINT | Year of orders |
| `month` | SMALLINT | Month number |
| `month_name` | VARCHAR(10) | Month name |
| `city` | VARCHAR(50) | Restaurant city |
| `cuisine_type` | VARCHAR(50) | Restaurant cuisine |
| `total_orders` | INTEGER | Count of all orders |
| `delivered_orders` | INTEGER | Count of delivered orders |
| `cancelled_orders` | INTEGER | Count of cancelled orders |
| `gross_revenue` | NUMERIC(15,2) | Sum of gross_total |
| `net_revenue` | NUMERIC(15,2) | Sum of net_total |
| `avg_order_value` | NUMERIC(10,2) | Average net_total for delivered orders |
| `avg_delivery_min` | NUMERIC(6,2) | Average delivery time for delivered orders |

This table is refreshed after every ETL run using a TRUNCATE + INSERT pattern in the Airflow DAG's `refresh_aggregates` task.

### 10.2 ml_order_forecast

**Purpose**: Stores 30-day order volume predictions from the Prophet model.

| Column | Type | Description |
|---|---|---|
| `forecast_date` | DATE | Predicted date |
| `predicted_orders` | INTEGER | Point estimate (yhat) |
| `lower_bound` | INTEGER | 80% confidence interval lower bound |
| `upper_bound` | INTEGER | 80% confidence interval upper bound |
| `created_at` | TIMESTAMP | When the forecast was generated |

**Rows**: 30 (one per future day)  
**Update strategy**: Full REPLACE on each ML run.

### 10.3 ml_model_metrics

**Purpose**: Stores model evaluation metrics for each forecast run, enabling tracking of model quality over time.

| Column | Type | Description |
|---|---|---|
| `evaluated_at` | TIMESTAMP | When the evaluation was performed |
| `mape` | FLOAT | Mean Absolute Percentage Error (in-sample) |
| `mae` | FLOAT | Mean Absolute Error (in-sample) |
| `rmse` | FLOAT | Root Mean Squared Error (in-sample) |
| `n_observations` | INTEGER | Number of training observations |

**Update strategy**: APPEND — each run adds a new row, allowing historical tracking of model performance.

---

## 11. ETL Pipeline — Extract

### 11.1 Pipeline Entry Point

The ETL pipeline is orchestrated by `scripts/etl_pipeline.py`. The main entry function is `run_pipeline()`, which executes the pipeline in three phases: EXTRACT → TRANSFORM → LOAD.

### 11.2 Database Connection

The `get_engine()` function constructs a PostgreSQL connection URL from environment variables with sensible defaults:

```python
url = (
    f"postgresql+psycopg2://{os.getenv('DB_USER','dw_user')}:"
    f"{os.getenv('DB_PASS','secret')}@"
    f"{os.getenv('DB_HOST','localhost')}:"
    f"{os.getenv('DB_PORT','5433')}/"
    f"{os.getenv('DB_NAME','foodflow_dw')}"
)
```

The engine is configured with `pool_size=5` and `max_overflow=10`, providing a connection pool suitable for the bulk-insert workload.

### 11.3 Extract Phase

The `extract()` function reads all 7 CSV files from `data/raw/` into pandas DataFrames:

```python
def extract() -> dict[str, pd.DataFrame]:
    tables = ["customers", "restaurants", "menu_items",
              "delivery_agents", "orders", "order_items", "payments"]
```

**Validation**: If any required file is missing, a `FileNotFoundError` is raised with a clear message: `"Raw file missing: {path} → run generate_data.py first"`.

**Logging**: Each file read is logged with row count and column count:
```
  customers                   5,000 rows  10 cols
  restaurants                   200 rows  9 cols
  menu_items                  1,500 rows  8 cols
  ...
```

---

## 12. ETL Pipeline — Transform

### 12.1 Data Quality Logging

The `_log_quality()` helper function is called at the start of each transform function to assess data quality:

1. **Null analysis**: Calculates the null percentage for every column. If any column has nulls above 0%, it logs a warning with the specific columns and percentages.
2. **Duplicate detection**: Counts total duplicate rows. If any exist, it logs a warning with the count.

This provides visibility into data quality issues without blocking the pipeline.

### 12.2 dim_customer Transformation

**Steps**:
1. **Deduplication**: `drop_duplicates(subset="customer_id")` — removes exact duplicate customer records while preserving the first occurrence
2. **Date parsing**: `pd.to_datetime("registration_date")`
3. **String normalisation**:
   - `full_name`: `.str.strip().str.title()` — removes leading/trailing whitespace, converts to Title Case ("  rajesh kumar  " → "Rajesh Kumar")
   - `email`: `.str.lower().str.strip()` — converts to lowercase, removes whitespace
   - `city`: `.str.strip()` — removes whitespace
4. **Boolean cast**: `is_premium` → `astype(bool)`
5. **Feature engineering — tenure_days**:
   - `REFERENCE_DATE = pd.Timestamp("2024-12-31")`
   - `tenure_days = REFERENCE_DATE - registration_date` (in days)
6. **Feature engineering — customer_segment**:
   - Uses `np.select()` with four conditions based on `is_premium` and `tenure_days >= 365`
7. **Column selection**: Returns exactly 11 columns in the defined order

### 12.3 dim_restaurant Transformation

**Steps**:
1. **Deduplication**: `drop_duplicates(subset="restaurant_id")`
2. **String normalisation**:
   - `name`: `.str.strip().str.title()`
   - `city`: `.str.strip()`
3. **Date parsing**: `pd.to_datetime("onboarded_date")`
4. **Feature engineering — rating_band**:
   - Uses `pd.cut()` with bins `[0, 2.5, 3.5, 4.2, 5.0]` and labels `["Poor", "Average", "Good", "Excellent"]`
   - `right=True` means bins are right-inclusive: (0, 2.5], (2.5, 3.5], (3.5, 4.2], (4.2, 5.0]
5. **Column selection**: Returns exactly 10 columns

### 12.4 dim_menu_item Transformation

**Steps**:
1. **Deduplication**: `drop_duplicates(subset="item_id")`
2. **Feature engineering — price_band**:
   - Uses `pd.cut()` with bins `[0, 100, 200, 350, float("inf")]` and labels `["Budget", "Affordable", "Mid-Range", "Premium"]`
   - Right-inclusive bins
3. **Column selection**: Returns exactly 9 columns

### 12.5 dim_delivery_agent Transformation

**Steps**:
1. **Deduplication**: `drop_duplicates(subset="agent_id")`
2. **String normalisation**:
   - `name`: `.str.strip().str.title()`
3. **Date parsing**: `pd.to_datetime("joined_date")`
4. **Feature engineering — experience_days**:
   - Same `REFERENCE_DATE = pd.Timestamp("2024-12-31")`
   - `experience_days = REFERENCE_DATE - joined_date` (in days)
5. **Feature engineering — performance_tier**:
   - Uses `pd.cut()` with bins `[0, 3.5, 4.2, 4.7, 5.0]` and labels `["Below Average", "Average", "Good", "Top Performer"]`
6. **Column selection**: Returns exactly 8 columns

### 12.6 dim_date Construction

Unlike other dimensions, `dim_date` is not derived from a CSV. It is **programmatically generated**:

1. **Date range**: `pd.date_range(start="2023-01-01", end="2024-12-31", freq="D")` — generates 731 consecutive dates
2. **Date components**: Extracts day, month, month_name, quarter, year, week, day_of_week, day_name using pandas datetime accessors
3. **Weekend flag**: `day_of_week.isin([5, 6])` — Saturday (5) or Sunday (6)
4. **Holiday flag**: Checks against a hardcoded set of 8 Indian public holiday dates (4 per year)
5. **Peak season flag**: `month.isin([10, 11, 12, 1])` — October through January

### 12.7 fact_orders Transformation

This is the most complex transform, involving a merge of two source tables and multiple derived features:

**Steps**:
1. **Deduplication**: Both `orders` and `payments` are deduplicated on `order_id`
2. **Merge**: `orders.merge(payments[...], on="order_id", how="left")` — joins payment information to orders
   - Selected payment columns: `method`, `gross_total`, `discount_amount`, `delivery_fee`, `net_total`
3. **Timestamp parsing**: `pd.to_datetime("order_timestamp")`
4. **Date extraction**: `order_date` (as string) and `order_hour` (0–23)
5. **date_id attachment**: Creates a mapping from `full_date` (string) → `date_id` (integer) from `dim_date`, then maps each order's `order_date` to its surrogate key
6. **Null filling**: Money columns (`gross_total`, `discount_amount`, `delivery_fee`, `net_total`) are filled with 0.0 for cancelled orders that may have null payment data
7. **Derived KPIs**:
   - `is_delivered`: `(status == "Delivered").astype(int)` — 1 if delivered, 0 otherwise
   - `is_cancelled`: `(status == "Cancelled").astype(int)` — 1 if cancelled, 0 otherwise
8. **Time-of-day band**:
   - Uses `pd.cut()` with bins `[0, 6, 11, 14, 17, 20, 24]` and labels `["Night", "Morning", "Lunch", "Afternoon", "Dinner", "Late Night"]`
   - `right=False` means bins are left-inclusive: [0, 6), [6, 11), [11, 14), [14, 17), [17, 20), [20, 24)
9. **Column selection**: Returns exactly 18 columns

### 12.8 fact_order_items Transformation

**Steps**:
1. **Deduplication**: `drop_duplicates(subset="order_item_id")`
2. **Denormalisation**: Merges with `fact_orders[["order_id", "date_id", "customer_id"]]` to attach `date_id` and `customer_id` from the parent order
3. **Rename**: `line_total` → `revenue` for semantic clarity in the warehouse
4. **Column selection**: Returns exactly 8 columns

---

## 13. ETL Pipeline — Load

### 13.1 Bulk Load Strategy

The `load()` function uses SQLAlchemy's `to_sql()` method:

```python
df.to_sql(
    table_name,
    con=engine,
    if_exists="replace",     # DROP and CREATE on every run
    index=False,
    chunksize=5_000,         # Batch inserts of 5K rows
    method="multi",          # Multi-row INSERT statements
)
```

**Key decisions**:
- `if_exists="replace"`: Every run drops the existing table and recreates it. This is the simplest strategy — no need to track watermarks or handle upserts. The downside is that it doesn't scale to millions of rows and loses any concurrent access during the load window.
- `chunksize=5_000`: Inserts are batched in groups of 5,000 rows. This balances memory usage (loading all 200K rows at once would consume significant RAM) with insert efficiency (smaller chunks would result in more round-trips to the database).
- `method="multi"`: Uses multi-row INSERT statements (`INSERT INTO table VALUES (...), (...), (...)`) instead of single-row inserts. This is significantly faster — approximately 10–50x faster than single-row inserts.

### 13.2 Load Order

Tables are loaded in dependency order:
1. `dim_date` (independent)
2. `dim_customer` (independent)
3. `dim_restaurant` (independent)
4. `dim_menu_item` (depends on dim_restaurant for FK)
5. `dim_delivery_agent` (independent)
6. `fact_orders` (depends on all 4 dimensions + dim_date)
7. `fact_order_items` (depends on fact_orders for the merge)

### 13.3 Post-Load Indexing

After all tables are loaded, `apply_indexes()` creates performance indexes via raw SQL:

```sql
CREATE INDEX IF NOT EXISTS idx_fact_orders_customer   ON fact_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_restaurant ON fact_orders(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_date       ON fact_orders(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_agent      ON fact_orders(agent_id);
CREATE INDEX IF NOT EXISTS idx_fact_oi_item           ON fact_order_items(item_id);
CREATE INDEX IF NOT EXISTS idx_fact_oi_order          ON fact_order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_dim_date_ym            ON dim_date(year, month);
```

These indexes are applied **after** the bulk load (not during) because:
1. Building indexes on an empty table is instant
2. Building indexes on a fully loaded table is more efficient than maintaining them during inserts
3. PostgreSQL's `CREATE INDEX` is optimised for bulk index creation

**Note**: The DDL file (`01_schema_ddl.sql`) also creates indexes during initial schema creation. The ETL pipeline's `apply_indexes()` uses `CREATE INDEX IF NOT EXISTS` to avoid conflicts, making it safe to run independently.

---

## 14. Apache Airflow Orchestration

### 14.1 DAG Configuration

```python
dag = DAG(
    dag_id          = "foodflow_daily_etl",
    schedule_interval = "30 21 * * *",   # 21:30 UTC = 03:00 IST next day
    start_date      = datetime(2024, 1, 1),
    catchup         = False,
    default_args    = default_args,
    tags            = ["foodflow", "etl", "data-warehouse"],
)
```

**Schedule explanation**: `30 21 * * *` means "at minute 30 of hour 21 (UTC)". Since UTC is 5.5 hours behind IST, 21:30 UTC = 03:00 IST (next day). This timing is chosen because:
- 3 AM IST is typically the lowest-traffic period for a food delivery platform
- The previous day's data (up to midnight) is fully captured
- Results are ready for morning business review

**catchup=False**: Airflow will not run historical DAG runs for missed schedules. If the pipeline is down for a week, it will only run the current day's run, not backfill all 7 missed days.

### 14.2 Default Arguments

```python
default_args = {
    "owner":             "data-engineering-team",
    "depends_on_past":   False,
    "email":             ["dataops@foodflow.in"],
    "email_on_failure":  True,
    "email_on_retry":    False,
    "retries":           2,
    "retry_delay":       timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=90),
}
```

- **depends_on_past=False**: Each run is independent — today's run doesn't depend on yesterday's success
- **email_on_failure=True**: Sends email to `dataops@foodflow.in` if any task fails
- **retries=2**: If a task fails, it's retried up to 2 times with a 5-minute delay between retries
- **execution_timeout=90 minutes**: The entire DAG run must complete within 90 minutes, or it's killed

### 14.3 Task Details

#### Task 1: data_quality_check (PythonOperator)

This is a gatekeeper task that runs before any data processing. It verifies:

| File | Minimum Rows | Rationale |
|---|---|---|
| customers.csv | 100 | At least 100 customers must exist |
| restaurants.csv | 10 | At least 10 restaurants must exist |
| menu_items.csv | 50 | At least 50 menu items must exist |
| delivery_agents.csv | 10 | At least 10 agents must exist |
| orders.csv | 500 | At least 500 orders must exist |
| order_items.csv | 1,000 | At least 1,000 line items must exist |
| payments.csv | 500 | At least 500 payments must exist |

If any file is missing or has too few rows, the task raises a `ValueError` and the pipeline stops. This prevents corrupted or incomplete data from poisoning the warehouse.

#### Task 2: run_etl_pipeline (BashOperator)

Executes the standalone ETL script:
```bash
cd /opt/airflow/foodflow && python scripts/etl_pipeline.py
```

This runs inside the Airflow container, using the mounted volumes for access to scripts and data.

#### Task 3: refresh_aggregates (PostgresOperator)

Executes a TRUNCATE + INSERT directly against the warehouse:
```sql
TRUNCATE TABLE agg_monthly_revenue;
INSERT INTO agg_monthly_revenue
SELECT ... FROM fact_orders ... GROUP BY ...
```

This repopulates the pre-aggregated summary table for BI performance.

#### Task 4: ml_order_volume_forecast (BashOperator)

Executes the ML forecasting script:
```bash
cd /opt/airflow/foodflow && python scripts/ml_forecast.py
```

#### Task 5: notify_success (PythonOperator)

Sends an HTML email notification upon successful pipeline completion:
- **To**: `analytics@foodflow.in`
- **Subject**: `[FoodFlow] ETL Success — {execution_date}`
- **Content**: Execution date, DAG name, completion status

### 14.4 Airflow Connection

The DAG uses the Airflow Connection `foodflow_postgres`, defined in `docker-compose.yml`:
```
AIRFLOW_CONN_FOODFLOW_POSTGRES = postgresql+psycopg2://dw_user:secret@postgres:5432/foodflow_dw
```

Inside the Airflow container, the PostgreSQL hostname is `postgres` (the Docker service name), not `localhost`. The port is `5432` (container-internal port).

---

## 15. Analytical SQL Queries

### 15.1 Overview

The file `02_analytical_queries.sql` contains 11 production-grade analytical queries covering all major business dimensions. Each query is designed to answer a specific business question and uses advanced SQL features appropriate for the task.

### 15.2 Query Catalogue

#### Q1: Monthly Revenue Trend
**Technique**: CTEs, LAG window function, month-over-month growth percentage  
**Business question**: Is our revenue growing or declining? At what rate?  
**Key insight**: The `LAG()` window function compares each month's revenue to the previous month, computing the percentage change. This is the standard approach for time-series growth analysis.

#### Q2: Top 10 Restaurants
**Technique**: GROUP BY, aggregates, computed delivery success rate  
**Business question**: Which restaurants generate the most revenue? How reliable are they?  
**Key insight**: Combines revenue metrics with operational metrics (delivery success rate, average delivery time) to provide a holistic view of restaurant performance.

#### Q3: Customer Lifetime Value
**Technique**: LEFT JOIN, NTILE(4) quartile ranking, CLV tiers  
**Business question**: Who are our most valuable customers? How should we segment them?  
**Key insight**: Uses NTILE to divide customers into 4 quartiles by lifetime value, then labels them as Champion, Loyal, At-Risk, or Dormant. This enables targeted marketing strategies.

#### Q4: Top 10 Menu Items
**Technique**: Multi-table JOIN (fact_order_items → dim_menu_item → dim_restaurant), revenue by item  
**Business question**: Which specific menu items generate the most revenue?  
**Key insight**: Goes beyond restaurant-level analysis to the item level, revealing which dishes drive revenue.

#### Q5: Cancellation Analysis
**Technique**: GROUP BY with HAVING filter, cancellation rate percentage  
**Business question**: Where are cancellations concentrated? Which cities/cuisines have the highest cancellation rates?  
**Key insight**: The HAVING clause filters to groups with ≥100 orders, ensuring statistical significance. Only cities/cuisines with meaningful sample sizes are reported.

#### Q6: Hourly Demand Pattern
**Technique**: day_name × order_hour cross-tabulation  
**Business question**: When do customers order most? What are the peak hours and days?  
**Key insight**: Creates a two-dimensional view (day of week × hour) that reveals ordering patterns — useful for staffing, delivery agent scheduling, and restaurant prep planning.

#### Q7: Agent Performance
**Technique**: Simple GROUP BY with aggregates  
**Business question**: Which delivery agents are handling the most deliveries? How fast are they?  
**Key insight**: Combines volume (deliveries), speed (avg_time), and value (total_value) metrics for a complete performance view.

#### Q8: RFM Segmentation
**Technique**: NTILE(5) scoring on Recency, Frequency, Monetary dimensions, 9-segment classification  
**Business question**: How can we segment our customer base using the standard RFM framework?  
**Key insight**: Uses NTILE(5) to score each customer on all three dimensions (1–5 scale), then combines scores and applies a decision tree to assign 9 actionable segments: Champions, Loyal Customers, New Customers, Potential Loyalists, Recent Customers, At-Risk Customers, About to Sleep, Lost, and Can't Lose Them.

#### Q9: Year-over-Year Revenue
**Technique**: Simple annual aggregation  
**Business question**: What is our total revenue by year?  
**Key insight**: The simplest query — provides the high-level annual trend.

#### Q10: Platform Distribution
**Technique**: GROUP BY platform  
**Business question**: Which platforms (App-iOS, App-Android, Web) drive the most orders and revenue?  
**Key insight**: Helps understand platform preference and allocate development resources.

#### Q11: Aggregate Table Population
**Technique**: INSERT with ON CONFLICT DO UPDATE upsert  
**Business question**: How do we populate the pre-aggregated summary table?  
**Key insight**: Uses `ON CONFLICT (year, month, city, cuisine_type) DO UPDATE SET net_revenue = EXCLUDED.net_revenue` to handle re-runs safely without creating duplicate rows.

### 15.3 SQL Features Used

| Feature | Queries | Purpose |
|---|---|---|
| CTEs (WITH clauses) | Q1, Q3, Q8 | Organise complex queries into readable steps |
| Window functions (LAG, NTILE) | Q1, Q3, Q8 | Compare across rows, rank/score |
| Aggregate functions (SUM, COUNT, AVG) | All | Compute metrics |
| FILTER clause | Q1, Q2, Q5, Q11 | Conditional aggregation |
| LEFT JOIN | Q3 | Include customers with zero orders |
| INNER JOIN | Q2, Q4, Q5, Q6, Q7, Q8, Q9, Q10, Q11 | Match records across tables |
| HAVING | Q5 | Filter aggregated results |
| ORDER BY ... LIMIT | Q2, Q4, Q3 | Top-N results |
| ON CONFLICT ... DO UPDATE | Q11 | Upsert for idempotent inserts |

---

## 16. Machine Learning Forecasting

### 16.1 Model Selection

**Model**: Facebook Prophet (v1.1.5)

**Why Prophet?**
- Designed for business time-series with strong seasonal patterns
- Handles missing data gracefully (unlike ARIMA)
- Automatically detects and models changepoints
- Supports custom regressors (weekend flag)
- Produces interpretable forecasts with confidence intervals
- Requires minimal hyperparameter tuning

**Alternative considered**: SARIMA (Seasonal ARIMA) — rejected because it requires manual parameter selection (p, d, q)(P, D, Q, s) and handles missing data poorly.

### 16.2 Training Data

```sql
SELECT
    d.full_date AS ds,
    COUNT(fo.order_id) AS y
FROM fact_orders fo
JOIN dim_date d ON fo.date_id = d.date_id
WHERE fo.status = 'Delivered'
GROUP BY d.full_date
ORDER BY d.full_date;
```

- **Target variable**: Daily count of delivered orders (`y`)
- **Date range**: 2023-01-01 to 2024-12-31 (~731 daily observations)
- **Filter**: Only "Delivered" orders — cancelled and refunded orders don't represent genuine demand

### 16.3 Model Configuration

```python
m = Prophet(
    changepoint_prior_scale=0.15,    # Moderate flexibility in trend changes
    seasonality_mode="multiplicative", # Seasonal patterns scale with trend level
    weekly_seasonality=True,         # Model day-of-week patterns
    yearly_seasonality=True,         # Model annual patterns
    daily_seasonality=False,         # Not applicable (daily granularity)
)
```

**Hyperparameter rationale**:
- `changepoint_prior_scale=0.15`: Default is 0.05. A higher value (0.15) allows the model to be more flexible in adapting to trend changes — appropriate for a food delivery business that may experience rapid growth or seasonal shifts.
- `seasonality_mode="multiplicative"`: Means that the seasonal pattern scales proportionally with the overall trend level. If order volume doubles, the lunch rush also doubles — this is more realistic than additive seasonality for this domain.

### 16.4 Custom Regressor

```python
df["is_weekend"] = df["ds"].dt.dayofweek.isin([5, 6]).astype(int)
m.add_regressor("is_weekend")
```

The weekend flag is added as an external regressor because weekend ordering behaviour is typically different from weekdays (more leisure orders, different time patterns). This is a known, deterministic feature that the model can use to improve accuracy.

### 16.5 Forecast Generation

```python
future = m.make_future_dataframe(periods=30)
future["is_weekend"] = future["ds"].dt.dayofweek.isin([5, 6]).astype(int)
forecast = m.predict(future)
```

The model generates predictions for 30 days beyond the last training date. The `is_weekend` feature is computed for each future date using the same logic as the training data.

### 16.6 Output Processing

**Future-only filtering**:
```python
last_date = df["ds"].max()
output = forecast[forecast["ds"] > last_date][["ds", "yhat", "yhat_lower", "yhat_upper"]]
```

This is a **critical fix** — the original code used `datetime.now()` which would include historical fitted values. Using `df["ds"].max()` ensures only genuinely future dates are included.

**Value cleaning**:
```python
output["predicted_orders"] = output["predicted_orders"].clip(lower=0).round().astype(int)
```

Negative predictions (possible with Prophet's confidence intervals) are clipped to 0 — you can't have negative orders.

**Destination**:
- Written to `ml_order_forecast` table in the warehouse (full REPLACE)
- Plot saved to `outputs/plots/forecast_plot.png` (150 DPI)
- 7-day preview printed to console

---

## 17. Model Evaluation Metrics

### 17.1 Metrics Computed

Three standard regression evaluation metrics are computed on the **in-sample fit** (training data):

#### MAPE (Mean Absolute Percentage Error)
```python
mape = np.mean(np.abs(error[mask] / actual[mask])) * 100
```
- Measures error as a percentage of actual values
- Useful for business stakeholders who think in percentages
- Masked to exclude zero-actual days (avoiding division by zero)
- Interpretation: "On average, the model's predictions are off by X%"

#### MAE (Mean Absolute Error)
```python
mae = np.mean(np.abs(error))
```
- Measures average absolute deviation in the original units (orders)
- Less sensitive to outliers than RMSE
- Interpretation: "On average, the model is off by X orders per day"

#### RMSE (Root Mean Squared Error)
```python
rmse = np.sqrt(np.mean(error ** 2))
```
- Penalises larger errors more heavily (due to squaring)
- Useful when large errors are particularly costly
- Interpretation: "The typical prediction error is X orders"

### 17.2 Storage

Metrics are written to `ml_model_metrics` table in **APPEND** mode, meaning each run adds a new row. This enables:
- Tracking model quality over time
- Detecting model degradation (increasing MAPE over runs)
- Comparing different model configurations in future iterations

### 17.3 Display on Dashboard

The Streamlit dashboard displays these metrics at the top of the ML Forecast page:
```
MAPE: 12.3%    MAE: 15.2    RMSE: 22.1
```

This provides immediate visibility into model quality for stakeholders.

---

## 18. Interactive Dashboard (Streamlit)

### 18.1 Technology Stack

- **Framework**: Streamlit (auto-reloads on code changes)
- **Charts**: Plotly (interactive, zoomable, hoverable)
- **Data source**: Direct SQL queries against PostgreSQL DW
- **Caching**: `@st.cache_data(ttl=300)` — results cached for 5 minutes to reduce database load

### 18.2 Page Structure

The dashboard has a sidebar navigation with 10 pages:

#### Page 1: 📊 Overview
- **KPI strip**: Total orders, net revenue, avg order value, avg delivery time, delivery rate — displayed as metric cards at the top of every page
- **Order status distribution**: Pie chart (delivered/cancelled/refunded)
- **Platform split**: Bar chart showing orders by platform
- **Monthly revenue trend**: Dual-axis chart — revenue (line) + orders (bar) over time
- **Data model summary**: Table showing row counts per table

#### Page 2: 💰 Revenue
- **Monthly revenue line chart**: Revenue over time with markers
- **MoM growth bar chart**: Color-coded green/red for positive/negative growth
- **Full data table**: All monthly revenue data

#### Page 3: 🏆 Restaurants
- **Top 10 restaurants bar chart**: Revenue with city coloring
- **Hover data**: Rating, delivery success rate, total orders
- **Full data table**

#### Page 4: 👥 Customers
- **Customer segments pie chart**: Distribution of Premium-Loyal, Premium-New, etc.
- **Top 20 CLV bar chart**: Lifetime value with segment coloring
- **Full data table**

#### Page 5: 🍔 Menu Items
- **Top 10 items bar chart**: Revenue with category coloring
- **Hover data**: Units sold, order count, average price
- **Full data table**

#### Page 6: ❌ Cancellations
- **Cancellation rate bar chart**: Top 15 cities by cancellation rate
- **Scatter plot**: Volume vs cancellation rate, sized by cancelled count
- **Full data table**

#### Page 7: ⏰ Demand Patterns
- **Day × Hour heatmap**: Orders by day of week and hour of day
- **Color scale**: YlOrRd (yellow → orange → red) for intuitive demand visualization
- **Full data table**

#### Page 8: 🚴 Delivery Agents
- **Leaderboard bar chart**: Top 15 agents by deliveries
- **Box plots**: Delivery volume distribution by performance tier
- **Full data table**

#### Page 9: 📈 RFM Segmentation
- **Segment bar chart**: Customer count per RFM segment
- **Scatter plot**: Frequency vs monetary value, sized by customer count
- **Full segment summary table**

#### Page 10: 🔮 ML Forecast
- **Model metrics**: MAPE, MAE, RMSE displayed as metric cards
- **Forecast chart**: Predicted orders with confidence interval shading
- **Forecast data table**
- **Static forecast plot**: Prophet-generated matplotlib plot (if available)

### 18.3 Design Patterns

**KPI Strip**: A reusable function `show_kpi_strip()` runs a single query against `fact_orders` and displays 5 metric cards at the top of every page. This provides consistent context regardless of which page the user is viewing.

**Query Caching**: All database queries use `@st.cache_data(ttl=300)` — results are cached for 5 minutes. This means:
- Multiple visits to the same page within 5 minutes return cached data (no database query)
- After 5 minutes, the cache expires and the query is re-executed
- This balances data freshness with database load

**Plotly Charts**: All charts use Plotly (not matplotlib) for interactivity:
- Hover tooltips with detailed information
- Zoom and pan
- Toggle traces on/off
- Export as PNG

---

## 19. Metabase BI Integration

### 19.1 What Metabase Adds

While the Streamlit dashboard provides pre-built visualisations, Metabase offers:
- **Ad-hoc SQL querying**: Analysts can write and execute custom SQL queries without knowing Python
- **Chart builder**: Visual charts from query results without coding
- **Dashboard builder**: Drag-and-drop assembly of charts into executive dashboards
- **Question interface**: "Ask a question" mode for non-technical users to explore data
- **Scheduling**: Email reports and Slack alerts based on query results
- **User management**: Role-based access control (admin, editor, viewer)

### 19.2 Setup Process

1. Start Metabase: `docker compose up -d metabase`
2. Open `http://localhost:3000` and complete the setup wizard
3. Add the PostgreSQL data warehouse as a data source:
   - Host: `foodflow_postgres`
   - Port: `5432`
   - Database: `foodflow_dw`
   - User: `dw_user`
   - Password: `secret`
4. Metabase automatically introspects the schema and makes all tables available

### 19.3 Workflow

The recommended workflow for using Metabase with FoodFlow:
1. Navigate to SQL Editor
2. Paste any query from `02_analytical_queries.sql`
3. Execute and view results
4. Click "Visualize" to convert results to a chart
5. Click "Save" and "Add to Dashboard" to include in a dashboard
6. Repeat for all 11 queries to build a comprehensive analytics dashboard

---

## 20. Testing Strategy

### 20.1 Test Framework

- **Framework**: pytest
- **Test file**: `tests/test_etl.py`
- **Total tests**: 20
- **Coverage**: All dimension transform functions + data integrity checks

### 20.2 Test Organisation

Tests are organised into 6 test classes:

#### TestTransformCustomers (7 tests)
| Test | What it verifies |
|---|---|
| `test_deduplication` | Duplicate customer_id rows are removed |
| `test_name_normalisation` | Names are converted to Title Case, stripped of whitespace |
| `test_email_normalisation` | Emails are lowercase, stripped of whitespace |
| `test_city_stripped` | City names have no leading/trailing whitespace |
| `test_tenure_days` | Computed tenure is correct and positive |
| `test_customer_segments exist` | All segments are from the valid set |
| `test_required_columns` | Output has exactly 11 expected columns |

#### TestTransformRestaurants (2 tests)
| Test | What it verifies |
|---|---|
| `test_rating_bands` | Rating 2.3 → "Poor", Rating 4.5 → "Excellent" |
| `test_name_normalisation` | Names are Title Case, stripped |

#### TestTransformMenuItems (1 test)
| Test | What it verifies |
|---|---|
| `test_price_bands` | ₹80 → "Budget", ₹250 → "Mid-Range", ₹350 → "Mid-Range" |

#### TestTransformAgents (2 tests)
| Test | What it verifies |
|---|---|
| `test_performance_tiers` | Rating 3.2 → "Below Average", Rating 4.8 → "Top Performer" |
| `test_experience_days` | Computed experience is correct and positive |

#### TestBuildDimDate (5 tests)
| Test | What it verifies |
|---|---|
| `test_date_range` | Correct number of rows generated |
| `test_date_id_format` | YYYYMMDD format is correct |
| `test_weekend_flag` | Saturdays and Sundays are flagged |
| `test_holiday_flag` | Indian public holidays are flagged |
| `test_required_columns` | Output has all 13 required columns |

#### TestDataIntegrity (3 tests)
| Test | What it verifies |
|---|---|
| `test_no_null_keys_after_transform` | Primary keys are never null |
| `test_boolean_columns` | Boolean columns have bool dtype |
| `test_numeric_columns_are_numeric` | Numeric columns have numeric dtype |

### 20.3 Test Fixtures

Each test class uses pytest fixtures to create small, focused sample DataFrames:

```python
@pytest.fixture
def sample_customers():
    return pd.DataFrame({
        "customer_id": ["CUST00001", "CUST00002", "CUST00003", "CUST00001"],
        ...
    })
```

The fixtures include intentional duplicates and edge cases (leading/trailing whitespace, mixed case) to verify that the transform functions handle them correctly.

### 20.4 Running Tests

```bash
pytest tests/ -v          # Verbose output
pytest tests/ -v --tb=short  # Short traceback format
```

Expected result: **20 passed** in approximately 1–2 seconds (tests run entirely in memory — no database required).

---

## 21. Docker Compose Infrastructure

### 21.1 Volume Management

| Volume | Purpose | Persistence |
|---|---|---|
| `postgres_data` | DW database files | Survives `docker compose down` |
| `airflow_db_data` | Airflow metadata | Survives `docker compose down` |
| `metabase_data` | Metabase application data | Survives `docker compose down` |
| `metabase_db_data` | Metabase database files | Survives `docker compose down` |
| `./01_schema_ddl.sql` (bind mount) | Schema initialization script | Read-only mount |
| `./airflow/dags` (bind mount) | DAG files | Read-write |
| `./scripts` (bind mount) | Pipeline scripts | Read-only for Airflow |
| `./data` (bind mount) | Raw CSVs | Read-only for Airflow |
| `./outputs` (bind mount) | Generated outputs | Read-write |

### 21.2 Health Checks

Three services have health checks:

| Service | Command | Interval | Retries |
|---|---|---|---|
| foodflow_postgres | `pg_isready -U dw_user -d foodflow_dw` | 10s | 5 |
| foodflow_airflow_db | `pg_isready -U airflow` | 10s | 5 |
| foodflow_metabase_db | `pg_isready -U metabase` | 10s | 5 |

The Airflow service depends on both PostgreSQL DW and Airflow DB being healthy before starting. Metabase depends on both PostgreSQL DW and Metabase DB being healthy.

### 21.3 Startup Sequence

```
1. foodflow_postgres starts → health check passes
2. foodflow_airflow_db starts → health check passes
3. foodflow_metabase_db starts → health check passes
4. foodflow_airflow starts (after postgres + airflow_db healthy)
   ├── pip install (≈30-60s)
   ├── airflow db init
   ├── airflow users create
   ├── airflow scheduler (background)
   └── airflow webserver (foreground)
5. foodflow_metabase starts (after postgres + metabase_db healthy)
```

### 21.4 Docker Compose Commands

```bash
docker compose up -d                    # Start all services
docker compose up -d postgres           # Start only PostgreSQL
docker compose up -d metabase           # Start only Metabase
docker compose logs -f                  # Tail all logs
docker compose logs -f airflow          # Tail Airflow logs only
docker compose down                     # Stop all (data persists)
docker compose down -v                  # Stop all + delete volumes (nuclear)
docker compose ps                       # Show running containers
docker compose exec postgres psql -U dw_user -d foodflow_dw  # Direct DB access
```

---

## 22. Project Structure and File Map

```
foodflow/
│
├── 01_schema_ddl.sql                    # PostgreSQL DDL — star schema creation
│   │
│   ├── DROP TABLE statements            # Reverse dependency order
│   ├── CREATE TABLE dim_date            # Calendar dimension (731 rows)
│   ├── CREATE TABLE dim_customer        # Customer dimension (5,000 rows)
│   ├── CREATE TABLE dim_restaurant      # Restaurant dimension (200 rows)
│   ├── CREATE TABLE dim_menu_item       # Menu item dimension (1,500 rows)
│   ├── CREATE TABLE dim_delivery_agent  # Delivery agent dimension (300 rows)
│   ├── CREATE TABLE fact_orders         # Order-level fact (80,000 rows)
│   ├── CREATE TABLE fact_order_items    # Line-item fact (~200K rows)
│   ├── CREATE INDEX statements          # 13 performance indexes
│   └── CREATE TABLE agg_monthly_revenue # Pre-aggregated summary
│
├── 02_analytical_queries.sql            # 11 analytical SQL queries
│   │
│   ├── Q1: Monthly Revenue Trend        # CTE + LAG + MoM growth
│   ├── Q2: Top 10 Restaurants           # GROUP BY + aggregates
│   ├── Q3: Customer Lifetime Value      # LEFT JOIN + NTILE + CLV tiers
│   ├── Q4: Top 10 Menu Items            # Multi-table JOIN
│   ├── Q5: Cancellation Analysis        # GROUP BY + HAVING
│   ├── Q6: Hourly Demand Pattern        # Cross-tabulation
│   ├── Q7: Agent Performance            # Simple aggregation
│   ├── Q8: RFM Segmentation             # NTILE(5) + 9-segment classification
│   ├── Q9: Year-over-Year Revenue       # Annual aggregation
│   ├── Q10: Platform Distribution       # Platform breakdown
│   └── Q11: Aggregate Population        # UPSERT (ON CONFLICT)
│
├── docker-compose.yml                   # Infrastructure orchestration (5 services)
│   ├── postgres:5433                    # Data warehouse
│   ├── airflow-db:5432                  # Airflow metadata
│   ├── airflow:8080                     # Pipeline orchestration
│   ├── metabase-db:5432                 # Metabase metadata
│   └── metabase:3000                    # BI dashboard
│
├── foodflow_daily_etl.py                # Airflow DAG definition (root level)
│   ├── data_quality_check               # Task 1: PythonOperator
│   ├── run_etl_pipeline                 # Task 2: BashOperator
│   ├── refresh_aggregates               # Task 3: PostgresOperator
│   ├── ml_order_volume_forecast         # Task 4: BashOperator
│   └── notify_success                   # Task 5: PythonOperator
│
├── requirements.txt                     # Python dependencies (12 pinned packages)
├── .env.example                         # Environment variable template
├── run_all.sh                           # End-to-end run script
├── README.md                            # Project documentation
│
├── airflow/
│   └── dags/
│       └── foodflow_daily_etl.py        # DAG (copy for Airflow discovery)
│
├── data/
│   └── raw/
│       ├── customers.csv                # 5,000 rows, 10 columns
│       ├── restaurants.csv              # 200 rows, 9 columns
│       ├── menu_items.csv               # 1,500 rows, 8 columns
│       ├── delivery_agents.csv          # 300 rows, 7 columns
│       ├── orders.csv                   # 80,000 rows, 10 columns
│       ├── order_items.csv              # ~200K rows, 6 columns
│       └── payments.csv                 # 80,000 rows, 9 columns
│
├── outputs/
│   └── plots/
│       └── forecast_plot.png            # Generated by ml_forecast.py
│
├── scripts/
│   ├── generate_data.py                 # Synthetic data generator
│   │   ├── Config section               # N_CUSTOMERS, N_RESTAURANTS, etc.
│   │   ├── Reference data               # CITIES, CUISINES, CATEGORIES
│   │   ├── Step 1: Customers            # Faker-generated customer records
│   │   ├── Step 2: Restaurants          # Faker-generated restaurant records
│   │   ├── Step 3: Menu Items           # Faker-generated menu items
│   │   ├── Step 4: Delivery Agents      # Faker-generated agent records
│   │   ├── Step 5: Orders               # Time-biased order generation
│   │   ├── Step 6: Order Items          # Line item generation
│   │   └── Step 7: Payments             # Payment record derivation
│   │
│   ├── etl_pipeline.py                  # Core ETL pipeline
│   │   ├── get_engine()                 # PostgreSQL connection
│   │   ├── extract()                    # Read 7 CSVs
│   │   ├── _log_quality()               # Data quality logging
│   │   ├── transform_customers()        # dim_customer transform
│   │   ├── transform_restaurants()      # dim_restaurant transform
│   │   ├── transform_menu_items()       # dim_menu_item transform
│   │   ├── transform_agents()           # dim_delivery_agent transform
│   │   ├── build_dim_date()             # Programmatic date dimension
│   │   ├── transform_orders()           # fact_orders transform
│   │   ├── transform_order_items()      # fact_order_items transform
│   │   ├── load()                       # Bulk insert via to_sql
│   │   ├── apply_indexes()              # Post-load index creation
│   │   └── run_pipeline()               # Main orchestrator
│   │
│   ├── ml_forecast.py                   # ML forecasting
│   │   ├── get_engine()                 # DB connection
│   │   ├── load_training_data()         # Query daily delivered counts
│   │   ├── train_and_forecast()         # Prophet model training + prediction
│   │   ├── save_forecast_plot()         # matplotlib chart generation
│   │   ├── evaluate_model()             # MAPE, MAE, RMSE computation
│   │   ├── write_metrics_to_dw()        # Store evaluation metrics
│   │   ├── write_forecast_to_dw()       # Store future predictions
│   │   └── run()                        # Main pipeline
│   │
│   └── dashboard_app.py                 # Streamlit interactive dashboard
│       ├── get_engine()                 # DB connection (cached)
│       ├── query()                      # SQL execution (cached 5min)
│       ├── show_kpi_strip()             # Global KPI metric cards
│       ├── page_overview()              # KPI strip + status pie + revenue trend
│       ├── page_revenue()               # Revenue line + MoM growth
│       ├── page_restaurants()           # Top restaurants bar chart
│       ├── page_customers()             # Segment pie + CLV bar
│       ├── page_menu_items()            # Top items bar chart
│       ├── page_cancellations()         # Cancellation rate analysis
│       ├── page_demand()                # Day × Hour heatmap
│       ├── page_agents()                # Agent leaderboard + box plots
│       ├── page_rfm()                   # RFM segment analysis
│       ├── page_forecast()              # Forecast with confidence bands
│       └── Router                       # Navigation dispatcher
│
└── tests/
    ├── __init__.py                      # Package marker
    └── test_etl.py                      # Unit tests (20 tests)
        ├── TestTransformCustomers       # 7 tests
        ├── TestTransformRestaurants     # 2 tests
        ├── TestTransformMenuItems       # 1 test
        ├── TestTransformAgents          # 2 tests
        ├── TestBuildDimDate             # 5 tests
        └── TestDataIntegrity            # 3 tests
```

---

## 23. Configuration and Environment Variables

### 23.1 .env File

```bash
DB_HOST=localhost
DB_PORT=5433
DB_NAME=foodflow_dw
DB_USER=dw_user
DB_PASS=secret
```

### 23.2 Variable Documentation

| Variable | Default | Scope | Description |
|---|---|---|---|
| `DB_HOST` | `localhost` | Local scripts, Streamlit | PostgreSQL hostname when connecting from host |
| `DB_PORT` | `5433` | Local scripts, Streamlit | Host-side port mapped to container 5432 |
| `DB_NAME` | `foodflow_dw` | All | Data warehouse database name |
| `DB_USER` | `dw_user` | All | PostgreSQL username (matches POSTGRES_USER) |
| `DB_PASS` | `secret` | All | PostgreSQL password (matches POSTGRES_PASSWORD) |

### 23.3 Airflow-Specific Configuration

Inside the Airflow container, environment variables are set via `docker-compose.yml`:

| Variable | Value | Description |
|---|---|---|
| `DB_HOST` | `postgres` | Container-internal hostname |
| `DB_PORT` | `5432` | Container-internal port |
| `AIRFLOW_CONN_FOODFLOW_POSTGRES` | Full connection URI | Used by PostgresOperator tasks |

### 23.4 Airflow DAG Thresholds

The data quality check enforces minimum row counts:

| File | Min Rows | Failure Message |
|---|---|---|
| customers.csv | 100 | "LOW ROWS: customers.csv has X < 100" |
| restaurants.csv | 10 | "LOW ROWS: restaurants.csv has X < 10" |
| menu_items.csv | 50 | "LOW ROWS: menu_items.csv has X < 50" |
| delivery_agents.csv | 10 | "LOW ROWS: delivery_agents.csv has X < 10" |
| orders.csv | 500 | "LOW ROWS: orders.csv has X < 500" |
| order_items.csv | 1,000 | "LOW ROWS: order_items.csv has X < 1000" |
| payments.csv | 500 | "LOW ROWS: payments.csv has X < 500" |

---

## 24. Dependencies and Package Management

### 24.1 requirements.txt

```
pandas==2.2.3
numpy==1.26.4
sqlalchemy==2.0.27
psycopg2-binary==2.9.9
python-dotenv==1.0.1
Faker==23.3.0
prophet==1.1.5
matplotlib==3.8.3
scikit-learn==1.4.0
apache-airflow==2.8.4
apache-airflow-providers-postgres==5.10.2
tqdm==4.66.2
loguru==0.7.2
```

### 24.2 Dependency Usage Map

| Package | Used In | Purpose |
|---|---|---|
| `pandas==2.2.3` | etl_pipeline.py, generate_data.py, ml_forecast.py, dashboard_app.py, test_etl.py | Data manipulation, CSV reading, SQL execution |
| `numpy==1.26.4` | etl_pipeline.py, generate_data.py, ml_forecast.py | Numerical operations, random sampling, feature engineering |
| `sqlalchemy==2.0.27` | etl_pipeline.py, ml_forecast.py, dashboard_app.py, test_etl.py | Database connection, bulk inserts, SQL execution |
| `psycopg2-binary==2.9.9` | etl_pipeline.py, ml_forecast.py, dashboard_app.py | PostgreSQL driver for SQLAlchemy |
| `python-dotenv==1.0.1` | etl_pipeline.py, ml_forecast.py, dashboard_app.py | Environment variable loading from .env file |
| `Faker==23.3.0` | generate_data.py | Realistic synthetic data generation (en_IN locale) |
| `prophet==1.1.5` | ml_forecast.py | Time-series forecasting |
| `matplotlib==3.8.3` | ml_forecast.py | Forecast plot generation |
| `scikit-learn==1.4.0` | requirements.txt | **UNUSED** — declared but not imported |
| `apache-airflow==2.8.4` | foodflow_daily_etl.py | Pipeline orchestration |
| `apache-airflow-providers-postgres==5.10.2` | foodflow_daily_etl.py | PostgresOperator for Airflow |
| `tqdm==4.66.2` | requirements.txt | **UNUSED** — declared but not imported |
| `loguru==0.7.2` | requirements.txt | **UNUSED** — standard logging is used instead |

### 24.3 Additional Dependencies (Not in requirements.txt)

These are installed separately for the dashboard and testing:

| Package | Used In | Purpose |
|---|---|---|
| `streamlit` | dashboard_app.py | Interactive dashboard framework |
| `plotly` | dashboard_app.py | Interactive charting |
| `pytest` | test_etl.py | Unit testing framework |

---

## 25. Design Decisions and Rationale

### 25.1 Star Schema vs Snowflake Schema

**Decision**: Star schema (denormalised dimensions)

**Rationale**: Star schema minimises the number of JOINs required for analytical queries. In a snowflake schema, `dim_menu_item` would reference a separate `dim_restaurant` table, which would reference a separate `dim_city` table. For OLAP workloads where read performance and query simplicity matter more than storage efficiency, star schema is the standard choice.

### 25.2 SCD Type 1 vs Type 2

**Decision**: Type 1 (overwrite on change) for all dimensions

**Rationale**: For an academic/portfolio project, Type 1 is sufficient. The data doesn't actually change after generation — it's a static dataset. In a real production system, Type 2 (historical tracking with valid_from/valid_to) would be essential for at least `dim_customer` and `dim_restaurant` to maintain historical accuracy. With Type 1, if a customer changes cities, their historical orders would appear to be from the new city.

### 25.3 Full REPLACE ETL vs Incremental

**Decision**: Full REPLACE (DROP and recreate tables)

**Rationale**: For 80,000 orders, full replacement takes seconds and is the simplest approach — no watermark tracking, no upsert logic, no conflict resolution. The downside is that it doesn't scale to millions of rows and blocks concurrent access during the load window. For a production system with growing data, incremental ETL with UPSERT (INSERT ... ON CONFLICT DO UPDATE) would be necessary.

### 25.4 Integer Flags vs Boolean Flags

**Decision**: `is_delivered` and `is_cancelled` stored as SMALLINT (0/1)

**Rationale**: While PostgreSQL supports BOOLEAN, integer flags offer:
1. Compatibility with SQL dialects that don't have boolean types
2. Easy `SUM(is_delivered)` for counting delivered orders (vs `COUNT(*) FILTER (WHERE is_delivered = true)`)
3. Consistency with the 0/1 convention in data warehousing
4. Slightly faster aggregation in some PostgreSQL versions

### 25.5 Degenerate Dimensions in Fact Table

**Decision**: `status`, `platform`, `method` kept in `fact_orders` instead of separate dimension tables

**Rationale**: Creating separate dimension tables for attributes with 3-5 possible values adds no analytical benefit. Each dimension table would have:
- A surrogate key (wasting storage)
- A single descriptive column
- No additional attributes

Degenerate dimensions are the standard approach for low-cardinality attributes that are intrinsic to the fact event.

### 25.6 Surrogate Key on dim_date

**Decision**: `date_id` as INTEGER (YYYYMMDD) instead of using `full_date` (DATE) as the key

**Rationale**:
1. Integer range scans are faster than DATE comparisons in PostgreSQL
2. The YYYYMMDD format is human-readable in query results
3. Standard data warehousing practice
4. Simplifies date arithmetic in queries (e.g., `WHERE date_id BETWEEN 20240101 AND 20240131`)

### 25.7 Prophet for Forecasting

**Decision**: Facebook Prophet instead of ARIMA, SARIMA, or LSTM

**Rationale**:
- **vs ARIMA/SARIMA**: Prophet handles missing data, automatic changepoint detection, and custom regressors without manual parameter tuning
- **vs LSTM**: Prophet requires significantly less data, trains in seconds (not hours), and produces interpretable results
- **For this dataset**: Daily order counts with weekly and yearly seasonality are exactly what Prophet is designed for

### 25.8 Two Dashboard Options

**Decision**: Both Streamlit AND Metabase

**Rationale**:
- **Streamlit**: Demonstrates Python/Plotly skills, custom interactivity, and full programmatic control. Shows engineering capability.
- **Metabase**: Demonstrates BI tool proficiency, which is what real data teams use for self-service analytics. Shows practical capability.
- **Together**: They cover both the "I can build custom tools" and "I can use standard BI tools" narratives — both are important in interviews.

### 25.9 LocalExecutor vs CeleryExecutor

**Decision**: LocalExecutor for Airflow

**Rationale**: For a single-machine development environment with one DAG running daily, LocalExecutor is sufficient. CeleryExecutor would add complexity (Redis/RabbitMQ broker, multiple worker processes) with no benefit for this scale.

### 25.10 Faker en_IN Locale

**Decision**: Use `en_IN` (Indian) locale instead of generic `en_US`

**Rationale**: The project models an Indian food delivery company. Using `en_IN` generates:
- Realistic Indian names (Rajesh Kumar, Priya Sharma, Suresh Yadav)
- Indian cities (Mumbai, Delhi, Bengaluru)
- Indian phone number formats
This makes the data immediately recognisable and contextually appropriate.

---

## 26. Known Limitations

### 26.1 ETL Limitations

1. **Full REPLACE strategy**: Every ETL run drops and recreates tables. This doesn't scale to millions of rows and blocks concurrent access during the load window. An incremental UPSERT strategy would be needed for production.

2. **No transaction wrapping**: If the load fails midway (e.g., after loading 5 of 7 tables), partial data remains in the database. The next run would see inconsistent state. Using `engine.begin()` as a context manager would ensure atomic commits.

3. **SCD Type 1 only**: All dimension changes overwrite history. In production, `dim_customer` and `dim_restaurant` should use Type 2 (historical tracking) to maintain accurate historical reporting.

4. **Hardcoded reference date**: `REFERENCE_DATE = pd.Timestamp("2024-12-31")` in the ETL pipeline means `tenure_days` and `experience_days` will become increasingly stale as time passes. Using `pd.Timestamp.today()` or deriving from the latest order date would fix this.

### 26.2 ML Limitations

1. **In-sample evaluation only**: MAPE, MAE, and RMSE are computed on the training data (in-sample fit). This can overestimate model quality. A proper evaluation would use a holdout set (e.g., train on first 18 months, test on last 6 months).

2. **Single model**: Only Prophet is used. No baseline comparison (naive forecast, moving average, seasonal naive) is provided to establish whether Prophet actually adds value over simpler approaches.

3. **Limited features**: Only `is_weekend` is used as a regressor. Additional features like holidays, promotional events, or lag features could improve accuracy.

4. **No model versioning**: Each run replaces the `ml_order_forecast` table. There's no history of previous forecasts for comparison.

### 26.3 Data Limitations

1. **Synthetic data**: All data is randomly generated. While realistic, it doesn't capture real-world patterns, correlations, or anomalies.

2. **No data drift**: The data is static — there's no evolution over time (no growing customer base, no changing ordering patterns, no new restaurants opening).

3. **No missing or corrupted data**: The synthetic generator produces clean data. Real-world data would have missing values, encoding issues, and data quality problems.

4. **No real-time data**: All data is batch-generated. There's no streaming or real-time ingestion component.

### 26.4 Infrastructure Limitations

1. **Single-node**: All services run on a single machine. No horizontal scaling, no high availability, no failover.

2. **Hardcoded credentials**: `admin/admin` for Airflow, `secret` for database passwords. These are development defaults, not production-grade security.

3. **No monitoring**: No alerting on pipeline duration, data quality degradation, or model drift beyond the basic email-on-failure.

4. **Airflow pip install on startup**: The Airflow container installs Python packages on every start, adding 30-60 seconds to startup time. A custom Dockerfile would pre-bake these dependencies.

### 26.5 Unused Dependencies

- `scikit-learn` (1.4.0): Declared but never imported
- `tqdm` (4.66.2): Declared but never imported
- `loguru` (0.7.2): Declared but standard `logging` is used instead

These add unnecessary weight to the dependency tree and could confuse readers about what the project actually uses.

---

## 27. Future Enhancements

### 27.1 Data Engineering Enhancements

1. **Incremental ETL**: Implement UPSERT-based loading with a `last_modified` watermark table. This would allow adding only new orders instead of rebuilding the entire warehouse.

2. **SCD Type 2**: Add `valid_from`, `valid_to`, and `is_current` columns to `dim_customer` and `dim_restaurant` to track historical dimension changes.

3. **dbt (data build tool)**: Migrate analytical queries and aggregate table creation to dbt models. This provides version-controlled, testable, and documented SQL transformations.

4. **Data quality framework**: Integrate Great Expectations or pandera for automated data quality validation during the transform phase — not just file existence checks.

5. **Data partitioning**: Partition `fact_orders` by `date_id` (range partitioning in PostgreSQL) for faster time-based queries on large datasets.

### 27.2 Analytics Enhancements

1. **Cohort analysis**: Add queries that track customer behaviour over time — how does the order frequency of customers who joined in Q1 2023 compare to those who joined in Q3 2023?

2. **Basket analysis**: Which items are frequently ordered together? (Market basket analysis using association rules)

3. **Customer churn prediction**: Identify customers who haven't ordered in X days and predict their likelihood of returning.

4. **Restaurant recommendation**: Collaborative filtering or content-based recommendation engine using order history.

### 27.3 ML Enhancements

1. **Holdout evaluation**: Split data into train/test sets for honest model evaluation.

2. **Baseline models**: Add naive forecast (y = yesterday's value), seasonal naive (y = same day last week), and moving average for comparison.

3. **Additional regressors**: Incorporate holiday flags from `dim_date`, promotional periods, or external data (weather, economic indicators).

4. **Model selection**: Compare Prophet with SARIMA, LightGBM, or neural network approaches.

5. **Hyperparameter tuning**: Use cross-validation to optimise `changepoint_prior_scale`, seasonality parameters, and regressor strength.

### 27.4 Infrastructure Enhancements

1. **Custom Dockerfile for Airflow**: Pre-bake Python dependencies instead of `pip install` on startup.

2. **CI/CD pipeline**: GitHub Actions to run tests, lint code, and build Docker images on every push.

3. **Observability**: Add Grafana for infrastructure monitoring (CPU, memory, query performance) alongside Metabase for business analytics.

4. **Multi-environment**: Separate dev/staging/prod configurations with different data sizes and resource allocations.

### 27.5 Dashboard Enhancements

1. **Real-time metrics**: WebSocket-based live dashboard showing today's orders as they happen (would require a streaming data source).

2. **Drill-down capabilities**: Click on a city → see restaurants in that city → click a restaurant → see its menu items and orders.

3. **Export functionality**: Download charts as PNG/PDF, export data tables as CSV.

4. **User authentication**: Role-based access — analysts can see everything, restaurant partners see only their data.

---

## 28. Performance Characteristics

### 28.1 Data Volume

| Metric | Value |
|---|---|
| Total CSV file size | ~22 MB |
| Largest CSV | order_items.csv (9.2 MB) |
| Total rows across all datasets | ~290,000 |
| Largest table | fact_order_items (~200K rows) |
| PostgreSQL database size (on disk) | ~50–100 MB (including indexes) |

### 28.2 ETL Performance

| Stage | Estimated Time | Notes |
|---|---|---|
| EXTRACT (7 CSV reads) | 2–5 seconds | pandas.read_csv is fast for 22 MB total |
| TRANSFORM (7 transforms) | 5–15 seconds | Pandas operations on DataFrames up to 200K rows |
| LOAD (7 table inserts) | 10–30 seconds | Bulk inserts via multi-row INSERT, chunksize 5K |
| Index creation | 1–3 seconds | 7 indexes on loaded tables |
| **Total ETL** | **18–53 seconds** | For 80K orders + 200K order items |

### 28.3 Query Performance

| Query | Complexity | Estimated Time | Indexes Used |
|---|---|---|---|
| Q1 (Monthly Revenue) | Medium (CTE + window) | 50–200ms | idx_fo_date, idx_dd_yearmonth |
| Q2 (Top Restaurants) | Medium (GROUP BY + sort) | 50–150ms | idx_fo_restaurant |
| Q3 (CLV) | High (LEFT JOIN + NTILE) | 100–300ms | idx_fo_customer |
| Q8 (RFM) | High (multi-CTE + NTILE) | 100–400ms | idx_fo_customer |
| Q11 (Aggregate) | Medium (GROUP BY + upsert) | 200–500ms | idx_fo_date, idx_fo_restaurant, idx_dr_city |

With 80,000 orders, all queries complete in under 500ms. At 10 million orders, query times would increase significantly without partitioning or additional indexes.

### 28.4 ML Performance

| Stage | Estimated Time | Notes |
|---|---|---|
| Data extraction | 1–2 seconds | SQL query aggregating 80K orders to ~730 daily counts |
| Model training | 5–15 seconds | Prophet fitting on ~730 data points |
| Forecast generation | 1–2 seconds | 30-day prediction |
| Plot generation | 2–5 seconds | matplotlib rendering |
| Database write | 1–2 seconds | 30 rows to ml_order_forecast |
| **Total ML** | **10–26 seconds** | For 30-day forecast |

### 28.5 Dashboard Performance

| Metric | Value | Notes |
|---|---|---|
| First page load | 2–5 seconds | Initial database connection + query execution |
| Cached page load | < 1 second | Data served from Streamlit cache (5-minute TTL) |
| Chart rendering | < 1 second | Plotly renders client-side in browser |
| Memory usage | 100–200 MB | Streamlit server + pandas DataFrames |

### 28.6 Docker Resource Requirements

| Service | Minimum RAM | CPU |
|---|---|---|
| PostgreSQL DW | 256 MB | 0.5 cores |
| Airflow DB | 128 MB | 0.25 cores |
| Airflow (webserver + scheduler) | 512 MB | 1 core |
| Metabase DB | 128 MB | 0.25 cores |
| Metabase | 512 MB | 0.5 cores |
| **Total minimum** | **1.5 GB** | **2.5 cores** |
| **Recommended** | **4 GB** | **4 cores** |

---

## 29. Data Quality and Validation

### 29.1 Pre-ETL Validation

The Airflow DAG's `data_quality_check` task verifies:
- All 7 CSV files exist in `data/raw/`
- Each file meets minimum row count thresholds
- Missing files or insufficient row counts raise a `ValueError` and stop the pipeline

### 29.2 Transform-Time Validation

The `_log_quality()` function in the ETL pipeline:
- Calculates null percentages for every column in every DataFrame
- Counts duplicate rows
- Logs warnings for any quality issues found

This doesn't stop the pipeline but provides visibility into data quality.

### 29.3 Database-Level Validation

PostgreSQL enforces:
- **Primary key constraints**: No duplicate keys in any table
- **Foreign key constraints**: Every FK reference must point to an existing parent row
- **NOT NULL constraints**: Required columns cannot be null
- **UNIQUE constraints**: `dim_date.full_date` must be unique
- **Data type constraints**: Numeric columns reject string values, date columns reject invalid dates

### 29.4 Post-Load Validation

After ETL completion, the following can be verified:

```sql
-- Verify row counts
SELECT 'dim_date' AS tbl, COUNT(*) FROM dim_date
UNION ALL SELECT 'dim_customer', COUNT(*) FROM dim_customer
UNION ALL SELECT 'dim_restaurant', COUNT(*) FROM dim_restaurant
UNION ALL SELECT 'dim_menu_item', COUNT(*) FROM dim_menu_item
UNION ALL SELECT 'dim_delivery_agent', COUNT(*) FROM dim_delivery_agent
UNION ALL SELECT 'fact_orders', COUNT(*) FROM fact_orders
UNION ALL SELECT 'fact_order_items', COUNT(*) FROM fact_order_items;

-- Verify referential integrity (should return 0 rows)
SELECT fo.order_id FROM fact_orders fo
LEFT JOIN dim_customer c ON fo.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- Verify flag consistency (should return 0 rows)
SELECT order_id FROM fact_orders
WHERE is_delivered = 1 AND status != 'Delivered';
```

### 29.5 Test Coverage

The 20 unit tests in `tests/test_etl.py` provide automated validation of:
- Deduplication correctness
- String normalisation (Title Case, lowercase, strip)
- Feature engineering (tenure_days, experience_days, bands, segments)
- Date dimension completeness (weekend flags, holiday flags)
- Data type integrity (booleans are bool, numerics are numeric)
- Column completeness (all required columns present)

---

## 30. Deployment and Operations

### 30.1 Initial Setup

```bash
# 1. Clone or navigate to project directory
cd /path/to/foodflow

# 2. Install Python dependencies
pip install -r requirements.txt
pip install streamlit plotly pytest

# 3. Generate data
python scripts/generate_data.py

# 4. Start infrastructure
docker compose up -d

# 5. Run ETL
python scripts/etl_pipeline.py

# 6. Run ML forecast
python scripts/ml_forecast.py

# 7. Run tests
pytest tests/ -v

# 8. Launch dashboard
streamlit run scripts/dashboard_app.py --server.headless true
```

### 30.2 Daily Operations (via Airflow)

Once Airflow is running, the pipeline runs automatically daily at 03:00 IST:

1. **03:00 IST**: DAG triggers
2. **03:00–03:01**: Data quality check
3. **03:01–03:05**: ETL pipeline (extract, transform, load)
4. **03:05–03:06**: Refresh aggregate tables
5. **03:06–03:10**: ML forecast retraining
6. **03:10**: Email notification sent

### 30.3 Monitoring

- **Airflow UI** (`:8080`): View DAG runs, task logs, success/failure status
- **PostgreSQL logs**: `docker compose logs -f postgres`
- **Dashboard**: Streamlit and Metabase show data freshness through the latest order date

### 30.4 Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| "Connection refused" on port 5433 | PostgreSQL not started | `docker compose up -d postgres` |
| "Raw file missing" error | Data not generated | `python scripts/generate_data.py` |
| "Table does not exist" | Schema not initialised | `docker compose down -v && docker compose up -d` |
| Airflow DAG not visible | DAG file not in `airflow/dags/` | Copy file to `airflow/dags/` |
| Dashboard shows no data | ETL not run | `python scripts/etl_pipeline.py` |
| ML forecast fails | No data in fact_orders | Run ETL first, then forecast |

### 30.5 Backup and Recovery

- **Database backup**: `docker exec foodflow_postgres pg_dump -U dw_user foodflow_dw > backup.sql`
- **Database restore**: `docker exec -i foodflow_postgres psql -U dw_user foodflow_dw < backup.sql`
- **Volume backup**: Copy Docker volumes from `/var/lib/docker/volumes/`
- **CSV backup**: The raw CSVs in `data/raw/` are the source of truth — regenerate them if needed via `generate_data.py`

---

## 31. Appendix — Full SQL Queries

### Q1: Monthly Revenue Trend with MoM Growth

```sql
WITH monthly AS (
    SELECT
        d.year, d.month, d.month_name,
        SUM(fo.net_total) AS net_revenue,
        COUNT(*) AS total_orders,
        COUNT(*) FILTER (WHERE fo.is_delivered = 1) AS delivered_orders
    FROM fact_orders fo
    JOIN dim_date d ON fo.date_id = d.date_id
    WHERE LOWER(fo.status) != 'cancelled'
    GROUP BY d.year, d.month, d.month_name
),
with_growth AS (
    SELECT *,
        LAG(net_revenue) OVER (ORDER BY year, month) AS prev_revenue,
        ROUND((
            100.0 * (net_revenue - LAG(net_revenue) OVER (ORDER BY year, month))
            / NULLIF(LAG(net_revenue) OVER (ORDER BY year, month), 0)
        )::numeric, 2) AS mom_growth_pct
    FROM monthly
)
SELECT
    year, month, month_name,
    ROUND(net_revenue::numeric, 2) AS net_revenue_inr,
    total_orders, delivered_orders,
    ROUND((net_revenue / NULLIF(delivered_orders, 0))::numeric, 2) AS avg_order_value,
    mom_growth_pct
FROM with_growth
ORDER BY year, month;
```

### Q2: Top 10 Restaurants by Revenue

```sql
SELECT
    r.restaurant_id, r.name AS restaurant_name, r.city, r.cuisine_type, r.rating,
    COUNT(*) AS total_orders,
    ROUND(SUM(fo.net_total)::numeric, 2) AS net_revenue,
    ROUND(AVG(fo.net_total)::numeric, 2) AS avg_order_value,
    ROUND(AVG(fo.delivery_time_min)::numeric, 1) AS avg_delivery_min,
    ROUND((100.0 * SUM(fo.is_delivered) / COUNT(*))::numeric, 2) AS delivery_success_rate
FROM fact_orders fo
JOIN dim_restaurant r ON fo.restaurant_id = r.restaurant_id
GROUP BY r.restaurant_id, r.name, r.city, r.cuisine_type, r.rating
ORDER BY net_revenue DESC LIMIT 10;
```

### Q3: Customer Lifetime Value with Quartile Ranking

```sql
WITH clv AS (
    SELECT
        c.customer_id, c.full_name, c.city, c.customer_segment,
        COUNT(fo.order_id) AS total_orders,
        SUM(fo.net_total) AS lifetime_value,
        ROUND(AVG(fo.net_total)::numeric, 2) AS avg_order_value,
        MAX(fo.order_timestamp::DATE) AS last_order_date,
        CURRENT_DATE - MAX(fo.order_timestamp::DATE) AS days_since_last_order
    FROM dim_customer c
    LEFT JOIN fact_orders fo ON c.customer_id = fo.customer_id
       AND LOWER(fo.status) = 'delivered'
    GROUP BY c.customer_id, c.full_name, c.city, c.customer_segment
),
ranked AS (
    SELECT *,
        NTILE(4) OVER (ORDER BY lifetime_value DESC) AS clv_quartile
    FROM clv WHERE total_orders > 0
)
SELECT *,
    CASE clv_quartile
        WHEN 1 THEN 'Champion' WHEN 2 THEN 'Loyal'
        WHEN 3 THEN 'At-Risk'  WHEN 4 THEN 'Dormant'
    END AS clv_tier
FROM ranked ORDER BY lifetime_value DESC LIMIT 50;
```

### Q8: RFM Segmentation (Complete)

```sql
WITH base_rfm AS (
    SELECT
        c.customer_id, c.full_name, c.city, c.customer_segment,
        COUNT(*) AS frequency, SUM(fo.net_total) AS monetary,
        CURRENT_DATE - MAX(fo.order_timestamp::DATE) AS recency_days,
        AVG(fo.net_total) AS avg_order_value
    FROM dim_customer c
    JOIN fact_orders fo ON c.customer_id = fo.customer_id
    WHERE LOWER(fo.status) = 'delivered'
    GROUP BY c.customer_id, c.full_name, c.city, c.customer_segment
),
scored AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency_days DESC)  AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC)       AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)        AS m_score
    FROM base_rfm
),
segmented AS (
    SELECT *,
        r_score + f_score + m_score AS rfm_total,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2 AND m_score <= 2 THEN 'New Customers'
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 2 THEN 'Potential Loyalists'
            WHEN r_score >= 4 AND f_score >= 4 AND m_score <= 2 THEN 'Recent Customers'
            WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4 THEN 'At-Risk Customers'
            WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'About to Sleep'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Lost'
            WHEN r_score >= 3 AND f_score <= 2 AND m_score >= 3 THEN 'Can''t Lose Them'
            ELSE 'Others'
        END AS rfm_segment
    FROM scored
)
SELECT
    rfm_segment, COUNT(*) AS customer_count,
    ROUND(AVG(recency_days)::numeric, 1) AS avg_recency_days,
    ROUND(AVG(frequency)::numeric, 1) AS avg_frequency,
    ROUND(AVG(monetary)::numeric, 2) AS avg_monetary,
    ROUND(AVG(rfm_total)::numeric, 1) AS avg_rfm_score,
    MIN(rfm_total) AS min_rfm_score, MAX(rfm_total) AS max_rfm_score
FROM segmented
GROUP BY rfm_segment
ORDER BY avg_rfm_score DESC;
```

---

*End of Comprehensive Report — FoodFlow Analytics v1.0*
*This document covers every component, decision, implementation detail, and limitation of the project.*
