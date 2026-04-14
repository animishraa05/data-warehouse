"""
FoodFlow Analytics — ETL Pipeline Unit Tests
==============================================
Tests core transformation logic without needing a running database.

Run:
    pytest tests/ -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

# Import transform functions from the ETL pipeline
import sys
from pathlib import Path

# Add parent directory to path so we can import etl_pipeline
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from etl_pipeline import (
    transform_customers,
    transform_restaurants,
    transform_menu_items,
    transform_agents,
    build_dim_date,
)


# ── FIXTURES ──────────────────────────────────────────────────

@pytest.fixture
def sample_customers():
    return pd.DataFrame({
        "customer_id": ["CUST00001", "CUST00002", "CUST00003", "CUST00001"],
        "full_name": ["  rajesh kumar  ", "PRIYA SHARMA", "amit patel", "rajesh kumar"],
        "email": [" Rajesh@Gmail.COM ", "priya@yahoo.co.in", "amit@test.com", "Rajesh@Gmail.COM"],
        "phone": ["9876543210", "9876543211", "9876543212", "9876543210"],
        "city": [" Mumbai ", "Delhi", "Bengaluru", " Mumbai "],
        "age_group": ["25-34", "35-44", "18-24", "25-34"],
        "gender": ["Male", "Female", "Male", "Male"],
        "is_premium": [True, False, True, True],
        "registration_date": ["2023-01-15", "2024-06-01", "2022-03-10", "2023-01-15"],
    })


@pytest.fixture
def sample_restaurants():
    return pd.DataFrame({
        "restaurant_id": ["REST0001", "REST0002"],
        "name": ["  spice kitchen  ", "ITALIAN HOUSE"],
        "city": ["Mumbai", "Delhi"],
        "cuisine_type": ["North Indian", "Italian"],
        "rating": [2.3, 4.5],
        "total_reviews": [120, 890],
        "avg_prep_time_min": [25, 30],
        "is_veg_only": [False, True],
        "onboarded_date": ["2022-05-10", "2023-01-01"],
    })


@pytest.fixture
def sample_menu_items():
    return pd.DataFrame({
        "item_id": ["ITEM00001", "ITEM00002", "ITEM00003"],
        "restaurant_id": ["REST0001", "REST0001", "REST0002"],
        "item_name": ["Butter Chicken", "Paneer Tikka", "Margherita"],
        "category": ["Main Course", "Starters", "Main Course"],
        "price": [80.0, 350.0, 250.0],
        "is_available": [True, True, False],
        "is_veg": [False, True, True],
        "calories": [450, 300, 600],
    })


@pytest.fixture
def sample_agents():
    return pd.DataFrame({
        "agent_id": ["AGT0001", "AGT0002"],
        "name": ["  suresh yadav  ", "RAMESH KUMAR"],
        "city": ["Mumbai", "Delhi"],
        "vehicle": ["Bike", "Scooter"],
        "rating": [3.2, 4.8],
        "joined_date": ["2023-06-01", "2022-01-15"],
    })


# ── TESTS ─────────────────────────────────────────────────────

class TestTransformCustomers:
    def test_deduplication(self, sample_customers):
        result = transform_customers(sample_customers)
        assert len(result) == 3, "Should remove duplicate customer_id rows"

    def test_name_normalisation(self, sample_customers):
        result = transform_customers(sample_customers)
        names = result["full_name"].tolist()
        assert "Rajesh Kumar" in names
        assert "Priya Sharma" in names

    def test_email_normalisation(self, sample_customers):
        result = transform_customers(sample_customers)
        emails = result["email"].tolist()
        assert all(e == e.lower().strip() for e in emails)

    def test_city_stripped(self, sample_customers):
        result = transform_customers(sample_customers)
        assert " Mumbai" not in result["city"].tolist()

    def test_tenure_days(self, sample_customers):
        result = transform_customers(sample_customers)
        # CUST00003 registered 2022-03-10, reference 2024-12-31 → ~1027 days
        row = result[result["customer_id"] == "CUST00003"]
        assert row["tenure_days"].values[0] > 1000

    def test_customer_segments_exist(self, sample_customers):
        result = transform_customers(sample_customers)
        valid_segments = {"Premium-Loyal", "Premium-New", "Regular-Loyal", "Regular-New"}
        assert set(result["customer_segment"].unique()).issubset(valid_segments)

    def test_required_columns(self, sample_customers):
        result = transform_customers(sample_customers)
        expected_cols = [
            "customer_id", "full_name", "email", "phone", "city",
            "age_group", "gender", "is_premium", "registration_date",
            "tenure_days", "customer_segment",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"


class TestTransformRestaurants:
    def test_rating_bands(self, sample_restaurants):
        result = transform_restaurants(sample_restaurants)
        assert result.loc[0, "rating_band"] == "Poor"
        assert result.loc[1, "rating_band"] == "Excellent"

    def test_name_normalisation(self, sample_restaurants):
        result = transform_restaurants(sample_restaurants)
        assert result["name"].tolist() == ["Spice Kitchen", "Italian House"]


class TestTransformMenuItems:
    def test_price_bands(self, sample_menu_items):
        result = transform_menu_items(sample_menu_items)
        bands = dict(zip(result["item_id"], result["price_band"]))
        assert bands["ITEM00001"] == "Budget"    # ₹80  → (0, 100]
        assert bands["ITEM00002"] == "Mid-Range"  # ₹350 → (200, 350], right=True
        assert bands["ITEM00003"] == "Mid-Range"  # ₹250 → (200, 350]


class TestTransformAgents:
    def test_performance_tiers(self, sample_agents):
        result = transform_agents(sample_agents)
        tiers = dict(zip(result["agent_id"], result["performance_tier"]))
        assert tiers["AGT0001"] == "Below Average"   # rating 3.2 → (0, 3.5]
        assert tiers["AGT0002"] == "Top Performer"   # rating 4.8 → (4.7, 5.0]

    def test_experience_days(self, sample_agents):
        result = transform_agents(sample_agents)
        # AGT0002 joined 2022-01-15, reference 2024-12-31 → ~1081 days
        row = result[result["agent_id"] == "AGT0002"]
        assert row["experience_days"].values[0] > 1000


class TestBuildDimDate:
    def test_date_range(self):
        result = build_dim_date("2023-01-01", "2023-01-10")
        assert len(result) == 10

    def test_date_id_format(self):
        result = build_dim_date("2023-01-01", "2023-01-05")
        assert result.loc[0, "date_id"] == 20230101
        assert result.loc[4, "date_id"] == 20230105

    def test_weekend_flag(self):
        result = build_dim_date("2023-01-01", "2023-01-07")
        # Jan 1 2023 = Sunday, Jan 7 2023 = Saturday
        weekends = result[result["is_weekend"]]
        assert len(weekends) >= 2

    def test_holiday_flag(self):
        result = build_dim_date("2023-01-01", "2023-12-31")
        republic_day = result[result["full_date"] == "2023-01-26"]
        assert republic_day["is_holiday"].values[0]

    def test_required_columns(self):
        result = build_dim_date("2023-01-01", "2023-01-05")
        required = [
            "date_id", "full_date", "day", "month", "month_name",
            "quarter", "year", "week", "day_of_week", "day_name",
            "is_weekend", "is_holiday", "is_peak_season",
        ]
        for col in required:
            assert col in result.columns


class TestDataIntegrity:
    """Tests that verify transformation chain produces consistent data."""

    def test_no_null_keys_after_transform(self, sample_customers):
        result = transform_customers(sample_customers)
        assert result["customer_id"].isnull().sum() == 0

    def test_boolean_columns(self, sample_customers):
        result = transform_customers(sample_customers)
        assert result["is_premium"].dtype == bool

    def test_numeric_columns_are_numeric(self, sample_restaurants):
        result = transform_restaurants(sample_restaurants)
        assert pd.api.types.is_numeric_dtype(result["total_reviews"])
        assert pd.api.types.is_numeric_dtype(result["avg_prep_time_min"])
