"""Step 3: Streamlit dashboard. Run:  streamlit run app.py"""
import sqlite3
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB = Path(__file__).parent / "sales.db"
st.set_page_config(page_title="Furniture Sales Forecasting", layout="wide")


@st.cache_data
def q(sql):
    with sqlite3.connect(DB) as con:
        return pd.read_sql(sql, con)


st.title("Furniture Store Sales Forecasting")
st.caption("SQLite + Python (SARIMA, Random Forest, Gradient Boosting) on Superstore furniture orders, 2014-2017")

hist = q("SELECT * FROM monthly_features")
hist["month"] = pd.to_datetime(hist["month"])
pred = q("SELECT * FROM predictions")
pred["month"] = pd.to_datetime(pred["month"])
metrics = q("SELECT * FROM model_metrics")

c1, c2, c3 = st.columns(3)
c1.metric("Total sales", f"${hist['sales'].sum():,.0f}")
c2.metric("Best month", hist.loc[hist['sales'].idxmax(), 'month'].strftime("%b %Y"))
c3.metric("Avg monthly sales", f"${hist['sales'].mean():,.0f}")

tab1, tab2, tab3 = st.tabs(["Forecast", "Model comparison", "SQL analytics"])

with tab1:
    fut = pred[pred.kind == "future"]
    model_name = fut["model"].iloc[0]
    fig = go.Figure()
    fig.add_scatter(x=hist.month, y=hist.sales, name="Actual", mode="lines+markers")
    fig.add_scatter(x=fut.month, y=fut.predicted, name=f"Forecast ({model_name})",
                    mode="lines+markers", line=dict(dash="dash"))
    fig.update_layout(yaxis_title="Monthly sales ($)", height=450)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(fut[["month", "predicted"]].assign(predicted=lambda d: d.predicted.round(0)),
                 hide_index=True)

with tab2:
    st.subheader("2017 hold-out results (train 2014-2016)")
    st.dataframe(metrics, hide_index=True)
    test = pred[pred.kind == "test"]
    models = st.multiselect("Models", test.model.unique().tolist(),
                            default=test.model.unique().tolist()[:3])
    act = test[test.model == test.model.iloc[0]]
    fig = go.Figure()
    fig.add_scatter(x=act.month, y=act.actual, name="Actual", line=dict(width=4, color="black"))
    for m in models:
        d = test[test.model == m]
        fig.add_scatter(x=d.month, y=d.predicted, name=m)
    fig.update_layout(height=420, yaxis_title="Sales ($)")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Sales by sub-category and year")
    sub = q("SELECT * FROM subcategory_yearly")
    st.plotly_chart(px.bar(sub, x="year", y="sales", color="sub_category", barmode="group"),
                    use_container_width=True)
    st.subheader("Region x segment")
    rs = q("SELECT * FROM region_segment_sales")
    st.plotly_chart(px.bar(rs, x="region", y="sales", color="segment", barmode="group"),
                    use_container_width=True)
    st.subheader("Window-function features (LAG, moving average, YoY)")
    st.dataframe(hist, hide_index=True)
