import streamlit as st
import database
import altair as alt
import pandas as pd

import queries

GRANULARITIES = ["Yearly", "Quarterly", "Monthly", "Weekly", "Daily"]

st.set_page_config(
    page_title="Dutch Railway OLAP Dashboard",
    layout="wide",
    page_icon = "train-icon.png"
)

 
# ----------------------------------------------------------------------------
# SHARED UI HELPERS
# ----------------------------------------------------------------------------
def kpi_row(items: list[tuple[str, str, str | None]]) -> None:
    for col, (label, value, delta) in zip(st.columns(len(items)), items):
        col.metric(label, value, delta)

 
def coming_soon(title: str, description: str, planned: list[str]) -> None:
    st.dataframe(queries.get_station_cancellations())
 
 
# ----------------------------------------------------------------------------
# REPORT 1: Average delays (get_avg_cancellation_report)
# ----------------------------------------------------------------------------
def render_avg_delay_report() -> None:
   st.dataframe(queries.get_avg_delay_report())
 
# ----------------------------------------------------------------------------
# REPORT 2: Station cancellations (get_station_cancellation_report)
# ----------------------------------------------------------------------------
def render_station_cancellations() -> None:
    st.dataframe(queries.get_station_cancellations())
 
# ----------------------------------------------------------------------------
# REPORT 3: Service Reliability (get_service_reliability())
# ----------------------------------------------------------------------------
def render_service_reliability() -> None:
    st.dataframe(queries.get_service_reliability())
 

# ----------------------------------------------------------------------------
# REPORT 4: Service Related Delays (get_service_delays())
# ----------------------------------------------------------------------------
def get_service_related_delays() -> None:
    st.dataframe(queries.get_service_delays())
 
 
REPORTS = {
    "Average Delays": render_avg_delay_report,
    "Station Cancellations": render_station_cancellations,
    "Service Reliability": render_service_reliability,
    "Most Delayed Services": get_service_related_delays,
}
 
# ----------------------------------------------------------------------------
# PAGE SHELL
# ----------------------------------------------------------------------------
st.title("Dutch Railway Analytical Report")
st.caption("")
 
tabs = st.tabs(list(REPORTS))
for tab, render in zip(tabs, REPORTS.values()):
    with tab:
        render()
 