import streamlit as st

def run_query(query: str, params: dict = None):
    conn = st.connection("mysql", type="sql")
    df = conn.query(query, params=params)
    return df


# 1. Overall Delays
def get_avg_delay_report(granularity="Monthly", month="ALL", company="ALL", station="ALL"):
    date_column = {
        "Yearly": "d.year",
        "Quarterly": "d.quarter",
        "Monthly": "d.month_name",
        "Weekly": "d.week_number",
        "Daily": "d.day",
    }.get(granularity, "d.month_name")

    where_clauses = ["1=1"] 
    params = {}

    if month != "ALL":
        where_clauses.append("d.month_name = :month")
        params["month"] = str(month)

    if station != "ALL":
        where_clauses.append("s.station_name = :station")
        params["station"] = str(station)

    if company != "ALL":
        where_clauses.append("se.company_name = :company")
        params["company"] = str(company)

    where_sql = " AND ".join(where_clauses)

    query = f"""
    WITH average_delay_time AS (
        SELECT 
            {date_column} AS time_period,
            s.station_name,
            ROUND(AVG(f.arrival_delay), 2) AS arrival_delay,
            ROUND(AVG(f.departure_delay), 2) AS departure_delay,
            SUM(CASE WHEN f.arrival_delay > 15 THEN 1 ELSE 0 END) AS severe_issues
        FROM fact_train_stop AS f
        JOIN dim_date AS d ON f.date_key = d.date_key
        JOIN dim_station AS s ON f.station_key = s.station_key
        JOIN dim_service AS se ON f.service_key = se.service_key
        WHERE {where_sql}
        GROUP BY {date_column}, s.station_name
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
    return run_query(query, params)


# 2. Cancellations in a station at a certain time
def get_station_cancellations(granularity="Yearly", month="ALL", station="ALL"):
    date_column = {
        "Yearly": "d.year",
        "Quarterly": "d.quarter",
        "Monthly": "d.month_name",
        "Weekly": "d.week_number",
        "Daily": "d.day",
    }.get(granularity, "d.year")
    
    where_clauses = ["1=1"] 
    params = {}
    
    if month != "ALL":
        where_clauses.append("d.month_name = :month")
        params["month"] = str(month)
    
    if station != "ALL":
        where_clauses.append("st.station_name = :station")
        params["station"] = str(station)
    
    where_sql = " AND ".join(where_clauses)

    query = f"""
    WITH station_cancellation AS (
        SELECT 
            {date_column} AS time_period,
            st.station_name AS station_name,
            
            -- Total Cancelled Stops (Arrival OR Departure)
            SUM(CASE WHEN f.arrival_cancelled = 1 OR f.departure_cancelled = 1 THEN 1 ELSE 0 END) AS total_cancelled,
            
            -- Full vs Partial Service Failures
            SUM(CASE WHEN f.service_completely_cancelled = 1 THEN 1 ELSE 0 END) AS total_fully_cancelled,
            SUM(CASE WHEN f.service_partly_cancelled = 1 THEN 1 ELSE 0 END) AS total_partially_cancelled
        FROM fact_train_stop AS f
        JOIN dim_station AS st ON f.station_key = st.station_key
        JOIN dim_date AS d ON f.date_key = d.date_key
        WHERE {where_sql}
        GROUP BY {date_column}, st.station_name
    )
    SELECT
        time_period,
        station_name,
        total_cancelled,
        total_fully_cancelled,
        total_partially_cancelled,

        -- Window Functions: Rank within time period
        DENSE_RANK() OVER (PARTITION BY time_period ORDER BY total_cancelled DESC) AS total_cancelled_rank,
        DENSE_RANK() OVER (PARTITION BY time_period ORDER BY total_fully_cancelled DESC) AS fully_cancelled_rank
    FROM station_cancellation
    ORDER BY time_period ASC, total_cancelled_rank ASC;
    """
    return run_query(query, params)


# 3. Service cancellation rate
def get_service_reliability(service_level="Company", company="ALL", service_type="ALL", train="ALL"):
    service_column = {
        "Company": "se.company_name",
        "Service Type": "se.service_level",
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

    if train != "ALL":
        where_clauses.append("se.train_number = :train")
        params["train"] = str(train)

    where_sql = " AND ".join(where_clauses)

    query = f"""
    WITH service_level_cancellation AS (
        SELECT 
            {service_column} AS service_level,
            
            -- Absolute Cancellation Count
            SUM(CASE WHEN f.arrival_cancelled = 1 OR f.departure_cancelled = 1 THEN 1 ELSE 0 END) AS total_cancelled_stops,
            
            -- Average Delay for Non-Cancelled Trains
            ROUND(AVG(CASE WHEN f.arrival_cancelled = 0 THEN f.arrival_delay END), 2) AS avg_delay_trains,
            
            -- Cancellation Rate Percentage
            ROUND(
                (SUM(CASE WHEN f.arrival_cancelled = 1 OR f.departure_cancelled = 1 THEN 1 ELSE 0 END) * 100.0) 
                / COUNT(*), 2
            ) AS cancellation_rate
        FROM fact_train_stop AS f
        JOIN dim_service AS se ON f.service_key = se.service_key
        WHERE {where_sql}
        GROUP BY {service_column}
    ) 
    SELECT
        service_level,
        total_cancelled_stops,
        avg_delay_trains,
        cancellation_rate,

        -- Window Functions: Rank service levels across network
        DENSE_RANK() OVER (ORDER BY total_cancelled_stops DESC) AS total_cancel_rank,
        DENSE_RANK() OVER (ORDER BY cancellation_rate DESC) AS cancellation_rank_rate
    FROM service_level_cancellation
    ORDER BY cancellation_rate DESC;
    """
    return run_query(query, params)


# 4. Service-related delays
def get_service_delays(granularity="Monthly", service_level="Company", company="ALL", service_type="ALL", train="ALL"):    
    service_column = {
        "Company": "se.company_name",
        "Service Type": "se.service_level",
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

    if train != "ALL":
        where_clauses.append("se.train_number = :train")
        params["train"] = str(train)

    where_sql = " AND ".join(where_clauses)

    query = f"""
    WITH service_delay_summary AS (
        SELECT 
            {service_column} AS service_level,
                
            -- Average Delays
            ROUND(AVG(f.arrival_delay), 2) AS avg_arrival_delay,
            ROUND(AVG(f.departure_delay), 2) AS avg_departure_delay,
                
            -- Extreme Delays
            MAX(f.arrival_delay) AS max_arrival_delay,
                
            -- Severe Delay Volume (> 15 mins)
            SUM(CASE WHEN f.arrival_delay > 15 THEN 1 ELSE 0 END) AS severe_delay_count,
                
            -- Total Stops Evaluated
            COUNT(*) AS total_stops
        FROM fact_train_stop AS f
        JOIN dim_service AS se ON f.service_key = se.service_key
        WHERE {where_sql}
        GROUP BY {service_column}
    ) 
    SELECT
        service_level,
        avg_arrival_delay,
        avg_departure_delay,
        max_arrival_delay,
        severe_delay_count,
        total_stops,

        -- Window Functions: Rank service levels by delay severity
        DENSE_RANK() OVER (ORDER BY avg_arrival_delay DESC) AS avg_delay_rank,
        DENSE_RANK() OVER (ORDER BY severe_delay_count DESC) AS severe_delay_rank
    FROM service_delay_summary
    ORDER BY avg_arrival_delay DESC;
    """
    return run_query(query, params)