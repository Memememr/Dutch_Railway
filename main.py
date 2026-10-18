import streamlit as st
import altair as alt
import pandas as pd

import queries

GRANULARITIES = ["Yearly", "Quarterly", "Monthly", "Weekly", "Daily"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
SERVICE_LEVELS = ["Company", "Service Type", "Train Number"]

st.set_page_config(
    page_title="Dutch Railway OLAP Dashboard",
    layout="wide",
    page_icon="train-icon.png",
)


# ----------------------------------------------------------------------------
# SHARED UI HELPERS
# ----------------------------------------------------------------------------
def kpi_row(items: list[tuple[str, str, str | None]]) -> None:
    for col, (label, value, delta) in zip(st.columns(len(items)), items):
        col.metric(label, value, delta)


def time_axis(granularity: str, title: str = "Period") -> alt.X:
    """X axis for time_period; month names need explicit calendar order."""
    sort = MONTHS if granularity == "Monthly" else "ascending"
    return alt.X("time_period:O", sort=sort, title=title)


def fmt(value, suffix: str = "", decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.{decimals}f}{suffix}"


def empty_guard(df: pd.DataFrame | None) -> bool:
    """Show a message and return True when there is nothing to plot."""
    if df is None or df.empty:
        st.info("No data for the selected filters.")
        return True
    return False


def show_table(df: pd.DataFrame, label: str = "View data table") -> None:
    with st.expander(label):
        st.dataframe(df, use_container_width=True, hide_index=True)


# Cached filter option lists (queried here so queries.py stays untouched)
@st.cache_data(ttl=3600)
def company_options() -> list[str]:
    df = queries.run_query("SELECT DISTINCT company FROM dim_service ORDER BY company;")
    return ["ALL"] + df["company"].dropna().astype(str).tolist()


@st.cache_data(ttl=3600)
def service_type_options() -> list[str]:
    df = queries.run_query("SELECT DISTINCT service_type FROM dim_service ORDER BY service_type;")
    return ["ALL"] + df["service_type"].dropna().astype(str).tolist()


@st.cache_data(ttl=3600)
def train_options() -> list[str]:
    df = queries.run_query("SELECT DISTINCT train_number FROM dim_service ORDER BY train_number;")
    return ["ALL"] + df["train_number"].dropna().astype(str).tolist()


# ----------------------------------------------------------------------------
# REPORT 1: Average delays (get_avg_delay_report)
# ----------------------------------------------------------------------------
def render_avg_delay_report() -> None:
    st.header("Average Station Delay & Network Benchmarks")
    st.caption("Tracks arrival and departure delays alongside network-wide averages and rank calculations.")

    c1, c2, c3, c4 = st.columns(4)
    gran = c1.selectbox("Granularity", GRANULARITIES, index=2, key="d_gran")
    month = c2.selectbox("Month", ["ALL"] + MONTHS, key="d_month")
    company = c3.selectbox("Company", company_options(), key="d_company")
    station = c4.selectbox("Station", queries.get_all_stations(), key="d_station")

    df = queries.get_avg_delay_report(gran, month, company, station)
    if empty_guard(df):
        return

    # KPIs
    worst = df.groupby("station_name")["arrival_delay"].mean().idxmax()
    kpi_row([
        ("Avg arrival delay (min)", fmt(df["arrival_delay"].mean()), None),
        ("Avg departure delay (min)", fmt(df["departure_delay"].mean()), None),
        ("Severe arrivals (>15 min)", f"{int(df['severe_issues'].sum()):,}", None),
        ("Most delayed station", str(worst), None),
    ])

    left, right = st.columns(2)

    # Network benchmark trend (one row per period, since benchmark is per period)
    with left:
        st.subheader("Network benchmark over time")
        bench = (
            df.drop_duplicates("time_period")
            [["time_period", "benchmark_arrival", "benchmark_departure"]]
            .melt("time_period", var_name="Type", value_name="Minutes")
        )
        bench["Type"] = bench["Type"].map({
            "benchmark_arrival": "Arrival",
            "benchmark_departure": "Departure",
        })
        chart = (
            alt.Chart(bench)
            .mark_line(point=True)
            .encode(
                x=time_axis(gran),
                y=alt.Y("Minutes:Q", title="Avg delay (min)"),
                color=alt.Color("Type:N", title=None),
                tooltip=["time_period", "Type", "Minutes"],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)

    # Top N stations
    with right:
        st.subheader("Most delayed stations")
        top_n = st.slider("Top N", 5, 30, 10, key="d_topn")
        agg = (
            df.groupby("station_name", as_index=False)
            .agg(arrival_delay=("arrival_delay", "mean"),
                 departure_delay=("departure_delay", "mean"))
            .nlargest(top_n, "arrival_delay")
            .melt("station_name", var_name="Type", value_name="Minutes")
        )
        agg["Type"] = agg["Type"].map({
            "arrival_delay": "Arrival",
            "departure_delay": "Departure",
        })
        order = (
            agg[agg["Type"] == "Arrival"]
            .sort_values("Minutes", ascending=False)["station_name"].tolist()
        )
        chart = (
            alt.Chart(agg)
            .mark_bar()
            .encode(
                y=alt.Y("station_name:N", sort=order, title=None),
                x=alt.X("Minutes:Q", title="Avg delay (min)"),
                yOffset="Type:N",
                color=alt.Color("Type:N", title=None),
                tooltip=["station_name", "Type", alt.Tooltip("Minutes:Q", format=".2f")],
            )
            .properties(height=max(320, top_n * 28))
        )
        st.altair_chart(chart, use_container_width=True)

    # Heatmap of station x period (only readable when not too many stations)
    if station == "ALL":
        st.subheader("Station × period heatmap (arrival delay)")
        top_stations = (
            df.groupby("station_name")["arrival_delay"].mean()
            .nlargest(15).index
        )
        heat = df[df["station_name"].isin(top_stations)]
        chart = (
            alt.Chart(heat)
            .mark_rect()
            .encode(
                x=time_axis(gran),
                y=alt.Y("station_name:N", title=None),
                color=alt.Color("arrival_delay:Q", title="Min", scale=alt.Scale(scheme="orangered")),
                tooltip=["time_period", "station_name", "arrival_delay", "arrival_delay_rank"],
            )
            .properties(height=420)
        )
        st.altair_chart(chart, use_container_width=True)

    st.dataframe(df, width="stretch",hide_index=True)


# ----------------------------------------------------------------------------
# REPORT 2: Station cancellations (get_station_cancellations)
# ----------------------------------------------------------------------------
def render_station_cancellations() -> None:
    st.header("Station Cancellations")
    st.caption("Cancelled stops per station, split into fully and partially cancelled services.")

    c1, c2, c3 = st.columns(3)
    gran = c1.selectbox("Granularity", GRANULARITIES, index=0, key="c_gran")
    month = c2.selectbox("Month", ["ALL"] + MONTHS, key="c_month")
    station = c3.selectbox("Station", queries.get_all_stations(), key="c_station")

    df = queries.get_station_cancellations(gran, month, station)
    if empty_guard(df):
        return

    kpi_row([
        ("Cancelled stops", f"{int(df['total_cancelled'].sum()):,}", None),
        ("Fully cancelled", f"{int(df['total_fully_cancelled'].sum()):,}", None),
        ("Partially cancelled", f"{int(df['total_partially_cancelled'].sum()):,}", None),
    ])

    left, right = st.columns(2)

    with left:
        st.subheader("Cancellations over time")
        trend = (
            df.groupby("time_period", as_index=False)[
                ["total_fully_cancelled", "total_partially_cancelled"]
            ].sum()
            .melt("time_period", var_name="Type", value_name="Count")
        )
        trend["Type"] = trend["Type"].map({
            "total_fully_cancelled": "Fully cancelled",
            "total_partially_cancelled": "Partially cancelled",
        })
        chart = (
            alt.Chart(trend)
            .mark_bar()
            .encode(
                x=time_axis(gran),
                y=alt.Y("Count:Q", title="Cancelled stops"),
                color=alt.Color("Type:N", title=None),
                tooltip=["time_period", "Type", "Count"],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)

    with right:
        st.subheader("Stations with most cancellations")
        top_n = st.slider("Top N", 5, 30, 10, key="c_topn")
        agg = (
            df.groupby("station_name", as_index=False)["total_cancelled"].sum()
            .nlargest(top_n, "total_cancelled")
        )
        chart = (
            alt.Chart(agg)
            .mark_bar()
            .encode(
                y=alt.Y("station_name:N", sort="-x", title=None),
                x=alt.X("total_cancelled:Q", title="Cancelled stops"),
                tooltip=["station_name", "total_cancelled"],
            )
            .properties(height=max(320, top_n * 28))
        )
        st.altair_chart(chart, use_container_width=True)

    st.dataframe(df, width="stretch",hide_index=True)


# ----------------------------------------------------------------------------
# REPORT 3: Service Reliability (get_service_reliability)
# ----------------------------------------------------------------------------
def render_service_reliability() -> None:
    st.header("Service Reliability")
    st.caption("Cancellation rate and delay for non-cancelled stops, grouped by service dimension.")

    c1, c2, c3, c4 = st.columns(4)
    level = c1.selectbox("Group by", SERVICE_LEVELS, key="r_level")
    company = c2.selectbox("Company", company_options(), key="r_company")
    stype = c3.selectbox("Service type", service_type_options(), key="r_stype")
    train = c4.selectbox("Train number", train_options(), key="r_train")

    df = queries.get_service_reliability(level, company, stype, train)
    if empty_guard(df):
        return

    kpi_row([
        ("Groups", f"{len(df):,}", None),
        ("Highest cancellation rate", fmt(df["cancellation_rate"].max(), "%"), None),
        ("Total cancelled stops", f"{int(df['total_cancelled_stops'].sum()):,}", None),
        ("Avg delay (non-cancelled)", fmt(df["avg_delay_trains"].mean(), " min"), None),
    ])

    left, right = st.columns(2)

    with left:
        st.subheader("Cancellation rate")
        top_n = st.slider("Top N", 5, 30, 10, key="r_topn")
        top = df.nlargest(top_n, "cancellation_rate")
        chart = (
            alt.Chart(top)
            .mark_bar()
            .encode(
                y=alt.Y("service_level:N", sort="-x", title=level),
                x=alt.X("cancellation_rate:Q", title="Cancellation rate (%)"),
                color=alt.Color("cancellation_rate:Q", legend=None,
                                scale=alt.Scale(scheme="reds")),
                tooltip=["service_level", "cancellation_rate",
                         "total_cancelled_stops", "cancellation_rank_rate"],
            )
            .properties(height=max(320, top_n * 28))
        )
        st.altair_chart(chart, use_container_width=True)

    with right:
        st.subheader("Share of cancelled stops")
        n_slices = min(top_n, 6)
        top = df.nlargest(n_slices, "total_cancelled_stops")[["service_level", "total_cancelled_stops"]]
        other = df["total_cancelled_stops"].sum() - top["total_cancelled_stops"].sum()
        if other > 0:
            top = pd.concat(
                [top, pd.DataFrame({"service_level": ["Other"], "total_cancelled_stops": [other]})],
                ignore_index=True,
            )
        chart = (
            alt.Chart(top)
            .mark_arc(innerRadius=60)
            .encode(
                theta=alt.Theta("total_cancelled_stops:Q"),
                color=alt.Color("service_level:N", title=level,
                                sort=top["service_level"].tolist()),
                tooltip=["service_level", "total_cancelled_stops"],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)

    st.dataframe(df, width="stretch",hide_index=True)


# ----------------------------------------------------------------------------
# REPORT 4: Service Related Delays (get_service_delays)
# ----------------------------------------------------------------------------
def render_service_related_delays() -> None:
    st.header("Most Delayed Services")
    st.caption("Average and extreme delays, plus severe-delay volume, per service dimension.")

    c1, c2, c3, c4 = st.columns(4)
    level = c1.selectbox("Group by", SERVICE_LEVELS, key="s_level")
    company = c2.selectbox("Company", company_options(), key="s_company")
    stype = c3.selectbox("Service type", service_type_options(), key="s_stype")
    train = c4.selectbox("Train number", train_options(), key="s_train")

    df = queries.get_service_delays("Monthly", level, company, stype, train)
    if empty_guard(df):
        return

    kpi_row([
        ("Avg arrival delay", fmt(df["avg_arrival_delay"].mean(), " min"), None),
        ("Avg departure delay", fmt(df["avg_departure_delay"].mean(), " min"), None),
        ("Max arrival delay", fmt(df["max_arrival_delay"].max(), " min", 0), None),
        ("Severe delays (>15 min)", f"{int(df['severe_delay_count'].sum()):,}", None),
    ])

    top_n = st.slider("Top N", 5, 13, 5, key="s_topn")
    left, right = st.columns(2)

    with left:
        st.subheader("Average delay")
        top = df.nlargest(top_n, "avg_arrival_delay")
        melted = top.melt(
            "service_level",
            value_vars=["avg_arrival_delay", "avg_departure_delay"],
            var_name="Type", value_name="Minutes",
        )
        melted["Type"] = melted["Type"].map({
            "avg_arrival_delay": "Arrival",
            "avg_departure_delay": "Departure",
        })
        chart = (
            alt.Chart(melted)
            .mark_bar()
            .encode(
                y=alt.Y("service_level:N", sort=top["service_level"].tolist(), title=level),
                x=alt.X("Minutes:Q", title="Avg delay (min)"),
                yOffset="Type:N",
                color=alt.Color("Type:N", title=None),
                tooltip=["service_level", "Type", alt.Tooltip("Minutes:Q", format=".2f")],
            )
            .properties(height=max(320, top_n * 34))
        )
        st.altair_chart(chart, use_container_width=True)

    with right:
        st.subheader("Severe delay volume")
        top = df.nlargest(top_n, "severe_delay_count")
        chart = (
            alt.Chart(top)
            .mark_bar(color="#d9534f")
            .encode(
                y=alt.Y("service_level:N", sort="-x", title=level),
                x=alt.X("severe_delay_count:Q", title="Stops delayed > 15 min"),
                tooltip=["service_level", "severe_delay_count",
                         "total_stops", "max_arrival_delay"],
            )
            .properties(height=max(320, top_n * 34))
        )
        st.altair_chart(chart, use_container_width=True)

    st.dataframe(df, width="stretch",hide_index=True)


REPORTS = {
    "Average Delays": render_avg_delay_report,
    "Station Cancellations": render_station_cancellations,
    "Service Reliability": render_service_reliability,
    "Most Delayed Services": render_service_related_delays,
}

# ----------------------------------------------------------------------------
# PAGE SHELL
# ----------------------------------------------------------------------------
st.title("Dutch Railway Analytical Report")
st.caption("OLAP report over the train-stop fact table: delays, cancellations and service reliability.")

tabs = st.tabs(list(REPORTS))
for tab, render in zip(tabs, REPORTS.values()):
    with tab:
        render()