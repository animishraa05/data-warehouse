"""
FoodFlow Analytics — Synthetic Data Generator
=============================================
Generates realistic CSV datasets for:
  - customers, restaurants, menu_items, orders, order_items, delivery_agents, payments

Run:
    pip install faker pandas numpy
    python generate_data.py

Output: ../data/raw/  (one CSV per entity)
"""

import os, random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker("en_IN")  # Indian locale — realistic names, cities, phone numbers
random.seed(42)
np.random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── CONFIG ─────────────────────────────────────────────────────────────────────
N_CUSTOMERS        = 5_000
N_RESTAURANTS      = 200
N_MENU_ITEMS       = 1_500   # ~7–8 items per restaurant
N_DELIVERY_AGENTS  = 300
N_ORDERS           = 80_000
START_DATE         = datetime(2023, 1, 1)
END_DATE           = datetime(2024, 12, 31)

CITIES = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai",
          "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Indore"]

CUISINES = ["North Indian", "South Indian", "Chinese", "Italian",
            "Continental", "Fast Food", "Biryani", "Desserts", "Beverages", "Snacks"]

CATEGORIES = ["Starters", "Main Course", "Breads", "Rice", "Beverages", "Desserts", "Combos"]

ORDER_STATUSES = ["Delivered", "Delivered", "Delivered", "Delivered",
                  "Cancelled", "Refunded"]  # ~67 % delivered

PAYMENT_METHODS = ["UPI", "Credit Card", "Debit Card", "Cash on Delivery", "Wallet"]

# ── 1. CUSTOMERS ───────────────────────────────────────────────────────────────
print("Generating customers …")
customers = pd.DataFrame({
    "customer_id":    [f"CUST{str(i).zfill(5)}" for i in range(1, N_CUSTOMERS + 1)],
    "full_name":      [fake.name() for _ in range(N_CUSTOMERS)],
    "email":          [fake.email() for _ in range(N_CUSTOMERS)],
    "phone":          [fake.phone_number() for _ in range(N_CUSTOMERS)],
    "city":           np.random.choice(CITIES, N_CUSTOMERS),
    "registration_date": [
        (START_DATE - timedelta(days=random.randint(0, 730))).strftime("%Y-%m-%d")
        for _ in range(N_CUSTOMERS)
    ],
    "age_group":      np.random.choice(["18-24", "25-34", "35-44", "45-54", "55+"],
                                       N_CUSTOMERS, p=[0.25, 0.35, 0.20, 0.12, 0.08]),
    "gender":         np.random.choice(["Male", "Female", "Other"],
                                       N_CUSTOMERS, p=[0.55, 0.42, 0.03]),
    "is_premium":     np.random.choice([True, False], N_CUSTOMERS, p=[0.18, 0.82]),
})
customers.to_csv(f"{OUTPUT_DIR}/customers.csv", index=False)

# ── 2. RESTAURANTS ─────────────────────────────────────────────────────────────
print("Generating restaurants …")
restaurants = pd.DataFrame({
    "restaurant_id":   [f"REST{str(i).zfill(4)}" for i in range(1, N_RESTAURANTS + 1)],
    "name":            [fake.company() + " Kitchen" for _ in range(N_RESTAURANTS)],
    "city":            np.random.choice(CITIES, N_RESTAURANTS),
    "cuisine_type":    np.random.choice(CUISINES, N_RESTAURANTS),
    "rating":          np.round(np.random.uniform(2.5, 5.0, N_RESTAURANTS), 1),
    "total_reviews":   np.random.randint(50, 5000, N_RESTAURANTS),
    "avg_prep_time_min": np.random.randint(15, 50, N_RESTAURANTS),
    "is_veg_only":     np.random.choice([True, False], N_RESTAURANTS, p=[0.20, 0.80]),
    "onboarded_date":  [
        (START_DATE - timedelta(days=random.randint(0, 1095))).strftime("%Y-%m-%d")
        for _ in range(N_RESTAURANTS)
    ],
})
restaurants.to_csv(f"{OUTPUT_DIR}/restaurants.csv", index=False)

# ── 3. MENU ITEMS ──────────────────────────────────────────────────────────────
print("Generating menu items …")
rest_ids = restaurants["restaurant_id"].tolist()
menu_items = pd.DataFrame({
    "item_id":       [f"ITEM{str(i).zfill(5)}" for i in range(1, N_MENU_ITEMS + 1)],
    "restaurant_id": np.random.choice(rest_ids, N_MENU_ITEMS),
    "item_name":     [fake.bs().title() for _ in range(N_MENU_ITEMS)],
    "category":      np.random.choice(CATEGORIES, N_MENU_ITEMS),
    "price":         np.round(np.random.uniform(50, 600, N_MENU_ITEMS), 2),
    "is_available":  np.random.choice([True, False], N_MENU_ITEMS, p=[0.92, 0.08]),
    "is_veg":        np.random.choice([True, False], N_MENU_ITEMS, p=[0.55, 0.45]),
    "calories":      np.random.randint(100, 900, N_MENU_ITEMS),
})
menu_items.to_csv(f"{OUTPUT_DIR}/menu_items.csv", index=False)

# ── 4. DELIVERY AGENTS ─────────────────────────────────────────────────────────
print("Generating delivery agents …")
delivery_agents = pd.DataFrame({
    "agent_id":   [f"AGT{str(i).zfill(4)}" for i in range(1, N_DELIVERY_AGENTS + 1)],
    "name":       [fake.name() for _ in range(N_DELIVERY_AGENTS)],
    "city":       np.random.choice(CITIES, N_DELIVERY_AGENTS),
    "vehicle":    np.random.choice(["Bike", "Scooter", "Bicycle"], N_DELIVERY_AGENTS,
                                   p=[0.65, 0.30, 0.05]),
    "rating":     np.round(np.random.uniform(3.0, 5.0, N_DELIVERY_AGENTS), 1),
    "joined_date": [
        (START_DATE - timedelta(days=random.randint(0, 730))).strftime("%Y-%m-%d")
        for _ in range(N_DELIVERY_AGENTS)
    ],
})
delivery_agents.to_csv(f"{OUTPUT_DIR}/delivery_agents.csv", index=False)

