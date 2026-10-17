import streamlit as st




st.set_page_config(
    page_title="Dutch Railway OLAP Dashboard",
    layout="wide",
)

## Database Connection
def get_db_connection():
    return st.connection("mysql",type = "sql")

## OLAP Query
def get_OLAP_report(time_granularity, selected_year):
    conn = get_db_connection()

    time_column = {
            "Yearly": "d.year",
            "Quarterly": "d.quarter",
            "Monthly": "d.month_name",
            "Weekly": "d.week_number",
            "Daily": "d.day",
        }.get(time_granularity, "d.year")

## base query --- Number of train delays
    query = f"""
    SELECT
        {time_column} AS time_period,
            AVG(f.arrival_delay) AS arrival_delay,
            AVG(f.departure_delay) AS departure_delay,
            AVG(f.arrival_cancelled) AS arrival_cancelled,
            AVG(f.departure_cancelled) AS departure_cancelled
        FROM fact_train_stop AS f
        JOIN dim_date AS d ON f.date_key = d.date_key
        WHERE 1=1
    """
    #        JOIN station AS st ON f.station_key = st.station_key
    #        JOIN service AS se ON f.service_key = se.service_key

    # insert params on WHERE
    params = {}

    if selected_year != "ALL" :
        query += "AND d.year= :year"
        params["year"] = int(selected_year)

    query += f" GROUP BY {time_column} ORDER by time_period ASC"

    return conn.query(query, params=params)

## User Interface 
st.title("Dutch Railway Analytics Dashboard")

report_type = st.sidebar.selectbox(
    "Select Granularity",
    ["Yearly", "Quarterly", "Monthly", "Weekly", "Daily"],
)
year = st.sidebar.selectbox("Select Year", ["ALL", 2025, 2024, 2023])

# Data Display
df = get_OLAP_report(report_type, year)

if not df.empty:
    st.dataframe(df, use_container_width=True)
    st.line_chart(df, x="time_period", y="arrival_delay")
else:
    st.warning("No records found.")

