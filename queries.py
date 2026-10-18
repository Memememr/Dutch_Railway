import database

# Overall Delays and Cancaellations
def get_avg_cancellation_report(time_granularity = "Monthly", selected_month = "ALL"):
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
            AVG(f.departure_delay) AS departure_delay
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


#2.  Stations with most departure cancellations
def get_station_cancellations():

    query = f"""
    SElECT st.station_name
    FROM fact_train_stop f
    JOIN dim_station st ON f.station_key = st.station_key
    GROUP BY station_name
    """

# 3. Service type and company reliability

def get_service_company_reliability():
    query = f"""
    SELECT 
    FROM fact_train_stop
    JOIN fact train stop
    GROUP BY
    """




# 4. Services that have the most delays 

