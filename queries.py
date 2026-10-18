import database

# Overall Delays and Cancaellations
def get_avg_cancellation_report(time_granularity = "Monthly", selected_month = "ALL", selected_station="ALL"):
    time_column = {
            "Yearly": "d.year",
            "Quarterly": "d.quarter",
            "Monthly": "d.month_name",
            "Weekly": "d.week_number",
            "Daily": "d.day",
        }.get(time_granularity, "d.month_name")

    where_clauses = ["1=1"] 
    params = {}

    if selected_month != "ALL":
        where_clauses.append("d.month_name = :month")
        params["month"] = str(selected_month)

    if selected_station != "ALL":
        where_clauses.append("s.station_name = :station")
        params["station"] = str(selected_station)

    where_sql = " AND ".join(where_clauses)

## base query --- Average time of train delays
    query = f"""
    WITH average_delay_time AS(
    SELECT 
        {time_column} AS 
            time_period,
            s.station_name,
            AVG(f.arrival_delay) AS arrival_delay,
            AVG(f.departure_delay) AS departure_delay,
            SUM(CASE WHEN f.arrival_delay > 15 THEN 1 ELSE 0 END) AS severe_issues
        FROM fact_train_stop AS f
        JOIN dim_date AS d ON f.date_key = d.date_key
        JOIN dim_station AS s ON f.station_key = s.station_key
        WHERE {where_sql}
        GROUP BY {time_column}, s.station_name
    )
    SELECT 
        time_period,
        station_name,
        arrival_delay,
        departure_delay,
        severe_issues,

        DENSE_RANK() OVER (PARTITION BY time_period ORDER BY arrival_delay DESC) AS arrival_delay_rank,
        DENSE_RANK() OVER (PARTITION BY time_period ORDER BY departure_delay DESC) AS dep_delay_rank,
        ROUND(AVG(arrival_delay) OVER (PARTITION BY time_period), 2) AS benchmark_arrival,
        ROUND(AVG(departure_delay) OVER (PARTITION BY time_period), 2) AS benchmark_departure
        FROM average_delay_time
        ORDER BY time_period ASC;
    """
    return database.run_query(query, params)


#2.  Stations with most departure cancellations
def get_station_cancellations():

    query = f"""
    SElECT st.station_name
    FROM fact_train_stop f
    JOIN dim_station st ON f.station_key = st.station_key
    GROUP BY station_name
    """

    params = {}

    return database.run(query)

# 3. Service cancellation rate

def get_service_cancellation(service_level="Company", company="ALL", service_type="ALL", train="ALL"):

    time_column = {
            "Company":"se.company_name",
            "Service Type":"se.service_level",
            "Train Number": "se.train_number"
        }.get(service_level, "se.company_name")

    where_clauses = ["1=1"]
    params = {}

    if company != "ALL":
        where_clauses.append("se.company_name = :company")
        params["company"] = str(company)

    if service_type != "ALL":
        where_clauses.append("se.service_type = :service_type")
        params["service_type"] = str(service_type)

    if service_type != "ALL":
            where_clauses.append("se.train_number = :train")
            params["train_number"] = str(train)

    # Combine all active filter clauses into one SQL snippet ({where_sql})
    where_sql = " AND ".join(where_clauses)


    query = f"""
    WITH service_level_cancellation AS (
        SELECT 
            {service_level} AS service_level,
            
            -- Absolute Cancellation Count
            SUM(CASE WHEN f.arrival_cancelled = 1 OR f.departure_cancelled = 1 THEN 1 ELSE 0 END) AS total_cancelled_stops,
            
            -- Average Delay for Non-Cancelled Trains
            ROUND(AVG(CASE WHEN f.arrival_cancelled = 0 THEN f.arrival_delay END), 2) AS avg_delay_trains,
            
            -- Cancellation Rate Percentage
            ROUND(
                (SUM(CASE WHEN f.arrival_cancelled = 1 OR f.departure_cancelled = 1 THEN 1 ELSE 0 END) * 100.0) 
                / COUNT(f.train_stop_key), 2
            ) AS cancellation_rate
        FROM fact_train_stop AS f
        JOIN dim_service AS se ON f.service_key = se.service_key
        WHERE {where_sql}
        GROUP BY {service_level}
    ) 
    SELECT
        service_level,
        total_cancelled_stops,
        avg_delay_trains,
        cancellation_rate,

        -- Window Functions: Rank service levels across the network without PARTITION BY
        DENSE_RANK() OVER (ORDER BY total_cancelled_stops DESC) AS total_cancel_rank,
        DENSE_RANK() OVER (ORDER BY cancellation_rate DESC) AS cancellation_rank_rate
    FROM service_level_cancellation
    ORDER BY cancellation_rate DESC;
    """

    return database.run_query(query, params)
    




# 4. Services that have the most delays 

