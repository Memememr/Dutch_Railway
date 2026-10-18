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
# DATA LAYER
# ----------------------------------------------------------------------------
REQUIRED_COLS = ["time_period", "station_name", "avg_departure_delay", "avg_arrival_delay"]
COL_ALIASES = {"departure_delay": "avg_departure_delay", "arrival_delay": "avg_arrival_delay"}
 
 
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
 
 
def render_service_company_reliability() -> None:
    st.dataframe(queries.get_service_reliability())
 
 
def render_most_delayed_services() -> None:
    coming_soon(
        "Most Delayed Services",
        "Services ranked by delay frequency and duration.",
        ["KPI cards (top delayed service, total delay minutes)",
         "Top-N bar chart (N selectable)",
         "Delay distribution / trend",
         "Summary table"],
    )
 
 
REPORTS = {
    "Average Delays": render_avg_delay_report,
    "Station Cancellations": render_station_cancellations,
    "Service Reliability": render_service_company_reliability,
    "Most Delayed Services": render_most_delayed_services,
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
 