# ── 5. ORDERS ──────────────────────────────────────────────────────────────────
print("Generating orders …")
date_range_days = (END_DATE - START_DATE).days

def random_timestamp(base=START_DATE, days=date_range_days):
    """Bias orders toward lunch (12–14) and dinner (19–22)."""
    d = base + timedelta(days=random.randint(0, days))
    hour_weights = [1,1,1,1,1,1,2,3,4,5,6,8,10,10,8,6,5,6,8,10,10,8,5,2]
    hour = random.choices(range(24), weights=hour_weights)[0]
    minute = random.randint(0, 59)
    return d.replace(hour=hour, minute=minute)

order_timestamps = [random_timestamp() for _ in range(N_ORDERS)]

orders = pd.DataFrame({
    "order_id":       [f"ORD{str(i).zfill(7)}" for i in range(1, N_ORDERS + 1)],
    "customer_id":    np.random.choice(customers["customer_id"], N_ORDERS),
    "restaurant_id":  np.random.choice(rest_ids, N_ORDERS),
    "agent_id":       np.random.choice(delivery_agents["agent_id"], N_ORDERS),
    "order_timestamp": [ts.strftime("%Y-%m-%d %H:%M:%S") for ts in order_timestamps],
    "delivery_time_min": np.random.randint(20, 75, N_ORDERS),
    "distance_km":    np.round(np.random.uniform(0.5, 15.0, N_ORDERS), 2),
    "status":         np.random.choice(ORDER_STATUSES, N_ORDERS),
    "discount_pct":   np.random.choice([0, 5, 10, 15, 20, 25],
                                       N_ORDERS, p=[0.40, 0.15, 0.20, 0.10, 0.10, 0.05]),
    "platform":       np.random.choice(["App-iOS", "App-Android", "Web"],
                                       N_ORDERS, p=[0.35, 0.45, 0.20]),
})
orders.to_csv(f"{OUTPUT_DIR}/orders.csv", index=False)

# ── 6. ORDER ITEMS ─────────────────────────────────────────────────────────────
print("Generating order items …")
item_ids = menu_items["item_id"].tolist()
item_prices = dict(zip(menu_items["item_id"], menu_items["price"]))

order_item_rows = []
for _, row in orders.iterrows():
    n_items = random.choices([1, 2, 3, 4, 5], weights=[20, 35, 25, 15, 5])[0]
    selected = random.sample(item_ids, min(n_items, len(item_ids)))
    for item_id in selected:
        qty = random.choices([1, 2, 3], weights=[65, 25, 10])[0]
        order_item_rows.append({
            "order_item_id": None,   # will assign after
            "order_id":      row["order_id"],
            "item_id":       item_id,
            "quantity":      qty,
            "unit_price":    item_prices[item_id],
            "line_total":    round(qty * item_prices[item_id], 2),
        })

order_items = pd.DataFrame(order_item_rows)
order_items["order_item_id"] = [f"OI{str(i).zfill(8)}" for i in range(1, len(order_items) + 1)]
order_items.to_csv(f"{OUTPUT_DIR}/order_items.csv", index=False)

# ── 7. PAYMENTS ────────────────────────────────────────────────────────────────
print("Generating payments …")

# Aggregate order total from order_items
order_totals = order_items.groupby("order_id")["line_total"].sum().reset_index()
order_totals.columns = ["order_id", "gross_total"]

payments_df = orders[["order_id", "discount_pct", "status"]].merge(order_totals, on="order_id")
payments_df["discount_amount"] = np.round(
    payments_df["gross_total"] * payments_df["discount_pct"] / 100, 2
)
payments_df["delivery_fee"] = np.round(np.random.uniform(20, 60, len(payments_df)), 2)
payments_df["net_total"] = np.round(
    payments_df["gross_total"] - payments_df["discount_amount"] + payments_df["delivery_fee"], 2
)
# Cancelled orders → no payment
payments_df.loc[payments_df["status"] == "Cancelled", "net_total"] = 0.0

payments = pd.DataFrame({
    "payment_id":     [f"PAY{str(i).zfill(7)}" for i in range(1, len(payments_df) + 1)],
    "order_id":       payments_df["order_id"].values,
    "method":         np.random.choice(PAYMENT_METHODS, len(payments_df),
                                       p=[0.40, 0.20, 0.15, 0.15, 0.10]),
    "gross_total":    payments_df["gross_total"].values,
    "discount_amount": payments_df["discount_amount"].values,
    "delivery_fee":   payments_df["delivery_fee"].values,
    "net_total":      payments_df["net_total"].values,
    "status":         payments_df["status"].map(
                          {"Delivered": "Success", "Cancelled": "Refunded",
                           "Refunded": "Refunded"}).fillna("Success").values,
})
payments.to_csv(f"{OUTPUT_DIR}/payments.csv", index=False)

print(f"\n✅  All datasets written to {OUTPUT_DIR}")
print(f"   customers      : {len(customers):>7,} rows")
print(f"   restaurants    : {len(restaurants):>7,} rows")
print(f"   menu_items     : {len(menu_items):>7,} rows")
print(f"   delivery_agents: {len(delivery_agents):>7,} rows")
print(f"   orders         : {len(orders):>7,} rows")
print(f"   order_items    : {len(order_items):>7,} rows")
print(f"   payments       : {len(payments):>7,} rows")
