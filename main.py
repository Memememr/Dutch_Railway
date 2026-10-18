import streamlit as st
import database

st.set_page_config(
    page_title="Dutch Railway OLAP Dashboard",
    layout="wide",
    page_icon = "train-icon.png"
)

# Overall Delays and Cancaellations
def get_avg_cancellation_report(time_granularity, selected_month):
    time_column = {
            "Yearly": "d.year",
            "Quarterly": "d.quarter",
            "Monthly": "d.month_name",
            "Weekly": "d.week_number",
            "Daily": "d.day",
        }.get(time_granularity, "d.month_name")

## base query --- Average time of train delays
    query = f"""
    SELECT
        {time_column} AS time_period,
            station_name,
            AVG(f.arrival_delay) AS arrival_delay,
            AVG(f.departure_delay) AS departure_delay,
        FROM fact_train_stop AS f
        JOIN dim_date AS d ON f.date_key = d.date_key
        JOIN dim_station AS s ON f.station_key = s.station_key
        WHERE 1=1
    """
    #        JOIN station AS st ON f.station_key = st.station_key
    #        JOIN service AS se ON f.service_key = se.service_key

    # insert params on WHERE
    params = {}

    if selected_month != "ALL" :
        query += " AND d.month_name= :month"
        params["month"] = str(selected_month)

    query += f" GROUP BY {time_column}, station_name ORDER by time_period ASC"

    return database.run_query(query, params)


# top 5 stations with most cancellations




## User Interface 
st.title("Dutch Railway Analytics Dashboard", icon = ":material/cable_car:" )
st.header("Arrival and Delay Analysis")
st.markdown("Analyze average arrival and departure delays across temporal granularities.")


time_granularity = st.segmented_control(
            "Time Period:",
            options=["Yearly", "Quarterly", "Monthly", "Weekly", "Daily"],
            selection_mode="single"
        )
        
selected_month = st.selectbox(
            "Month Filter:",
            options=["ALL", "January", "February", "March", "April", "May", "June", 
                    "July", "August", "September", "October", "November", "December"]
        )



st.dataframe(get_avg_cancellation_report(time_granularity, selected_month))