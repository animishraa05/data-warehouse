"""
FoodFlow Analytics — ETL Pipeline
==================================
Pipeline stages:
  E → Extract from CSV (simulates source systems)
  T → Transform: clean, normalize, feature-engineer
  L → Load into PostgreSQL Data Warehouse (star-schema)

Dependencies:
    pip install pandas numpy sqlalchemy psycopg2-binary python-dotenv

Environment (.env):
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=foodflow_dw
    DB_USER=dw_user
    DB_PASS=secret

Run:
    python etl_pipeline.py
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

# ── LOGGING ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("foodflow.etl")

load_dotenv()

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# ── DATABASE CONNECTION ────────────────────────────────────────────────────────
def get_engine():
    url = (
        f"postgresql+psycopg2://{os.getenv('DB_USER','dw_user')}:"
        f"{os.getenv('DB_PASS','secret')}@"
        f"{os.getenv('DB_HOST','localhost')}:"
        f"{os.getenv('DB_PORT','5433')}/"
        f"{os.getenv('DB_NAME','foodflow_dw')}"
    )
    return create_engine(url, pool_size=5, max_overflow=10)


# ══════════════════════════════════════════════════════════════════════════════
#  EXTRACT
# ══════════════════════════════════════════════════════════════════════════════
def extract() -> dict[str, pd.DataFrame]:
    """Read all raw CSV files into DataFrames."""
    log.info("EXTRACT — reading raw CSV sources")
    tables = ["customers", "restaurants", "menu_items",
              "delivery_agents", "orders", "order_items", "payments"]
    frames = {}
    for t in tables:
        path = RAW_DIR / f"{t}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Raw file missing: {path}  →  run generate_data.py first")
        frames[t] = pd.read_csv(path)
        log.info(f"  {t:<20} {len(frames[t]):>8,} rows  {len(frames[t].columns)} cols")
    return frames


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSFORM
# ══════════════════════════════════════════════════════════════════════════════

def _log_quality(name: str, df: pd.DataFrame):
    null_pct = df.isnull().mean().mul(100).round(2)
    problems = null_pct[null_pct > 0]
    if not problems.empty:
        log.warning(f"  {name} — nulls: {problems.to_dict()}")
    dupes = df.duplicated().sum()
    if dupes:
        log.warning(f"  {name} — {dupes} duplicate rows dropped")


def transform_customers(df: pd.DataFrame) -> pd.DataFrame:
    log.info("TRANSFORM — dim_customer")
    _log_quality("customers", df)
    df = df.drop_duplicates(subset="customer_id")
    df["registration_date"] = pd.to_datetime(df["registration_date"])
    df["full_name"] = df["full_name"].str.strip().str.title()
    df["email"] = df["email"].str.lower().str.strip()
    df["city"] = df["city"].str.strip()
    df["is_premium"] = df["is_premium"].astype(bool)

    # ── Feature: tenure_days (days since registration up to end of dataset)
    REFERENCE_DATE = pd.Timestamp("2024-12-31")
    df["tenure_days"] = (REFERENCE_DATE - df["registration_date"]).dt.days

    # ── Feature: customer_segment
    conditions = [
        df["is_premium"] & (df["tenure_days"] >= 365),
        df["is_premium"] & (df["tenure_days"] < 365),
        (~df["is_premium"]) & (df["tenure_days"] >= 365),
    ]
    choices = ["Premium-Loyal", "Premium-New", "Regular-Loyal"]
    df["customer_segment"] = np.select(conditions, choices, default="Regular-New")

    return df[[
        "customer_id", "full_name", "email", "phone",
        "city", "age_group", "gender", "is_premium",
        "registration_date", "tenure_days", "customer_segment",
    ]]


def transform_restaurants(df: pd.DataFrame) -> pd.DataFrame:
    log.info("TRANSFORM — dim_restaurant")
    _log_quality("restaurants", df)
    df = df.drop_duplicates(subset="restaurant_id")
    df["name"] = df["name"].str.strip().str.title()
    df["city"] = df["city"].str.strip()
    df["onboarded_date"] = pd.to_datetime(df["onboarded_date"])

    # ── Feature: rating_band
    bins   = [0, 2.5, 3.5, 4.2, 5.0]
    labels = ["Poor", "Average", "Good", "Excellent"]
    df["rating_band"] = pd.cut(df["rating"], bins=bins, labels=labels, right=True)

    return df[[
        "restaurant_id", "name", "city", "cuisine_type",
        "rating", "rating_band", "total_reviews",
        "avg_prep_time_min", "is_veg_only", "onboarded_date",
    ]]


def transform_menu_items(df: pd.DataFrame) -> pd.DataFrame:
    log.info("TRANSFORM — dim_menu_item")
    _log_quality("menu_items", df)
    df = df.drop_duplicates(subset="item_id")

    # ── Feature: price_band
    bins   = [0, 100, 200, 350, float("inf")]
    labels = ["Budget", "Affordable", "Mid-Range", "Premium"]
    df["price_band"] = pd.cut(df["price"], bins=bins, labels=labels, right=True)

    return df[[
        "item_id", "restaurant_id", "item_name", "category",
        "price", "price_band", "is_available", "is_veg", "calories",
    ]]


def transform_agents(df: pd.DataFrame) -> pd.DataFrame:
    log.info("TRANSFORM — dim_delivery_agent")
    _log_quality("delivery_agents", df)
    df = df.drop_duplicates(subset="agent_id")
    df["name"] = df["name"].str.strip().str.title()
    df["joined_date"] = pd.to_datetime(df["joined_date"])

    REFERENCE_DATE = pd.Timestamp("2024-12-31")
    df["experience_days"] = (REFERENCE_DATE - df["joined_date"]).dt.days

    # ── Feature: performance_tier
    bins   = [0, 3.5, 4.2, 4.7, 5.0]
    labels = ["Below Average", "Average", "Good", "Top Performer"]
    df["performance_tier"] = pd.cut(df["rating"], bins=bins, labels=labels, right=True)

    return df[[
        "agent_id", "name", "city", "vehicle",
        "rating", "performance_tier", "experience_days", "joined_date",
    ]]


def build_dim_date(start="2023-01-01", end="2024-12-31") -> pd.DataFrame:
    """Generate a complete date dimension."""
    log.info("TRANSFORM — dim_date")
    dates = pd.date_range(start=start, end=end, freq="D")
    df = pd.DataFrame({"full_date": dates})
    df["date_id"]     = df["full_date"].dt.strftime("%Y%m%d").astype(int)
    df["day"]         = df["full_date"].dt.day
    df["month"]       = df["full_date"].dt.month
    df["month_name"]  = df["full_date"].dt.strftime("%B")
    df["quarter"]     = df["full_date"].dt.quarter
    df["year"]        = df["full_date"].dt.year
    df["week"]        = df["full_date"].dt.isocalendar().week.astype(int)
    df["day_of_week"] = df["full_date"].dt.dayofweek          # 0=Mon
    df["day_name"]    = df["full_date"].dt.strftime("%A")
    df["is_weekend"]  = df["day_of_week"].isin([5, 6])

    # Indian public holidays (subset — extend as needed)
    holidays = {
        "2023-01-26", "2023-08-15", "2023-10-02", "2023-10-24",
        "2024-01-26", "2024-08-15", "2024-10-02", "2024-10-31",
    }
    df["is_holiday"] = df["full_date"].dt.strftime("%Y-%m-%d").isin(holidays)
    df["is_peak_season"] = df["month"].isin([10, 11, 12, 1])  # festive + winter
    return df


def transform_orders(
    orders: pd.DataFrame,
    payments: pd.DataFrame,
    dim_date: pd.DataFrame,
) -> pd.DataFrame:
    """Build fact_orders by joining orders + payments and attaching date_id."""
    log.info("TRANSFORM — fact_orders")
    _log_quality("orders", orders)
    _log_quality("payments", payments)

    orders = orders.drop_duplicates(subset="order_id")
    payments = payments.drop_duplicates(subset="order_id")

    fact = orders.merge(payments[
        ["order_id", "method", "gross_total", "discount_amount", "delivery_fee", "net_total"]
    ], on="order_id", how="left")

    # Parse timestamp
    fact["order_timestamp"] = pd.to_datetime(fact["order_timestamp"])
    fact["order_date"]      = fact["order_timestamp"].dt.date.astype(str)
    fact["order_hour"]      = fact["order_timestamp"].dt.hour

    # Attach date_id surrogate key
    date_map = dict(zip(
        dim_date["full_date"].dt.strftime("%Y-%m-%d"),
        dim_date["date_id"],
    ))
    fact["date_id"] = fact["order_date"].map(date_map)

    # Fill nulls that arise from cancelled orders with zero
    money_cols = ["gross_total", "discount_amount", "delivery_fee", "net_total"]
    fact[money_cols] = fact[money_cols].fillna(0.0)

    # ── Derived KPI columns
    fact["is_delivered"] = (fact["status"] == "Delivered").astype(int)
    fact["is_cancelled"]  = (fact["status"] == "Cancelled").astype(int)

    # ── Order time-of-day band
    bins   = [0, 6, 11, 14, 17, 20, 24]
    labels = ["Night", "Morning", "Lunch", "Afternoon", "Dinner", "Late Night"]
    fact["time_of_day"] = pd.cut(fact["order_hour"], bins=bins, labels=labels, right=False)

    return fact[[
        "order_id", "customer_id", "restaurant_id", "agent_id", "date_id",
        "order_timestamp", "order_hour", "time_of_day", "platform", "status",
        "is_delivered", "is_cancelled",
        "delivery_time_min", "distance_km", "discount_pct",
        "gross_total", "discount_amount", "delivery_fee", "net_total",
        "method",
    ]]


def transform_order_items(
    order_items: pd.DataFrame,
    fact_orders: pd.DataFrame,
) -> pd.DataFrame:
    """Bridge / line-item fact table."""
    log.info("TRANSFORM — fact_order_items")
    oi = order_items.drop_duplicates(subset="order_item_id")

    # Attach date_id from fact_orders for easy slicing
    oi = oi.merge(fact_orders[["order_id", "date_id", "customer_id"]], on="order_id", how="left")
    oi["revenue"] = oi["line_total"]   # rename for clarity in the warehouse
    return oi[[
        "order_item_id", "order_id", "item_id",
        "customer_id", "date_id",
        "quantity", "unit_price", "revenue",
    ]]


# ══════════════════════════════════════════════════════════════════════════════
#  LOAD
# ══════════════════════════════════════════════════════════════════════════════
def load(engine, table_name: str, df: pd.DataFrame, if_exists="replace"):
    log.info(f"LOAD  → {table_name:<30} {len(df):>8,} rows")
    df.to_sql(
        table_name,
        con=engine,
        if_exists=if_exists,
        index=False,
        chunksize=5_000,
        method="multi",
    )


def apply_indexes(engine):
    """Add performance indexes after bulk load."""
    log.info("Applying indexes …")
    statements = [
        "CREATE INDEX IF NOT EXISTS idx_fact_orders_customer   ON fact_orders(customer_id);",
        "CREATE INDEX IF NOT EXISTS idx_fact_orders_restaurant ON fact_orders(restaurant_id);",
        "CREATE INDEX IF NOT EXISTS idx_fact_orders_date       ON fact_orders(date_id);",
        "CREATE INDEX IF NOT EXISTS idx_fact_orders_agent      ON fact_orders(agent_id);",
        "CREATE INDEX IF NOT EXISTS idx_fact_oi_item           ON fact_order_items(item_id);",
        "CREATE INDEX IF NOT EXISTS idx_fact_oi_order          ON fact_order_items(order_id);",
        "CREATE INDEX IF NOT EXISTS idx_dim_date_ym            ON dim_date(year, month);",
    ]
    with engine.connect() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        conn.commit()
    log.info("Indexes applied ✓")


# ══════════════════════════════════════════════════════════════════════════════
#  ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════
def run_pipeline():
    log.info("=" * 60)
    log.info("FoodFlow Analytics — ETL Pipeline START")
    log.info("=" * 60)

    # EXTRACT
    raw = extract()

    # TRANSFORM
    dim_customer  = transform_customers(raw["customers"])
    dim_restaurant = transform_restaurants(raw["restaurants"])
    dim_menu_item  = transform_menu_items(raw["menu_items"])
    dim_agent      = transform_agents(raw["delivery_agents"])
    dim_date       = build_dim_date()
    fact_orders    = transform_orders(raw["orders"], raw["payments"], dim_date)
    fact_oi        = transform_order_items(raw["order_items"], fact_orders)

    # LOAD
    engine = get_engine()
    load(engine, "dim_date",           dim_date)
    load(engine, "dim_customer",       dim_customer)
    load(engine, "dim_restaurant",     dim_restaurant)
    load(engine, "dim_menu_item",      dim_menu_item)
    load(engine, "dim_delivery_agent", dim_agent)
    load(engine, "fact_orders",        fact_orders)
    load(engine, "fact_order_items",   fact_oi)

    apply_indexes(engine)

    log.info("=" * 60)
    log.info("ETL Pipeline COMPLETE ✓")
    log.info("=" * 60)


if __name__ == "__main__":
    run_pipeline()
