import pytest
from sqlalchemy import create_engine, text

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    conn = engine.connect()
    
    conn.execute(text("CREATE TABLE dim_station (station_key INT, station_name TEXT);"))
    conn.execute(text("CREATE TABLE dim_date (date_key INT, year INT, month_name TEXT, day INT);"))
    conn.execute(text("CREATE TABLE dim_service (service_key INT, company TEXT, service_type TEXT, train_number TEXT);"))
    conn.execute(text("""
        CREATE TABLE fact_train_stop (
            stop_id INT, station_key INT, date_key INT, service_key INT,
            arrival_delay REAL, departure_delay REAL, 
            arrival_cancelled INT, departure_cancelled INT,
            service_completely_cancelled INT, service_partly_cancelled INT
        );
    """))
    
    yield conn
    conn.close()

def seed_sample_data(connection):
    connection.execute(text("INSERT INTO dim_station VALUES (1, 'Amsterdam Centraal'), (2, 'Utrecht Centraal');"))
    connection.execute(text("INSERT INTO dim_date VALUES (101, 2026, 'January', 1), (102, 2026, 'January', 2);"))
    connection.execute(text("INSERT INTO dim_service VALUES (1, 'NS', 'Intercity', '1234');"))
    
    # Insert test data: 3 normal stops + 1 fully cancelled stop
    connection.execute(text("""
        INSERT INTO fact_train_stop (
            stop_id, station_key, date_key, service_key, 
            arrival_delay, departure_delay, 
            arrival_cancelled, departure_cancelled, 
            service_completely_cancelled, service_partly_cancelled
        )
        VALUES 
            (1, 1, 101, 1, 10.0, 5.0, 0, 0, 0, 0),
            (2, 1, 101, 1, 20.0, 15.0, 0, 0, 0, 0),
            (3, 2, 101, 1, 5.0,  2.0, 0, 0, 0, 0),
            (4, 2, 101, 1, 0.0,  0.0, 1, 1, 1, 0);
    """))