-- ============================================================
--  FoodFlow Analytics — Data Warehouse DDL
--  Database : PostgreSQL 15+
--  Schema   : Star Schema (OLAP-optimised)
-- ============================================================
--  Tables:
--    dim_date, dim_customer, dim_restaurant,
--    dim_menu_item, dim_delivery_agent,
--    fact_orders, fact_order_items
-- ============================================================

-- ── Drop in reverse-dependency order ─────────────────────────
DROP TABLE IF EXISTS fact_order_items CASCADE;
DROP TABLE IF EXISTS fact_orders       CASCADE;
DROP TABLE IF EXISTS dim_date          CASCADE;
DROP TABLE IF EXISTS dim_customer      CASCADE;
DROP TABLE IF EXISTS dim_restaurant    CASCADE;
DROP TABLE IF EXISTS dim_menu_item     CASCADE;
DROP TABLE IF EXISTS dim_delivery_agent CASCADE;

-- ============================================================
--  DIMENSION : dim_date
--  Grain : one row per calendar day (2023-01-01 → 2024-12-31)
-- ============================================================
CREATE TABLE dim_date (
    date_id        INTEGER      PRIMARY KEY,   -- YYYYMMDD surrogate key
    full_date      DATE         NOT NULL UNIQUE,
    day            SMALLINT     NOT NULL,
    month          SMALLINT     NOT NULL,
    month_name     VARCHAR(10)  NOT NULL,
    quarter        SMALLINT     NOT NULL,
    year           SMALLINT     NOT NULL,
    week           SMALLINT     NOT NULL,
    day_of_week    SMALLINT     NOT NULL,   -- 0=Monday … 6=Sunday
    day_name       VARCHAR(10)  NOT NULL,
    is_weekend     BOOLEAN      NOT NULL DEFAULT FALSE,
    is_holiday     BOOLEAN      NOT NULL DEFAULT FALSE,
    is_peak_season BOOLEAN      NOT NULL DEFAULT FALSE
);
COMMENT ON TABLE  dim_date IS 'Calendar dimension — supports time-series and seasonal analysis';
COMMENT ON COLUMN dim_date.date_id IS 'Surrogate key in YYYYMMDD integer format for fast range scans';

-- ============================================================
--  DIMENSION : dim_customer
--  Grain : one row per unique registered customer
-- ============================================================
CREATE TABLE dim_customer (
    customer_id       VARCHAR(10)  PRIMARY KEY,
    full_name         VARCHAR(100) NOT NULL,
    email             VARCHAR(150) NOT NULL,
    phone             VARCHAR(20),
    city              VARCHAR(50)  NOT NULL,
    age_group         VARCHAR(10),
    gender            VARCHAR(10),
    is_premium        BOOLEAN      NOT NULL DEFAULT FALSE,
    registration_date DATE         NOT NULL,
    tenure_days       INTEGER,        -- computed: days since registration
    customer_segment  VARCHAR(20)     -- Premium-Loyal | Premium-New | Regular-Loyal | Regular-New
);
COMMENT ON TABLE dim_customer IS 'SCD Type 1 — overwrites on change (suitable for academic scope)';

-- ============================================================
--  DIMENSION : dim_restaurant
--  Grain : one row per partner restaurant
-- ============================================================
CREATE TABLE dim_restaurant (
    restaurant_id    VARCHAR(8)   PRIMARY KEY,
    name             VARCHAR(150) NOT NULL,
    city             VARCHAR(50)  NOT NULL,
    cuisine_type     VARCHAR(50),
    rating           NUMERIC(3,1),
    rating_band      VARCHAR(15),   -- Poor | Average | Good | Excellent
    total_reviews    INTEGER,
    avg_prep_time_min SMALLINT,
    is_veg_only      BOOLEAN      NOT NULL DEFAULT FALSE,
    onboarded_date   DATE
);

-- ============================================================
--  DIMENSION : dim_menu_item
--  Grain : one row per menu offering (belongs to a restaurant)
-- ============================================================
CREATE TABLE dim_menu_item (
    item_id       VARCHAR(9)   PRIMARY KEY,
    restaurant_id VARCHAR(8)   NOT NULL REFERENCES dim_restaurant(restaurant_id),
    item_name     VARCHAR(200) NOT NULL,
    category      VARCHAR(50),
    price         NUMERIC(8,2) NOT NULL,
    price_band    VARCHAR(15),   -- Budget | Affordable | Mid-Range | Premium
    is_available  BOOLEAN      NOT NULL DEFAULT TRUE,
    is_veg        BOOLEAN      NOT NULL DEFAULT TRUE,
    calories      SMALLINT
);

-- ============================================================
--  DIMENSION : dim_delivery_agent
--  Grain : one row per registered delivery partner
-- ============================================================
CREATE TABLE dim_delivery_agent (
    agent_id         VARCHAR(7)  PRIMARY KEY,
    name             VARCHAR(100) NOT NULL,
    city             VARCHAR(50)  NOT NULL,
    vehicle          VARCHAR(20),
    rating           NUMERIC(3,1),
    performance_tier VARCHAR(20),   -- Below Average | Average | Good | Top Performer
    experience_days  INTEGER,
    joined_date      DATE
);

