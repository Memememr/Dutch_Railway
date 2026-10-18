import streamlit as st
import database
import altair as alt
import pandas as pd

from queries import get_avg_cancellation_report

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
 
 
def normalize_avg_report(df: pd.DataFrame, time_granularity: str) -> pd.DataFrame:
    """Accept the older column names and fail with a readable message otherwise."""
    df = df.rename(columns=COL_ALIASES)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(
            f"get_avg_cancellation_report returned columns {list(df.columns)}; "
            f"missing {missing}."
        )
    df = df.copy()
    for c in ("avg_departure_delay", "avg_arrival_delay"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["time_period"] = df["time_period"].astype(str)
    if "time_granularity" not in df.columns:
        df.insert(0, "time_granularity", time_granularity)
    return df
 
 
@st.cache_data(show_spinner="Loading data…", ttl=600)
def load_avg_report(time_granularity: str) -> pd.DataFrame:
    """One query per granularity; Streamlit caches each result separately."""
    return normalize_avg_report(get_avg_cancellation_report(time_granularity), time_granularity)
 
 
# ----------------------------------------------------------------------------
# SHARED UI HELPERS
# ----------------------------------------------------------------------------
def kpi_row(items: list[tuple[str, str, str | None]]) -> None:
    for col, (label, value, delta) in zip(st.columns(len(items)), items):
        col.metric(label, value, delta)
 
 
def download_button(df: pd.DataFrame, name: str) -> None:
    st.download_button(
        "⬇️ Download CSV", df.to_csv(index=False).encode(), f"{name}.csv", "text/csv"
    )
 
 
def coming_soon(title: str, description: str, planned: list[str]) -> None:
    st.info(f"**{title}** is still in development.")
    st.caption(description)
    st.markdown("**Planned sections** (same layout as the other reports):")
    st.markdown("\n".join(f"- {p}" for p in planned))
 
 
# ----------------------------------------------------------------------------
# REPORT 1: Average delays (get_avg_cancellation_report)
# ----------------------------------------------------------------------------
def render_avg_delay_report() -> None:
    # ---- controls -----------------------------------------------------------
    c1, c2, c3 = st.columns([1.2, 2, 2])
    gran = c1.radio("Time granularity", GRANULARITIES, index=2, horizontal=False, key="r1_gran")
 
    gdf = load_avg_report(gran)
    periods = sorted(gdf["time_period"].unique())
    period_label = {
        "Yearly": "year", "Quarterly": "quarter", "Monthly": "month",
        "Weekly": "week", "Daily": "day",
    }[gran]
    sel_periods = c2.multiselect(
        f"Filter by {period_label} (empty = all)", periods, key=f"r1_periods_{gran}"
    )
    stations = sorted(gdf["station_name"].unique())
    sel_stations = c3.multiselect("Filter by station (empty = all)", stations, key="r1_stations")
 
    view = gdf
    if sel_periods:
        view = view[view["time_period"].isin(sel_periods)]
    if sel_stations:
        view = view[view["station_name"].isin(sel_stations)]
 
    if view.empty:
        st.warning("No data for the selected filters.")
        return
 
    # ---- KPIs ---------------------------------------------------------------
    dep, arr = view["avg_departure_delay"].mean(), view["avg_arrival_delay"].mean()
    worst = (
        view.groupby("station_name")[["avg_departure_delay", "avg_arrival_delay"]]
        .mean().sum(axis=1).idxmax()
    )
    kpi_row([
        ("Avg departure delay", f"{dep:.1f} min", None),
        ("Avg arrival delay", f"{arr:.1f} min", f"{arr - dep:+.1f} vs departure"),
        ("Stations", f"{view['station_name'].nunique()}", None),
        ("Worst station", worst, None),
    ])
 
    # ---- charts ---------------------------------------------------------------
    long = view.melt(
        id_vars=["time_period", "station_name"],
        value_vars=["avg_departure_delay", "avg_arrival_delay"],
        var_name="metric", value_name="minutes",
    )
    long["metric"] = long["metric"].map(
        {"avg_departure_delay": "Departure", "avg_arrival_delay": "Arrival"}
    )
 
    left, right = st.columns(2)
    with left:
        st.subheader("Trend over time")
        trend = long.groupby(["time_period", "metric"], as_index=False)["minutes"].mean()
        # Daily/weekly series can have hundreds of points; keep x-axis readable
        line = (
            alt.Chart(trend)
            .mark_line(point=len(trend) < 80)
            .encode(
                x=alt.X("time_period:N", sort=None, title=None,
                        axis=alt.Axis(labelAngle=-45, labelOverlap="parity")),
                y=alt.Y("minutes:Q", title="Avg delay (min)"),
                color=alt.Color("metric:N", title=None),
                tooltip=["time_period", "metric", alt.Tooltip("minutes:Q", format=".2f")],
            )
            .properties(height=340)
        )
        st.altair_chart(line, width="stretch")
 
    with right:
        st.subheader("Delay by station")
        by_station = long.groupby(["station_name", "metric"], as_index=False)["minutes"].mean()
        bars = (
            alt.Chart(by_station)
            .mark_bar()
            .encode(
                x=alt.X("station_name:N", title=None, sort="-y"),
                y=alt.Y("minutes:Q", title="Avg delay (min)"),
                xOffset="metric:N",
                color=alt.Color("metric:N", title=None),
                tooltip=["station_name", "metric", alt.Tooltip("minutes:Q", format=".2f")],
            )
            .properties(height=340)
        )
        st.altair_chart(bars, width="stretch")
 
    # ---- summary table ----------------------------------------------------------
    st.subheader("Summary by station")
    summary = (
        view.groupby("station_name")
        .agg(
            periods=("time_period", "nunique"),
            avg_departure_delay=("avg_departure_delay", "mean"),
            avg_arrival_delay=("avg_arrival_delay", "mean"),
            max_arrival_delay=("avg_arrival_delay", "max"),
        )
        .round(2)
        .sort_values("avg_arrival_delay", ascending=False)
        .reset_index()
    )
    st.dataframe(
        summary,
        width="stretch",
        hide_index=True,
        column_config={
            "avg_arrival_delay": st.column_config.ProgressColumn(
                "avg_arrival_delay", format="%.2f", min_value=0,
                max_value=float(summary["avg_arrival_delay"].max()) * 1.1,
            )
        },
    )
 
    with st.expander("Detail rows"):
        detail = view.sort_values(["time_period", "station_name"]).reset_index(drop=True)
        st.dataframe(detail, width="stretch", hide_index=True)
        download_button(detail, f"avg_delay_{gran.lower()}")
 
 
# ----------------------------------------------------------------------------
# REPORTS 2-4 (placeholders -- same shell, fill in when queries are ready)
# ----------------------------------------------------------------------------
def render_station_cancellations() -> None:
    coming_soon(
        "Station Cancellations  ·  get_station_cancellations()",
        "Cancellation counts and rates per station.",
        ["KPI cards (total cancellations, rate, worst station)",
         "Trend line over time (reuse the granularity control)",
         "Bar chart by station + heatmap station × period",
         "Summary table"],
    )
 
 
def render_service_company_reliability() -> None:
    coming_soon(
        "Service Company Reliability  ·  get_service_company_reliability()",
        "Reliability of each service company (on-time %, cancellations, delays).",
        ["KPI cards (best/worst company, overall on-time %)",
         "Ranked bar chart of reliability score",
         "Trend per company",
         "Summary table"],
    )
 
 
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
 