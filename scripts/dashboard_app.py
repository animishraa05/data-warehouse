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
    page_title="FoodFlow Analytics Dashboard",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DB CONNECTION ────────────────────────────────────────────
@st.cache_resource
def get_engine():
    url = (
        f"postgresql+psycopg2://{os.getenv('DB_USER', 'dw_user')}:"
        f"{os.getenv('DB_PASS', 'secret')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5433')}/"
        f"{os.getenv('DB_NAME', 'foodflow_dw')}"
    )
    return create_engine(url)


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(sql, conn)


# ── SIDEBAR ──────────────────────────────────────────────────
st.sidebar.title("🍔 FoodFlow Analytics")
st.sidebar.markdown("---")

nav = st.sidebar.radio(
    "Navigate",
    ["📊 Overview", "💰 Revenue", "🏆 Restaurants", "👥 Customers",
     "🍔 Menu Items", "❌ Cancellations", "⏰ Demand Patterns",
     "🚴 Delivery Agents", "📈 RFM Segmentation", "🔮 ML Forecast"],
)

st.sidebar.markdown("---")
st.sidebar.caption("Data Warehouse: PostgreSQL 15")
st.sidebar.caption("ETL: Airflow Daily Pipeline")

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
    st.title("📊 FoodFlow Analytics — Dashboard")
    st.markdown("Food delivery data warehouse with **80K+ orders**, **5 dimensions**, **2 fact tables**, and **ML forecasting**.")
    show_kpi_strip()

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Order Status Distribution")
        status_data = query("""
            SELECT status, COUNT(*) AS orders
            FROM fact_orders GROUP BY status
        """)
        fig = px.pie(
            status_data, values="orders", names="status",
            color_discrete_sequence=px.colors.qualitative.Set2,
            hole=0.4,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Platform Split")
        platform_data = query("""
            SELECT platform, COUNT(*) AS orders,
                   ROUND(SUM(net_total)::numeric, 2) AS revenue
            FROM fact_orders WHERE is_delivered = 1
            GROUP BY platform
        """)
        fig = px.bar(
            platform_data, x="platform", y="orders",
            color="platform", text_auto=",",
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig.update_layout(showlegend=False, yaxis_title="Orders")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly Revenue Trend")
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
        line=dict(color="#1f77b4", width=2),
        fill="tozeroy", fillcolor="rgba(31,119,180,0.1)",
    ))
    fig.add_trace(go.Bar(
        x=revenue["date_str"], y=revenue["orders"],
        name="Orders", yaxis="y2",
        marker_color="rgba(255,165,0,0.6)",
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
    st.title("💰 Revenue Analytics")
    show_kpi_strip()

    st.subheader("Monthly Revenue Trend with MoM Growth")
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
        fig.update_traces(line_color="#2ecc71", line_width=2, marker_size=6)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            revenue.dropna(subset=["mom_growth_pct"]),
            x="date_str", y="mom_growth_pct",
            labels={"mom_growth_pct": "MoM Growth (%)", "date_str": "Month"},
            color="mom_growth_pct",
            color_continuous_scale="RdYlGn",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(revenue, use_container_width=True, hide_index=True)


# ── PAGE: RESTAURANTS ────────────────────────────────────────
def page_restaurants():
    st.title("🏆 Restaurant Analytics")
    show_kpi_strip()

    st.subheader("Top 10 Restaurants by Revenue")
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
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(restaurants, use_container_width=True, hide_index=True)


# ── PAGE: CUSTOMERS ──────────────────────────────────────────
def page_customers():
    st.title("👥 Customer Analytics")
    show_kpi_strip()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Customer Segments")
        segments = query("""
            SELECT customer_segment, COUNT(*) AS cnt
            FROM dim_customer
            GROUP BY customer_segment
            ORDER BY cnt DESC
        """)
        fig = px.pie(
            segments, values="cnt", names="customer_segment",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            hole=0.4,
        )
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Customer Lifetime Value (Top 20)")
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
        )
        fig.update_layout(xaxis_tickangle=-45, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("CLV Distribution")
    st.dataframe(clv, use_container_width=True, hide_index=True)


# ── PAGE: MENU ITEMS ─────────────────────────────────────────
def page_menu_items():
    st.title("🍔 Menu Item Analytics")
    show_kpi_strip()

    st.subheader("Top 10 Menu Items by Revenue")
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
    st.title("❌ Cancellation Analysis")
    show_kpi_strip()

    st.subheader("Cancellation Rate by City & Cuisine")
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
    st.title("⏰ Hourly Demand Pattern")
    show_kpi_strip()

    st.subheader("Orders by Day of Week & Hour")
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
        color_continuous_scale="YlOrRd",
    )
    fig.update_xaxes(side="bottom")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(demand, use_container_width=True, hide_index=True)


# ── PAGE: DELIVERY AGENTS ────────────────────────────────────
def page_agents():
    st.title("🚴 Delivery Agent Performance")
    show_kpi_strip()

    st.subheader("Agent Leaderboard")
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
    st.title("📈 RFM Customer Segmentation")
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
        fig = px.bar(
            rfm, x="rfm_segment", y="customer_count",
            color="rfm_segment", text_auto=True,
            labels={"customer_count": "Customers", "rfm_segment": "Segment"},
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig.update_layout(xaxis_tickangle=-45, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
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
    st.title("🔮 ML Order Volume Forecast")
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
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=forecast["forecast_date"], y=forecast["predicted_orders"],
            mode="lines+markers", name="Predicted",
            line=dict(color="#e74c3c", width=2), marker_size=4,
        ))
        fig.add_trace(go.Scatter(
            x=forecast["forecast_date"], y=forecast["upper_bound"],
            mode="lines", name="Upper Bound",
            line=dict(color="rgba(231,76,60,0.3)", width=1),
            showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=forecast["forecast_date"], y=forecast["lower_bound"],
            mode="lines", name="Lower Bound",
            line=dict(color="rgba(231,76,60,0.3)", width=1),
            fill="tonexty",
            fillcolor="rgba(231,76,60,0.15)",
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
    "📊 Overview": page_overview,
    "💰 Revenue": page_revenue,
    "🏆 Restaurants": page_restaurants,
    "👥 Customers": page_customers,
    "🍔 Menu Items": page_menu_items,
    "❌ Cancellations": page_cancellations,
    "⏰ Demand Patterns": page_demand,
    "🚴 Delivery Agents": page_agents,
    "📈 RFM Segmentation": page_rfm,
    "🔮 ML Forecast": page_forecast,
}

pages[nav]()
