"""
FoodFlow Analytics — ML Order Volume Forecasting
==================================================
Model   : Facebook Prophet (time-series forecasting)
Target  : Daily order volume (next 30 days)
Inputs  : Historical delivered order counts from data warehouse
"""

import os
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("foodflow.ml")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PLOTS_DIR = Path(__file__).resolve().parent.parent / "outputs" / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# DB CONNECTION
# ─────────────────────────────────────────────────────────────
def get_engine():
    url = (
        f"postgresql+psycopg2://{os.getenv('DB_USER','dw_user')}:"
        f"{os.getenv('DB_PASS','secret')}@"
        f"{os.getenv('DB_HOST','localhost')}:"
        f"{os.getenv('DB_PORT','5433')}/"
        f"{os.getenv('DB_NAME','foodflow_dw')}"
    )
    return create_engine(url)


# ─────────────────────────────────────────────────────────────
# LOAD TRAINING DATA
# ─────────────────────────────────────────────────────────────
def load_training_data(engine) -> pd.DataFrame:
    sql = """
        SELECT
            d.full_date        AS ds,
            COUNT(fo.order_id) AS y
        FROM fact_orders fo
        JOIN dim_date d ON fo.date_id = d.date_id
        WHERE fo.status = 'Delivered'
        GROUP BY d.full_date
        ORDER BY d.full_date;
    """
    df = pd.read_sql(sql, engine)
    df["ds"] = pd.to_datetime(df["ds"])
    log.info(f"Training data: {len(df)} daily observations")
    return df


# ─────────────────────────────────────────────────────────────
# MODEL TRAINING + FORECAST
# ─────────────────────────────────────────────────────────────
def train_and_forecast(df: pd.DataFrame, horizon: int = 30):
    from prophet import Prophet

    m = Prophet(
        changepoint_prior_scale=0.15,
        seasonality_mode="multiplicative",
        weekly_seasonality=True,
        yearly_seasonality=True,
        daily_seasonality=False,
    )

    # Weekend feature
    df["is_weekend"] = df["ds"].dt.dayofweek.isin([5, 6]).astype(int)
    m.add_regressor("is_weekend")

    log.info("Fitting Prophet model …")
    m.fit(df)

    future = m.make_future_dataframe(periods=horizon)
    future["is_weekend"] = future["ds"].dt.dayofweek.isin([5, 6]).astype(int)

    forecast = m.predict(future)
    log.info(f"Forecast generated for {horizon} days ahead")

    return m, forecast


# ─────────────────────────────────────────────────────────────
# SAVE PLOT
# ─────────────────────────────────────────────────────────────
def save_forecast_plot(m, forecast, path: Path):
    try:
        import matplotlib.pyplot as plt
        fig = m.plot(forecast, xlabel="Date", ylabel="Order Volume")
        fig.suptitle("FoodFlow — 30-Day Order Volume Forecast", fontsize=13)
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        log.info(f"Forecast plot saved → {path}")
    except Exception as e:
        log.warning(f"Plot generation failed: {e}")


# ─────────────────────────────────────────────────────────────
# MODEL EVALUATION
# ─────────────────────────────────────────────────────────────
def evaluate_model(df: pd.DataFrame, forecast_full: pd.DataFrame) -> dict:
    """
    Compute MAPE, MAE, RMSE on the training period (in-sample fit).
    Uses historical data where we have both actual and fitted values.
    """
    # Get fitted values for training dates
    fitted = forecast_full[["ds", "yhat"]].dropna()
    merged = df.merge(fitted, on="ds", how="inner")

    if len(merged) == 0:
        return {"mape": None, "mae": None, "rmse": None, "n_observations": 0}

    actual = merged["y"].values
    predicted = merged["yhat"].values
    error = actual - predicted

    mae = np.mean(np.abs(error))
    rmse = np.sqrt(np.mean(error ** 2))

    # MAPE — avoid division by zero
    mask = actual > 0
    if mask.sum() > 0:
        mape = np.mean(np.abs(error[mask] / actual[mask])) * 100
    else:
        mape = None

    return {
        "mape": round(float(mape), 2) if mape is not None else None,
        "mae": round(float(mae), 2),
        "rmse": round(float(rmse), 2),
        "n_observations": len(merged),
    }


def write_metrics_to_dw(engine, metrics: dict):
    """Write evaluation metrics to a table for dashboard consumption."""
    import json
    from datetime import datetime

    row = pd.DataFrame([{
        "evaluated_at": datetime.now(),
        "mape": metrics.get("mape"),
        "mae": metrics.get("mae"),
        "rmse": metrics.get("rmse"),
        "n_observations": metrics.get("n_observations"),
    }])

    row.to_sql("ml_model_metrics", engine, if_exists="append", index=False)


# ─────────────────────────────────────────────────────────────
# WRITE TO DATA WAREHOUSE (FIXED)
# ─────────────────────────────────────────────────────────────
def write_forecast_to_dw(engine, forecast: pd.DataFrame, df: pd.DataFrame):
    """
    Correctly extract only FUTURE predictions.
    Uses last training date instead of system time (critical fix).
    """

    last_date = df["ds"].max()

    output = forecast[forecast["ds"] > last_date][
        ["ds", "yhat", "yhat_lower", "yhat_upper"]
    ].copy()

    output.columns = [
        "forecast_date",
        "predicted_orders",
        "lower_bound",
        "upper_bound",
    ]

    # Clean values
    output["predicted_orders"] = output["predicted_orders"].clip(lower=0).round().astype(int)
    output["lower_bound"] = output["lower_bound"].clip(lower=0).round().astype(int)
    output["upper_bound"] = output["upper_bound"].clip(lower=0).round().astype(int)
    output["created_at"] = datetime.now()

    # Sort properly
    output = output.sort_values("forecast_date")

    # Write to DB
    output.to_sql("ml_order_forecast", engine, if_exists="replace", index=False)

    log.info(f"Forecast written to ml_order_forecast ({len(output)} rows)")

    # Preview
    print("\n📈  Next 7-day Order Volume Forecast:")
    print(output.head(7).to_string(index=False))


# ─────────────────────────────────────────────────────────────
# RUN PIPELINE
# ─────────────────────────────────────────────────────────────
def run():
    engine = get_engine()
    df = load_training_data(engine)

    model, fc = train_and_forecast(df, horizon=30)

    # Evaluate model quality
    metrics = evaluate_model(df, fc)
    log.info(f"Model evaluation → MAPE: {metrics['mape']}, MAE: {metrics['mae']}, RMSE: {metrics['rmse']}")
    write_metrics_to_dw(engine, metrics)

    save_forecast_plot(model, fc, PLOTS_DIR / "forecast_plot.png")

    write_forecast_to_dw(engine, fc, df)

    log.info("ML forecasting complete ✓")


if __name__ == "__main__":
    run()
