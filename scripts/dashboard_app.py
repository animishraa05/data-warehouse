"""
FoodFlow Analytics — Interactive Dashboard
============================================
Streamlit app that connects to the PostgreSQL data warehouse
and visualises all 11 analytical queries as interactive charts.

Run:
    pip install streamlit plotly
    streamlit run scripts/dashboard_app.py
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# ── PAGE CONFIG ──────────────────────────────────────────────
st.set_page_config(
    page_title="FoodFlow Analytics",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── NORD THEME CSS ──────────────────────────────────────────
st.markdown("""
<style>
    /* Nord Palette Reference */
    /* Polar Night:  nord0=#2e3440 nord1=#3b4252 nord2=#434c5e nord3=#4c566a */
    /* Snow Storm:   nord4=#d8dee9 nord5=#e5e9f0 nord6=#eceff4 */
    /* Frost:        nord7=#8fbcbb nord8=#88c0d0 nord9=#81a1c1 nord10=#5e81ac */
    /* Aurora:       nord11=#bf616a nord12=#d08770 nord13=#ebcb8b nord14=#a3be8c nord15=#b48ead */

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Main content area */
    .main .block-container {
        background-color: #eceff4;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    /* Sidebar - dark polar night */
    section[data-testid="stSidebar"] {
        background-color: #2e3440;
        border-right: 1px solid #434c5e;
    }
    section[data-testid="stSidebar"] * {
        color: #d8dee9 !important;
    }
    section[data-testid="stSidebar"] h1 {
        color: #e5e9f0 !important;
        font-size: 1.25rem;
        font-weight: 600;
    }
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div {
        color: #d8dee9 !important;
    }
    section[data-testid="stSidebar"] .stRadio > label {
        color: #d8dee9 !important;
        font-size: 0.875rem;
    }
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
        color: #d8dee9 !important;
    }
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
        color: #88c0d0 !important;
        background-color: #3b4252;
    }
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-baseweb="radio"][aria-checked="true"] {
        color: #88c0d0 !important;
        font-weight: 500;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #4c566a;
    }

    /* Title */
    h1 {
        color: #2e3440 !important;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }

    /* Subheading - nord10 frost blue */
    h2 {
        color: #5e81ac !important;
        font-size: 1.375rem;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 0.5rem;
        padding-bottom: 0.25rem;
        border-bottom: 2px solid #88c0d0;
    }

    /* Sub-subheading - nord9 */
    h3 {
        color: #81a1c1 !important;
        font-size: 1.125rem;
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }

    /* Horizontal rules */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #4c566a, transparent);
        margin: 1.5rem 0;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background-color: #e5e9f0;
        border: 1px solid #d8dee9;
        border-radius: 6px;
        padding: 1rem;
    }
    div[data-testid="stMetric"] p {
        color: #4c566a !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #2e3440 !important;
        font-size: 1.75rem !important;
        font-weight: 700;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: #5e81ac !important;
    }

    /* Markdown text */
    .stMarkdown p {
        color: #3b4252;
        font-size: 0.9rem;
        line-height: 1.6;
    }
    .stMarkdown strong {
        color: #2e3440;
        font-weight: 600;
    }

    /* Dataframe */
    .stDataFrame {
        border: 1px solid #d8dee9;
        border-radius: 6px;
    }

    /* Sidebar captions */
    [data-testid="stCaption"] {
        color: #4c566a !important;
        font-size: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

# ── DB CONNECTION ────────────────────────────────────────────
@st.cache_resource
def get_engine():
    url = (
        f"postgresql+psycopg2://{os.getenv('DB_USER', 'dw_user')}:"
        f"{os.getenv('DB_PASS', 'secret')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'foodflow_dw')}"
    )
    return create_engine(url)


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(sql, conn)


# ── SIDEBAR ──────────────────────────────────────────────────
st.sidebar.markdown("### FoodFlow Analytics")
st.sidebar.markdown("---")

nav = st.sidebar.radio(
    "Navigate",
    ["Overview", "Revenue", "Restaurants", "Customers",
     "Menu Items", "Cancellations", "Demand Patterns",
     "Delivery Agents", "RFM Segmentation", "ML Forecast"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("<p style='color:#4c566a;font-size:0.75rem;margin:0;'>Data Warehouse: PostgreSQL 15</p>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='color:#4c566a;font-size:0.75rem;margin:0.25rem 0 0 0;'>ETL: Airflow Daily Pipeline</p>", unsafe_allow_html=True)

# ── TOP METRICS (always visible) ────────────────────────────
def show_kpi_strip():
    """Show key metrics at the top of every page."""
    kpis = query("""
        SELECT
            COUNT(*) AS total_orders,
            SUM(CASE WHEN is_delivered = 1 THEN 1 ELSE 0 END) AS delivered,
            SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) AS cancelled,
            ROUND(SUM(CASE WHEN is_delivered = 1 THEN net_total ELSE 0 END)::numeric, 2) AS net_revenue,
            ROUND(AVG(CASE WHEN is_delivered = 1 THEN net_total ELSE NULL END)::numeric, 2) AS avg_order_value,
            ROUND(AVG(CASE WHEN is_delivered = 1 THEN delivery_time_min ELSE NULL END)::numeric, 1) AS avg_delivery_min,
            COUNT(DISTINCT customer_id) AS unique_customers,
            COUNT(DISTINCT restaurant_id) AS unique_restaurants
        FROM fact_orders
    """)

    row = kpis.iloc[0]
    cols = st.columns(5)

    cols[0].metric("Total Orders", f"{row['total_orders']:,}")
    cols[1].metric("Net Revenue", f"₹{row['net_revenue']:,.0f}")
    cols[2].metric("Avg Order Value", f"₹{row['avg_order_value']:,.0f}")
    cols[3].metric("Avg Delivery", f"{row['avg_delivery_min']} min")
    cols[4].metric("Delivery Rate",
                   f"{row['delivered'] / row['total_orders'] * 100:.1f}%"
                   if row['total_orders'] > 0 else "N/A")


# ── PAGE: OVERVIEW ───────────────────────────────────────────
def page_overview():
    st.title("FoodFlow Analytics Dashboard")
    st.markdown("""
    **About This Dashboard**: This dashboard provides a comprehensive view of FoodFlow's delivery operations, 
    tracking over 80,000 orders across 200 restaurants and 5,000 customers. It combines data from 8 dimension 
    tables and 2 fact tables to reveal patterns in revenue, customer behavior, and operational efficiency.
    
    **What to Look For**: Start with the order status distribution to understand fulfillment rates, then examine 
    the monthly revenue trend to identify growth patterns. The platform split reveals which ordering channels 
    drive the most business.
    """)
    show_kpi_strip()

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Order Status Distribution")
        st.markdown("""
        **What This Shows**: Breakdown of all orders by their final status — whether they were successfully 
        delivered, cancelled by the customer or restaurant, or refunded. This is the most fundamental metric 
        for understanding operational efficiency.
        
        **Key Insight**: A high delivery rate (>85%) indicates healthy operations. Look at the cancelled 
        percentage — if it's above 10%, there may be systemic issues in those restaurants or customer segments.
        """)
        status_data = query("""
            SELECT status, COUNT(*) AS orders
            FROM fact_orders GROUP BY status
        """)
        fig = px.pie(
            status_data, values="orders", names="status",
            color_discrete_sequence=["#88c0d0", "#a3be8c", "#ebcb8b", "#bf616a", "#81a1c1"],
            hole=0.4,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Platform Split")
        st.markdown("""
        **What This Shows**: Distribution of orders across different ordering platforms (web, iOS, Android) 
        along with the revenue each platform generates. This helps identify which channels are most valuable 
        for customer acquisition and retention.
        
        **Key Insight**: If one platform dominates, consider whether you're under-investing in others. A 
        healthy multi-platform strategy reduces dependency risk and captures different user demographics.
        """)
        platform_data = query("""
            SELECT platform, COUNT(*) AS orders,
                   ROUND(SUM(net_total)::numeric, 2) AS revenue
            FROM fact_orders WHERE is_delivered = 1
            GROUP BY platform
        """)
        fig = px.bar(
            platform_data, x="platform", y="orders",
            color="platform", text_auto=",",
            color_discrete_sequence=["#81a1c1", "#88c0d0", "#8fbcbb"],
        )
        fig.update_layout(showlegend=False, yaxis_title="Orders")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly Revenue Trend")
    st.markdown("""
    **What This Shows**: Total revenue from delivered orders over time (line chart, left axis) overlaid with 
    the number of orders per month (bar chart, right axis). The dual-axis view lets you see whether revenue 
    growth is driven by more orders or higher average order values.
    
    **Key Insight**: If revenue increases but order count stays flat, growth is coming from larger orders 
    (possibly good). If both rise, you have healthy volume-driven growth. Watch for seasonal dips — they 
    often correlate with holidays or economic events.
    """)
    revenue = query("""
        SELECT
            d.year, d.month, d.month_name,
            ROUND(SUM(fo.net_total)::numeric, 2) AS net_revenue,
            COUNT(*) AS orders
        FROM fact_orders fo
        JOIN dim_date d ON fo.date_id = d.date_id
        WHERE fo.is_delivered = 1
        GROUP BY d.year, d.month, d.month_name
        ORDER BY d.year, d.month
    """)
    revenue["date_str"] = revenue["year"].astype(str) + "-" + revenue["month"].astype(str).str.zfill(2)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=revenue["date_str"], y=revenue["net_revenue"],
        mode="lines+markers", name="Revenue",
        line=dict(color="#5e81ac", width=2.5),
        fill="tozeroy", fillcolor="rgba(94,129,172,0.08)",
    ))
    fig.add_trace(go.Bar(
        x=revenue["date_str"], y=revenue["orders"],
        name="Orders", yaxis="y2",
        marker_color="rgba(136,192,208,0.45)",
    ))
    fig.update_layout(
        yaxis_title="Revenue (₹)",
        yaxis2=dict(title="Orders", overlaying="y", side="right"),
        xaxis_title="Month",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Data Model")
    st.markdown("""
    | **Dimension** | **Rows** | **Fact** | **Rows** |
    |---|---|---|---|
    | dim_date | ~731 | fact_orders | 80,000 |
    | dim_customer | 5,000 | fact_order_items | ~200K |
    | dim_restaurant | 200 | agg_monthly_revenue | ~480 |
    | dim_menu_item | 1,500 | ml_order_forecast | 30 |
    | dim_delivery_agent | 300 | ml_model_metrics | per run |
    """)


# ── PAGE: REVENUE ────────────────────────────────────────────
def page_revenue():
    st.title("Revenue Analytics")
    st.markdown("""
    **About This Analysis**: Revenue is the most critical business metric. This page breaks down monthly 
    revenue trends and calculates month-over-month (MoM) growth rates to identify acceleration or deceleration 
    patterns.
    
    **What to Look For**: The revenue line shows your top-line trajectory. The MoM growth bar chart reveals 
    whether growth is speeding up or slowing down. Green bars = positive growth, red bars = contraction. 
    Consistent positive MoM growth indicates a healthy, scaling business.
    """)
    show_kpi_strip()

    st.subheader("Monthly Revenue Trend with MoM Growth")
    st.markdown("""
    **Left Chart**: Monthly revenue over the entire dataset period. The line shows absolute revenue, helping 
    you identify the overall trend direction and any seasonal patterns.
    
    **Right Chart**: Month-over-month growth rate as a percentage. This is more sensitive than absolute revenue 
    for spotting turning points. A sequence of declining green bars often precedes a revenue dip.
    """)
    revenue = query("""
        WITH monthly AS (
            SELECT
                d.year, d.month, d.month_name,
                ROUND(SUM(fo.net_total)::numeric, 2) AS net_revenue,
                COUNT(*) AS total_orders,
                COUNT(*) FILTER (WHERE fo.is_delivered = 1) AS delivered_orders
            FROM fact_orders fo
            JOIN dim_date d ON fo.date_id = d.date_id
            WHERE fo.status != 'Cancelled'
            GROUP BY d.year, d.month, d.month_name
        )
        SELECT *,
            LAG(net_revenue) OVER (ORDER BY year, month) AS prev_revenue,
            ROUND(
                (100.0 * (net_revenue - LAG(net_revenue) OVER (ORDER BY year, month))
                / NULLIF(LAG(net_revenue) OVER (ORDER BY year, month), 0))::numeric, 2
            ) AS mom_growth_pct
        FROM monthly
        ORDER BY year, month
    """)
    revenue["date_str"] = revenue["year"].astype(str) + "-" + revenue["month"].astype(str).str.zfill(2)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.line(
            revenue, x="date_str", y="net_revenue",
            markers=True, labels={"net_revenue": "Revenue (₹)", "date_str": "Month"},
        )
        fig.update_traces(line_color="#a3be8c", line_width=2.5, marker_size=6)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            revenue.dropna(subset=["mom_growth_pct"]),
            x="date_str", y="mom_growth_pct",
            labels={"mom_growth_pct": "MoM Growth (%)", "date_str": "Month"},
            color="mom_growth_pct",
            color_continuous_scale=[[0, "#bf616a"], [0.5, "#d8dee9"], [1, "#a3be8c"]],
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(revenue, use_container_width=True, hide_index=True)


# ── PAGE: RESTAURANTS ────────────────────────────────────────
def page_restaurants():
    st.title("Restaurant Analytics")
    st.markdown("""
    **About This Analysis**: Restaurants are the core supply-side of the platform. This page ranks restaurants 
    by revenue and provides operational context — delivery times, order volumes, and success rates.
    
    **What to Look For**: The top 10 restaurants by revenue may not be the most efficient. Compare delivery 
    success rates and average order values — a restaurant with fewer orders but higher values and faster 
    delivery is often more profitable than a high-volume, low-margin one.
    """)
    show_kpi_strip()

    st.subheader("Top 10 Restaurants by Revenue")
    st.markdown("""
    **What This Shows**: The highest-grossing restaurants ranked by total revenue. Hover over each bar to 
    see the restaurant's rating, delivery success rate, and total order count. City coloring helps you spot 
    geographic concentration.
    
    **Key Insight**: If one city dominates the top 10, your business may be geographically concentrated — 
    which is a risk if that market becomes competitive. Look for restaurants with high ratings AND high 
    delivery success rates — those are your sustainable performers.
    """)
    restaurants = query("""
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
        LIMIT 10
    """)

    fig = px.bar(
        restaurants,
        x="restaurant_name", y="net_revenue",
        color="city", text_auto=".2s",
        hover_data=["rating", "delivery_success_rate", "total_orders"],
        labels={"net_revenue": "Revenue (₹)", "restaurant_name": "Restaurant"},
        color_discrete_sequence=["#88c0d0", "#81a1c1", "#5e81ac", "#a3be8c", "#ebcb8b", "#d08770", "#bf616a", "#b48ead", "#8fbcbb"],
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(restaurants, use_container_width=True, hide_index=True)


# ── PAGE: CUSTOMERS ──────────────────────────────────────────
def page_customers():
    st.title("Customer Analytics")
    st.markdown("""
    **About This Analysis**: Understanding customer behavior is essential for retention and growth. This page 
    shows customer segment distribution and Customer Lifetime Value (CLV) — the total revenue a customer 
    generates over their relationship with the platform.
    
    **What to Look For**: The segment pie chart reveals your customer base composition. A healthy platform 
    has a mix of new customers (growth), loyal customers (stability), and champions (advocates). The CLV 
    chart shows who your most valuable customers are — and what segment they belong to.
    """)
    show_kpi_strip()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Customer Segments")
        st.markdown("""
        **What This Shows**: Distribution of customers across predefined segments based on behavior patterns 
        — frequency of orders, recency of last order, and total spending. Each segment requires a different 
        marketing strategy.
        
        **Key Insight**: If "Lost" or "At-Risk" segments are growing, you need re-engagement campaigns. If 
        "New Customers" is the largest segment, you're acquiring but not retaining — which is unsustainable.
        """)
        segments = query("""
            SELECT customer_segment, COUNT(*) AS cnt
            FROM dim_customer
            GROUP BY customer_segment
            ORDER BY cnt DESC
        """)
        fig = px.pie(
            segments, values="cnt", names="customer_segment",
            color_discrete_sequence=["#88c0d0", "#81a1c1", "#5e81ac", "#a3be8c", "#ebcb8b", "#d08770", "#bf616a", "#b48ead", "#8fbcbb"],
            hole=0.4,
        )
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Customer Lifetime Value (Top 20)")
        st.markdown("""
        **What This Shows**: The 20 customers who have generated the most revenue over their lifetime on the 
        platform. Color-coded by segment to reveal which types of customers are most valuable.
        
        **Key Insight**: Champions and Loyal Customers should dominate the top 20. If you see mostly New 
        Customers with high CLV, they may be one-time big spenders — retention strategy differs significantly. 
        Track whether these top customers are growing or shrinking over time.
        """)
        clv = query("""
            SELECT
                c.customer_id, c.full_name, c.city, c.customer_segment,
                COUNT(fo.order_id) AS total_orders,
                ROUND(SUM(fo.net_total)::numeric, 2) AS lifetime_value,
                ROUND(AVG(fo.net_total)::numeric, 2) AS avg_order_value
            FROM dim_customer c
            JOIN fact_orders fo ON c.customer_id = fo.customer_id
            WHERE LOWER(fo.status) = 'delivered'
            GROUP BY c.customer_id, c.full_name, c.city, c.customer_segment
            ORDER BY lifetime_value DESC
            LIMIT 20
        """)
        fig = px.bar(
            clv, x="full_name", y="lifetime_value",
            color="customer_segment", text_auto=".2s",
            hover_data=["total_orders", "avg_order_value"],
            labels={"lifetime_value": "Lifetime Value (₹)", "full_name": "Customer"},
            color_discrete_sequence=["#88c0d0", "#81a1c1", "#5e81ac", "#a3be8c", "#ebcb8b", "#d08770", "#bf616a", "#b48ead"],
        )
        fig.update_layout(xaxis_tickangle=-45, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("CLV Distribution")
    st.markdown("""
    **Data Table**: Full breakdown of the top 20 customers by lifetime value. Use this to identify individual 
    high-value customers and understand their ordering patterns — total orders, average order value, and 
    segment classification.
    """)
    st.dataframe(clv, use_container_width=True, hide_index=True)


# ── PAGE: MENU ITEMS ─────────────────────────────────────────
def page_menu_items():
    st.title("Menu Item Analytics")
    st.markdown("""
    **About This Analysis**: Individual menu items drive customer choice and restaurant differentiation. This 
    page identifies the top-performing items by revenue, revealing which categories and cuisines resonate 
    most with customers.
    
    **What to Look For**: Top items by revenue may be expensive but low-volume, or cheap but high-volume. 
    Look at units sold alongside revenue — an item with moderate revenue but very high units sold is a 
    volume driver that could be used in promotions.
    """)
    show_kpi_strip()

    st.subheader("Top 10 Menu Items by Revenue")
    st.markdown("""
    **What This Shows**: The 10 menu items that generate the most total revenue, colored by food category. 
    Hover data reveals total units sold, number of orders containing this item, and average price.
    
    **Key Insight**: Category diversity in the top 10 indicates broad appeal across customer preferences. If 
    one category dominates, you may be over-reliant on a specific type of customer or occasion. Cuisine type 
    coloring helps identify which culinary traditions perform best on the platform.
    """)
    items = query("""
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
        LIMIT 10
    """)

    fig = px.bar(
        items,
        x="item_name", y="total_revenue",
        color="category", text_auto=".2s",
        hover_data=["total_units_sold", "orders", "avg_price"],
        labels={"total_revenue": "Revenue (₹)", "item_name": "Item"},
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(items, use_container_width=True, hide_index=True)


# ── PAGE: CANCELLATIONS ──────────────────────────────────────
def page_cancellations():
    st.title("Cancellation Analysis")
    st.markdown("""
    **About This Analysis**: Cancellations represent failed transactions — lost revenue for restaurants, 
    frustrated customers, and wasted delivery capacity. Understanding where and why cancellations happen is 
    critical for operational improvement.
    
    **What to Look For**: High cancellation rates in specific cities or cuisines indicate systemic problems — 
    perhaps delivery agent shortages, restaurant preparation issues, or customer expectation mismatches. The 
    scatter plot reveals whether high-volume areas have proportionally high or low cancellation rates.
    """)
    show_kpi_strip()

    st.subheader("Cancellation Rate by City & Cuisine")
    st.markdown("""
    **Left Chart**: Top 15 city-cuisine combinations ranked by cancellation rate. The bar height shows the 
    percentage of orders that were cancelled. Color indicates cuisine type, helping you spot cuisine-specific 
    issues.
    
    **Right Chart**: Scatter plot of total orders vs cancellation rate. Bubble size = number of cancelled 
    orders. Points in the upper-right (high volume, high cancellation rate) are your most critical problem 
    areas — they affect the most customers. Points in the lower-right (high volume, low cancellation rate) 
    are your healthy, scalable operations.
    
    **Key Insight**: A city with high cancellation rate and high volume should be your top priority for 
    investigation. Low-volume, high-cancellation cells may be niche cases that don't warrant intervention.
    """)
    cancellations = query("""
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
        ORDER BY cancellation_rate DESC
    """)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            cancellations.head(15),
            x="city", y="cancellation_rate",
            color="cuisine_type", text_auto=".1f",
            labels={"cancellation_rate": "Cancellation Rate (%)", "city": "City"},
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(
            cancellations,
            x="total_orders", y="cancellation_rate",
            size="cancelled_orders", color="cuisine_type",
            hover_name="city", text="city",
            labels={"total_orders": "Total Orders", "cancellation_rate": "Cancellation Rate (%)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(cancellations, use_container_width=True, hide_index=True)


# ── PAGE: DEMAND PATTERNS ────────────────────────────────────
def page_demand():
    st.title("Hourly Demand Pattern")
    st.markdown("""
    **About This Analysis**: Understanding when customers order is critical for staffing, delivery agent 
    scheduling, and restaurant preparation. This heatmap reveals demand patterns across hours of the day 
    and days of the week.
    
    **What to Look For**: Peak hours (typically lunch 12-2pm and dinner 6-9pm) show when you need maximum 
    delivery agent availability. Weekend patterns often differ significantly from weekdays — higher volume 
    but also higher variance. Off-peak demand represents opportunities for promotions to fill capacity.
    """)
    show_kpi_strip()

    st.subheader("Orders by Day of Week & Hour")
    st.markdown("""
    **What This Shows**: A heatmap where darker red means more orders. Each cell shows the total number of 
    delivered orders for that specific day-of-week and hour-of-day combination. The pattern reveals your 
    demand rhythm.
    
    **Key Insights**:
    - **Lunch peak**: Usually 11am-2pm — weaker than dinner in most markets
    - **Dinner peak**: Usually 6pm-9pm — typically the largest demand window
    - **Weekend effect**: Saturday and Sunday often have higher volume but shifted timing (later starts)
    - **Late night**: Orders after 10pm may indicate underserved demand or delivery agent shortage
    
    **Operational Use**: Align delivery agent shifts with these patterns. If dinner peak is 7-9pm, agents 
    should be on the road by 6:30pm, not arriving at 7pm when the rush has already started.
    """)
    demand = query("""
        SELECT
            d.day_name,
            fo.order_hour,
            COUNT(*) AS orders,
            ROUND(SUM(fo.net_total)::numeric, 2) AS revenue
        FROM fact_orders fo
        JOIN dim_date d ON fo.date_id = d.date_id
        WHERE LOWER(fo.status) = 'delivered'
        GROUP BY d.day_name, fo.order_hour
        ORDER BY d.day_name, fo.order_hour
    """)

    # Pivot for heatmap
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    demand["day_name"] = pd.Categorical(demand["day_name"], categories=day_order, ordered=True)

    pivot = demand.pivot_table(index="day_name", columns="order_hour", values="orders", fill_value=0)

    fig = px.imshow(
        pivot,
        labels=dict(x="Hour of Day", y="Day of Week", color="Orders"),
        x=list(range(24)),
        y=day_order,
        color_continuous_scale=[[0, "#eceff4"], [0.3, "#d08770"], [0.7, "#bf616a"], [1, "#4c566a"]],
    )
    fig.update_xaxes(side="bottom")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(demand, use_container_width=True, hide_index=True)


# ── PAGE: DELIVERY AGENTS ────────────────────────────────────
def page_agents():
    st.title("Delivery Agent Performance")
    st.markdown("""
    **About This Analysis**: Delivery agents are the face of the platform and the most operationally 
    complex workforce. Their performance directly impacts customer satisfaction (delivery time) and 
    unit economics (deliveries per shift). This page analyzes agent productivity and efficiency.
    
    **What to Look For**: Top agents by delivery count should also have competitive average delivery 
    times. An agent with many deliveries but slow times may be overworked. Fast agents with few 
    deliveries may be underutilized or new. Performance tier distribution reveals whether your 
    tiering system is well-calibrated.
    """)
    show_kpi_strip()

    st.subheader("Agent Leaderboard")
    st.markdown("""
    **Left Chart**: Top 15 agents by total deliveries, colored by performance tier. Hover to see average 
    delivery time and total value of orders delivered. This reveals who your most productive agents are.
    
    **Right Chart**: Box plot showing delivery volume distribution by performance tier. The box shows the 
    middle 50% of agents in each tier, the line is the median, and whiskers show the range. Overlap between 
    tiers indicates that tier assignments may need recalibration — e.g., if some "Gold" agents have fewer 
    deliveries than "Silver" agents, the criteria may include factors beyond pure volume.
    
    **Key Insight**: Look for agents in the top 15 who are not in the highest performance tier — they may 
    be high-performers who should be promoted or rewarded to prevent churn.
    """)
    agents = query("""
        SELECT
            a.agent_id,
            a.name,
            a.city,
            a.vehicle,
            a.performance_tier,
            COUNT(*) AS deliveries,
            ROUND(AVG(fo.delivery_time_min)::numeric, 1) AS avg_time,
            ROUND(SUM(fo.net_total)::numeric, 2) AS total_value
        FROM fact_orders fo
        JOIN dim_delivery_agent a ON fo.agent_id = a.agent_id
        GROUP BY a.agent_id, a.name, a.city, a.vehicle, a.performance_tier
        ORDER BY deliveries DESC
    """)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            agents.head(15),
            x="name", y="deliveries",
            color="performance_tier", text_auto=True,
            hover_data=["avg_time", "total_value"],
            labels={"deliveries": "Deliveries", "name": "Agent"},
        )
        fig.update_layout(xaxis_tickangle=-45, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.box(
            agents,
            x="performance_tier", y="deliveries",
            color="performance_tier",
            labels={"deliveries": "Deliveries", "performance_tier": "Tier"},
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(agents, use_container_width=True, hide_index=True)


# ── PAGE: RFM ────────────────────────────────────────────────
def page_rfm():
    st.title("RFM Customer Segmentation")
    st.markdown("""
    **About This Analysis**: RFM (Recency, Frequency, Monetary) analysis is a proven method for 
    customer segmentation. It scores each customer on three dimensions: how recently they ordered (R), 
    how frequently they order (F), and how much they spend (M). Each dimension is scored 1-5 using 
    NTILE quintiles, then combined into segments with actionable labels.
    
    **Why RFM Matters**: Unlike simple demographics, RFM is behavioral — it tells you what customers 
    actually do, not who they are. This makes it directly actionable for marketing, retention, and 
    growth strategies.
    
    **What to Look For**: The bar chart shows how many customers fall into each segment. The scatter plot 
    reveals the relationship between order frequency and monetary value — customers above the implicit 
    trend line are more valuable than their frequency alone would predict.
    """)
    st.markdown("Recency, Frequency, Monetary analysis with **NTILE(5) scoring** and actionable segment labels.")
    show_kpi_strip()

    rfm = query("""
        WITH base_rfm AS (
            SELECT
                c.customer_id, c.full_name, c.city, c.customer_segment,
                COUNT(*) AS frequency,
                SUM(fo.net_total) AS monetary,
                CURRENT_DATE - MAX(fo.order_timestamp::DATE) AS recency_days
            FROM dim_customer c
            JOIN fact_orders fo ON c.customer_id = fo.customer_id
            WHERE LOWER(fo.status) = 'delivered'
            GROUP BY c.customer_id, c.full_name, c.city, c.customer_segment
        ),
        scored AS (
            SELECT *,
                NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
                NTILE(5) OVER (ORDER BY frequency ASC)      AS f_score,
                NTILE(5) OVER (ORDER BY monetary ASC)       AS m_score
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
            ROUND(AVG(rfm_total)::numeric, 1) AS avg_rfm_score
        FROM segmented
        GROUP BY rfm_segment
        ORDER BY avg_rfm_score DESC
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Segment Distribution")
        st.markdown("""
        **What This Shows**: Number of customers in each RFM segment. Champions are your best customers 
        (high R, F, and M scores). Lost customers were once active but haven't ordered recently. The 
        shape of this distribution tells you whether your customer base is healthy or at risk.
        
        **Healthy Distribution**: Champions and Loyal Customers are among the largest segments.
        **Warning Signs**: Lost, At-Risk, or About to Sleep dominate — indicates retention problems.
        **Growth Mode**: New Customers and Potential Loyalists are large — acquisition is working, but 
        you need to ensure they convert to Loyal over time.
        """)
        fig = px.bar(
            rfm, x="rfm_segment", y="customer_count",
            color="rfm_segment", text_auto=True,
            labels={"customer_count": "Customers", "rfm_segment": "Segment"},
            color_discrete_sequence=["#88c0d0", "#81a1c1", "#5e81ac", "#a3be8c", "#ebcb8b", "#d08770", "#bf616a", "#b48ead", "#8fbcbb"],
        )
        fig.update_layout(xaxis_tickangle=-45, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Frequency vs Monetary Value")
        st.markdown("""
        **What This Shows**: Each bubble is an RFM segment, positioned by average order frequency (x-axis) 
        and average monetary value (y-axis). Bubble size = number of customers in that segment. This reveals 
        which segments are most profitable and whether frequency correlates with spending.
        
        **Key Insight**: Segments above the implicit diagonal are more valuable than their frequency alone 
        would predict — they're your high-spenders. Segments below it order frequently but spend less — 
        they're deal-driven or price-sensitive.
        """)
        fig = px.scatter(
            rfm, x="avg_frequency", y="avg_monetary",
            size="customer_count", color="rfm_segment",
            hover_name="rfm_segment", text="rfm_segment",
            labels={"avg_frequency": "Avg Frequency", "avg_monetary": "Avg Monetary Value (₹)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(rfm, use_container_width=True, hide_index=True)


# ── PAGE: ML FORECAST ────────────────────────────────────────
def page_forecast():
    st.title("ML Order Volume Forecast")
    st.markdown("""
    **About This Forecast**: This page uses Facebook Prophet, a time-series forecasting model, to predict 
    order volume for the next 30 days. Prophet accounts for weekly seasonality (weekdays vs weekends), 
    yearly seasonality (monthly trends), and adds a weekend regressor to capture day-of-week effects.
    
    **Model Details**: Prophet fits an additive model where trend, seasonality, and holidays/regressors 
    are combined. The confidence interval (shaded area) represents uncertainty — wider intervals mean less 
    certainty, typically increasing as we forecast further into the future.
    
    **What to Look For**: The predicted order line (red) shows expected daily volume. The shaded confidence 
    band tells you the range of plausible outcomes. Use the lower bound for conservative staffing and the 
    upper bound for capacity planning.
    """)
    st.markdown("**Model**: Facebook Prophet | **Horizon**: 30 days | **Features**: weekend regressor, weekly + yearly seasonality")

    # Try to load forecast
    try:
        forecast = query("SELECT * FROM ml_order_forecast ORDER BY forecast_date")
        has_forecast = True
    except Exception:
        has_forecast = False
        st.warning("No forecast data found. Run `python scripts/ml_forecast.py` first.")

    if has_forecast:
        col1, col2, col3 = st.columns(3)

        # Show metrics if available
        try:
            metrics = query("SELECT * FROM ml_model_metrics ORDER BY evaluated_at DESC LIMIT 1")
            if len(metrics) > 0:
                row = metrics.iloc[0]
                col1.metric("MAPE", f"{row['mape']:.1f}%" if row.get("mape") else "N/A")
                col2.metric("MAE", f"{row['mae']:.1f}" if row.get("mae") else "N/A")
                col3.metric("RMSE", f"{row['rmse']:.1f}" if row.get("rmse") else "N/A")
        except Exception:
            pass

        st.subheader("30-Day Order Volume Forecast")
        st.markdown("""
        **What This Shows**: Predicted daily order volume for the next 30 days. The red line is the model's 
        best estimate. The shaded band around it is the 80% confidence interval — the range where the actual 
        value is expected to fall 80% of the time.
        
        **How to Use**: Plan delivery agent staffing based on the lower bound (conservative) or the prediction 
        (optimistic). If the forecast shows a significant dip, investigate whether it's a real seasonal pattern 
        or model uncertainty.
        """)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=forecast["forecast_date"], y=forecast["predicted_orders"],
            mode="lines+markers", name="Predicted",
            line=dict(color="#bf616a", width=2), marker_size=4,
        ))
        fig.add_trace(go.Scatter(
            x=forecast["forecast_date"], y=forecast["upper_bound"],
            mode="lines", name="Upper Bound",
            line=dict(color="rgba(191,97,106,0.25)", width=1),
            showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=forecast["forecast_date"], y=forecast["lower_bound"],
            mode="lines", name="Lower Bound",
            line=dict(color="rgba(191,97,106,0.25)", width=1),
            fill="tonexty",
            fillcolor="rgba(191,97,106,0.1)",
            showlegend=False,
        ))
        fig.update_layout(
            xaxis_title="Date", yaxis_title="Predicted Orders",
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(forecast, use_container_width=True, hide_index=True)

    # Try to load forecast plot
    plot_path = Path(__file__).resolve().parent.parent / "outputs" / "plots" / "forecast_plot.png"
    if plot_path.exists():
        st.subheader("Prophet Forecast Plot")
        st.image(str(plot_path), use_container_width=True)


# ── ROUTER ───────────────────────────────────────────────────
pages = {
    "Overview": page_overview,
    "Revenue": page_revenue,
    "Restaurants": page_restaurants,
    "Customers": page_customers,
    "Menu Items": page_menu_items,
    "Cancellations": page_cancellations,
    "Demand Patterns": page_demand,
    "Delivery Agents": page_agents,
    "RFM Segmentation": page_rfm,
    "ML Forecast": page_forecast,
}

pages[nav]()
