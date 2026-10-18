import pytest
from sqlalchemy import create_engine, text

TEST_DB_URL = "mysql+pymysql://root:password@localhost:3306/dutch_railway_test"

@pytest.fixture(scope="session")
def db_engine():
    """Create a persistent engine for the test session."""
    engine = create_engine(TEST_DB_URL)
    
    # Setup test schema (or seed dim/fact tables)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_station (
                station_key INT PRIMARY KEY,
                station_name VARCHAR(255)
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_date (
                date_key INT PRIMARY KEY,
                year INT,
                month_name VARCHAR(50),
                day INT
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS fact_train_stop (
                stop_id INT PRIMARY KEY,
                station_key INT,
                date_key INT,
                arrival_delay FLOAT,
                departure_delay FLOAT,
                arrival_cancelled INT
            );
        """))
    
    yield engine

    # Teardown: Clean up test tables after tests finish
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS fact_train_stop;"))
        conn.execute(text("DROP TABLE IF EXISTS dim_station;"))
        conn.execute(text("DROP TABLE IF EXISTS dim_date;"))

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provides a transactional database session per test function, rolling back changes after."""
    connection = db_engine.connect()
    transaction = connection.begin()
    
    yield connection
    
    transaction.rollback()
    connection.close()