-- ============================================================
--  FACT TABLE : fact_orders
--  Grain : one row per order
-- ============================================================
CREATE TABLE fact_orders (
    order_id          VARCHAR(11)  PRIMARY KEY,
    -- Foreign keys to dimensions
    customer_id       VARCHAR(10)  NOT NULL REFERENCES dim_customer(customer_id),
    restaurant_id     VARCHAR(8)   NOT NULL REFERENCES dim_restaurant(restaurant_id),
    agent_id          VARCHAR(7)   NOT NULL REFERENCES dim_delivery_agent(agent_id),
    date_id           INTEGER      NOT NULL REFERENCES dim_date(date_id),
    -- Degenerate dimensions (no separate table warranted)
    order_timestamp   TIMESTAMP    NOT NULL,
    order_hour        SMALLINT,
    time_of_day       VARCHAR(15),     -- Night | Morning | Lunch | Afternoon | Dinner | Late Night
    platform          VARCHAR(15),     -- App-iOS | App-Android | Web
    status            VARCHAR(15),     -- Delivered | Cancelled | Refunded
    -- Flags
    is_delivered      SMALLINT     NOT NULL DEFAULT 0,  -- 1/0 for easy SUM
    is_cancelled      SMALLINT     NOT NULL DEFAULT 0,
    -- Measures
    delivery_time_min SMALLINT,
    distance_km       NUMERIC(5,2),
    discount_pct      SMALLINT     DEFAULT 0,
    gross_total       NUMERIC(10,2) NOT NULL DEFAULT 0,
    discount_amount   NUMERIC(10,2) NOT NULL DEFAULT 0,
    delivery_fee      NUMERIC(7,2)  NOT NULL DEFAULT 0,
    net_total         NUMERIC(10,2) NOT NULL DEFAULT 0,
    method            VARCHAR(25)       -- Payment method (degenerate dim)
);
COMMENT ON TABLE  fact_orders IS 'Central fact table — order-level grain; measures in INR';
COMMENT ON COLUMN fact_orders.net_total IS 'gross_total - discount_amount + delivery_fee';

-- ============================================================
--  FACT TABLE : fact_order_items
--  Grain : one row per line item within an order
-- ============================================================
CREATE TABLE fact_order_items (
    order_item_id  VARCHAR(11)  PRIMARY KEY,
    order_id       VARCHAR(11)  NOT NULL REFERENCES fact_orders(order_id),
    item_id        VARCHAR(9)   NOT NULL REFERENCES dim_menu_item(item_id),
    customer_id    VARCHAR(10)  NOT NULL REFERENCES dim_customer(customer_id),
    date_id        INTEGER      NOT NULL REFERENCES dim_date(date_id),
    -- Measures
    quantity       SMALLINT     NOT NULL DEFAULT 1,
    unit_price     NUMERIC(8,2) NOT NULL,
    revenue        NUMERIC(10,2) NOT NULL   -- quantity × unit_price
);
COMMENT ON TABLE fact_order_items IS 'Line-item grain fact; enables product-level analytics';

-- ============================================================
--  PERFORMANCE INDEXES
-- ============================================================
CREATE INDEX idx_fo_customer    ON fact_orders(customer_id);
CREATE INDEX idx_fo_restaurant  ON fact_orders(restaurant_id);
CREATE INDEX idx_fo_agent       ON fact_orders(agent_id);
CREATE INDEX idx_fo_date        ON fact_orders(date_id);
CREATE INDEX idx_fo_status      ON fact_orders(status);
CREATE INDEX idx_fo_date_status ON fact_orders(date_id, status);

CREATE INDEX idx_foi_order      ON fact_order_items(order_id);
CREATE INDEX idx_foi_item       ON fact_order_items(item_id);
CREATE INDEX idx_foi_date       ON fact_order_items(date_id);

CREATE INDEX idx_dd_yearmonth   ON dim_date(year, month);
CREATE INDEX idx_dr_city        ON dim_restaurant(city);
CREATE INDEX idx_dc_city_seg    ON dim_customer(city, customer_segment);

-- ============================================================
--  AGGREGATE SUMMARY TABLE (Materialised for BI performance)
-- ============================================================
CREATE TABLE agg_monthly_revenue (
    year             SMALLINT,
    month            SMALLINT,
    month_name       VARCHAR(10),
    city             VARCHAR(50),
    cuisine_type     VARCHAR(50),
    total_orders     INTEGER,
    delivered_orders INTEGER,
    cancelled_orders INTEGER,
    gross_revenue    NUMERIC(15,2),
    net_revenue      NUMERIC(15,2),
    avg_order_value  NUMERIC(10,2),
    avg_delivery_min NUMERIC(6,2),
    PRIMARY KEY (year, month, city, cuisine_type)
);
COMMENT ON TABLE agg_monthly_revenue IS
  'Pre-aggregated summary — refresh after each ETL run for BI tool performance';
