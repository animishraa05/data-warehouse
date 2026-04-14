"""
FoodFlow Analytics — Apache Airflow DAG
========================================
Orchestrates the daily ETL pipeline:
  1. data_quality_check   — assert raw files exist and row counts are non-zero
  2. run_etl              — execute the full ETL (extract → transform → load)
  3. refresh_aggregates   — repopulate agg_monthly_revenue
  4. run_ml_predictions   — re-train and score order_volume forecast model
  5. notify_success       — email/Slack alert on completion

Schedule : Daily at 02:30 IST (21:00 UTC)

Install:
    pip install apache-airflow apache-airflow-providers-postgres
    airflow db init
    # Copy this file to $AIRFLOW_HOME/dags/
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.utils.email import send_email

# ── DAG-level defaults ──────────────────────────────────────────────────────
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

dag = DAG(
    dag_id          = "foodflow_daily_etl",
    description     = "FoodFlow Analytics — daily data pipeline",
    schedule_interval = "30 21 * * *",   # 21:30 UTC = 03:00 IST next day
    start_date      = datetime(2024, 1, 1),
    catchup         = False,
    default_args    = default_args,
    tags            = ["foodflow", "etl", "data-warehouse"],
    doc_md          = """
## FoodFlow Daily ETL
End-to-end pipeline from raw CSVs to star-schema warehouse.
**SLA:** complete within 60 minutes of schedule time.
""",
)

# ── Task 1 : Data Quality Check ─────────────────────────────────────────────
def data_quality_check(**context):
    """Verify raw source files exist and meet minimum row-count thresholds."""
    import os
    from pathlib import Path

    RAW_DIR = Path("/opt/airflow/foodflow/data/raw")
    THRESHOLDS = {
        "customers.csv":        100,
        "restaurants.csv":      10,
        "menu_items.csv":       50,
        "delivery_agents.csv":  10,
        "orders.csv":           500,
        "order_items.csv":      1000,
        "payments.csv":         500,
    }

    errors = []
    for fname, min_rows in THRESHOLDS.items():
        fpath = RAW_DIR / fname
        if not fpath.exists():
            errors.append(f"MISSING: {fname}")
            continue
        import csv
        with open(fpath) as f:
            row_count = sum(1 for _ in csv.reader(f)) - 1  # subtract header
        if row_count < min_rows:
            errors.append(f"LOW ROWS: {fname} has {row_count} < {min_rows}")

    if errors:
        raise ValueError("Data quality check FAILED:\n" + "\n".join(errors))

    print("✓ All source files passed quality checks")
    return True


task_dq_check = PythonOperator(
    task_id         = "data_quality_check",
    python_callable = data_quality_check,
    provide_context = True,
    dag             = dag,
)

# ── Task 2 : Run ETL ─────────────────────────────────────────────────────────
task_run_etl = BashOperator(
    task_id      = "run_etl_pipeline",
    bash_command = "cd /opt/airflow/foodflow && python scripts/etl_pipeline.py",
    dag          = dag,
)

# ── Task 3 : Refresh Aggregate Table ────────────────────────────────────────
task_refresh_agg = PostgresOperator(
    task_id          = "refresh_aggregates",
    postgres_conn_id = "foodflow_postgres",
    sql              = """
        TRUNCATE TABLE agg_monthly_revenue;
        INSERT INTO agg_monthly_revenue
        SELECT
            d.year, d.month, d.month_name,
            r.city, r.cuisine_type,
            COUNT(fo.order_id),
            COUNT(*) FILTER (WHERE fo.is_delivered = 1),
            COUNT(*) FILTER (WHERE fo.is_cancelled = 1),
            ROUND(SUM(fo.gross_total), 2),
            ROUND(SUM(fo.net_total), 2),
            ROUND(AVG(fo.net_total) FILTER (WHERE fo.is_delivered = 1), 2),
            ROUND(AVG(fo.delivery_time_min) FILTER (WHERE fo.is_delivered = 1), 2)
        FROM fact_orders fo
        JOIN dim_date       d ON fo.date_id       = d.date_id
        JOIN dim_restaurant r ON fo.restaurant_id = r.restaurant_id
        GROUP BY d.year, d.month, d.month_name, r.city, r.cuisine_type;
    """,
    dag = dag,
)

# ── Task 4 : ML Forecasting ──────────────────────────────────────────────────
task_ml_forecast = BashOperator(
    task_id      = "ml_order_volume_forecast",
    bash_command = "cd /opt/airflow/foodflow && python scripts/ml_forecast.py",
    dag          = dag,
)

# ── Task 5 : Success Notification ────────────────────────────────────────────
def notify_success(**context):
    execution_date = context["ds"]
    html_content = f"""
    <h3>✅ FoodFlow ETL Pipeline Completed</h3>
    <p><b>Execution Date:</b> {execution_date}</p>
    <p><b>DAG:</b> foodflow_daily_etl</p>
    <p>All tasks completed successfully. Dashboard data is refreshed.</p>
    """
    send_email(
        to      = ["analytics@foodflow.in"],
        subject = f"[FoodFlow] ETL Success — {execution_date}",
        html_content = html_content,
    )


task_notify = PythonOperator(
    task_id         = "notify_success",
    python_callable = notify_success,
    provide_context = True,
    dag             = dag,
)

# ── Pipeline Dependencies ─────────────────────────────────────────────────────
task_dq_check >> task_run_etl >> task_refresh_agg >> task_ml_forecast >> task_notify
