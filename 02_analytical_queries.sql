-- ============================================================
--  FoodFlow Analytics — Analytical Queries (FIXED)
-- ============================================================

-- ── CREATE AGG TABLE (needed for Q11) ─────────────────────────
CREATE TABLE IF NOT EXISTS agg_monthly_revenue (
    year INT,
    month INT,
    month_name TEXT,
    city TEXT,
    cuisine_type TEXT,
    total_orders INT,
    delivered_orders INT,
    cancelled_orders INT,
    gross_revenue NUMERIC,
    net_revenue NUMERIC,
    avg_order_value NUMERIC,
    avg_delivery_min NUMERIC,
    PRIMARY KEY (year, month, city, cuisine_type)
);

-- ── Q1 ─ Monthly Revenue Trend ────────────────────────────────
WITH monthly AS (
    SELECT
        d.year,
        d.month,
        d.month_name,
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
    total_orders,
    delivered_orders,
    ROUND((net_revenue / NULLIF(delivered_orders, 0))::numeric, 2) AS avg_order_value,
    mom_growth_pct
FROM with_growth
ORDER BY year, month;

-- ── Q2 ─ Top Restaurants ─────────────────────────────────────
SELECT
    r.restaurant_id,
    r.name AS restaurant_name,
    r.city,
    r.cuisine_type,
    r.rating,
    COUNT(*) AS total_orders,
    ROUND(SUM(fo.net_total)::numeric, 2) AS net_revenue,
    ROUND(AVG(fo.net_total)::numeric, 2) AS avg_order_value,
    ROUND(AVG(fo.delivery_time_min)::numeric, 1) AS avg_delivery_min,
    ROUND((100.0 * SUM(fo.is_delivered) / COUNT(*))::numeric, 2) AS delivery_success_rate
FROM fact_orders fo
JOIN dim_restaurant r ON fo.restaurant_id = r.restaurant_id
GROUP BY r.restaurant_id, r.name, r.city, r.cuisine_type, r.rating
ORDER BY net_revenue DESC
LIMIT 10;

-- ── Q3 ─ CLV ────────────────────────────────────────────────
WITH clv AS (
    SELECT
        c.customer_id,
        c.full_name,
        c.city,
        c.customer_segment,
        COUNT(fo.order_id) AS total_orders,
        SUM(fo.net_total) AS lifetime_value,
        ROUND(AVG(fo.net_total)::numeric, 2) AS avg_order_value,
        MAX(fo.order_timestamp::DATE) AS last_order_date,
        CURRENT_DATE - MAX(fo.order_timestamp::DATE) AS days_since_last_order
    FROM dim_customer c
    LEFT JOIN fact_orders fo 
        ON c.customer_id = fo.customer_id
       AND LOWER(fo.status) = 'delivered'
    GROUP BY c.customer_id, c.full_name, c.city, c.customer_segment
),
ranked AS (
    SELECT *,
        NTILE(4) OVER (ORDER BY lifetime_value DESC) AS clv_quartile
    FROM clv
    WHERE total_orders > 0
)
SELECT *,
    CASE clv_quartile
        WHEN 1 THEN 'Champion'
        WHEN 2 THEN 'Loyal'
        WHEN 3 THEN 'At-Risk'
        WHEN 4 THEN 'Dormant'
    END AS clv_tier
FROM ranked
ORDER BY lifetime_value DESC
LIMIT 50;

-- ── Q4 ─ Top Items ───────────────────────────────────────────
SELECT
    m.item_id,
    m.item_name,
    m.category,
    r.cuisine_type,
    SUM(foi.quantity) AS total_units_sold,
    COUNT(DISTINCT foi.order_id) AS orders,
    ROUND(SUM(foi.revenue)::numeric, 2) AS total_revenue,
    ROUND(AVG(foi.unit_price)::numeric, 2) AS avg_price
FROM fact_order_items foi
JOIN dim_menu_item m ON foi.item_id = m.item_id
JOIN dim_restaurant r ON m.restaurant_id = r.restaurant_id
GROUP BY m.item_id, m.item_name, m.category, r.cuisine_type
ORDER BY total_revenue DESC
LIMIT 10;

-- ── Q5 ─ Cancellation ───────────────────────────────────────
SELECT
    r.city,
    r.cuisine_type,
    COUNT(*) AS total_orders,
    SUM(fo.is_cancelled) AS cancelled_orders,
    ROUND((100.0 * SUM(fo.is_cancelled) / COUNT(*))::numeric, 2) AS cancellation_rate,
    ROUND(AVG(fo.delivery_time_min)::numeric, 1) AS avg_delivery
FROM fact_orders fo
JOIN dim_restaurant r ON fo.restaurant_id = r.restaurant_id
GROUP BY r.city, r.cuisine_type
HAVING COUNT(*) >= 100
ORDER BY cancellation_rate DESC;

-- ── Q6 ─ Hourly Demand ──────────────────────────────────────
SELECT
    d.day_name,
    fo.order_hour,
    COUNT(*) AS orders,
    ROUND(SUM(fo.net_total)::numeric, 2) AS revenue
FROM fact_orders fo
JOIN dim_date d ON fo.date_id = d.date_id
WHERE LOWER(fo.status) = 'delivered'
GROUP BY d.day_name, fo.order_hour
ORDER BY d.day_name, fo.order_hour;

-- ── Q7 ─ Agent Performance ──────────────────────────────────
SELECT
    a.agent_id,
    a.name,
    COUNT(*) AS deliveries,
    ROUND(AVG(fo.delivery_time_min)::numeric, 1) AS avg_time,
    ROUND(SUM(fo.net_total)::numeric, 2) AS total_value
FROM fact_orders fo
JOIN dim_delivery_agent a ON fo.agent_id = a.agent_id
GROUP BY a.agent_id, a.name
ORDER BY deliveries DESC;

-- ── Q8 ─ RFM Segmentation (Complete) ────────────────────────
-- Recency, Frequency, Monetary value with NTILE scoring
-- and actionable customer segment labels
WITH base_rfm AS (
    SELECT
        c.customer_id,
        c.full_name,
        c.city,
        c.customer_segment,
        COUNT(*) AS frequency,
        SUM(fo.net_total) AS monetary,
        CURRENT_DATE - MAX(fo.order_timestamp::DATE) AS recency_days,
        AVG(fo.net_total) AS avg_order_value
    FROM dim_customer c
    JOIN fact_orders fo ON c.customer_id = fo.customer_id
    WHERE LOWER(fo.status) = 'delivered'
    GROUP BY c.customer_id, c.full_name, c.city, c.customer_segment
),
scored AS (
    SELECT
        *,
        NTILE(5) OVER (ORDER BY recency_days DESC)  AS r_score,  -- lower recency = better
        NTILE(5) OVER (ORDER BY frequency ASC)       AS f_score,  -- higher freq = better
        NTILE(5) OVER (ORDER BY monetary ASC)        AS m_score   -- higher monetary = better
    FROM base_rfm
),
segmented AS (
    SELECT
        *,
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
            WHEN r_score >= 3 AND f_score <= 2 AND m_score >= 3 THEN 'Can\'t Lose Them'
            ELSE 'Others'
        END AS rfm_segment
    FROM scored
)
SELECT
    rfm_segment,
    COUNT(*) AS customer_count,
    ROUND(AVG(recency_days)::numeric, 1) AS avg_recency_days,
    ROUND(AVG(frequency)::numeric, 1) AS avg_frequency,
    ROUND(AVG(monetary)::numeric, 2) AS avg_monetary,
    ROUND(AVG(rfm_total)::numeric, 1) AS avg_rfm_score,
    MIN(rfm_total) AS min_rfm_score,
    MAX(rfm_total) AS max_rfm_score
FROM segmented
GROUP BY rfm_segment
ORDER BY avg_rfm_score DESC;

-- ── Q9 ─ YoY ────────────────────────────────────────────────
SELECT
    d.year,
    ROUND(SUM(fo.net_total)::numeric, 2) AS revenue
FROM fact_orders fo
JOIN dim_date d ON fo.date_id = d.date_id
WHERE LOWER(fo.status) = 'delivered'
GROUP BY d.year;

-- ── Q10 ─ Platform ──────────────────────────────────────────
SELECT
    platform,
    COUNT(*) AS orders,
    ROUND(SUM(net_total)::numeric, 2) AS revenue
FROM fact_orders
WHERE LOWER(status) = 'delivered'
GROUP BY platform;

-- ── Q11 ─ Aggregate ─────────────────────────────────────────
INSERT INTO agg_monthly_revenue
SELECT
    d.year,
    d.month,
    d.month_name,
    r.city,
    r.cuisine_type,
    COUNT(*) AS total_orders,
    COUNT(*) FILTER (WHERE fo.is_delivered = 1),
    COUNT(*) FILTER (WHERE fo.is_cancelled = 1),
    ROUND(SUM(fo.gross_total)::numeric, 2),
    ROUND(SUM(fo.net_total)::numeric, 2),
    ROUND(AVG(fo.net_total)::numeric, 2),
    ROUND(AVG(fo.delivery_time_min)::numeric, 2)
FROM fact_orders fo
JOIN dim_date d ON fo.date_id = d.date_id
JOIN dim_restaurant r ON fo.restaurant_id = r.restaurant_id
GROUP BY d.year, d.month, d.month_name, r.city, r.cuisine_type
ON CONFLICT (year, month, city, cuisine_type)
DO UPDATE SET net_revenue = EXCLUDED.net_revenue;
