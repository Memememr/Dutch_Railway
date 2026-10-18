import pytest
import pandas as pd
import queries
from conftest import seed_sample_data

@pytest.fixture(autouse=True)
def mock_run_query(db_session, monkeypatch):
    """
    Intercept calls to queries.run_query so Streamlit's st.connection() 
    is bypassed completely during tests.
    """
    def _mock_run_query(query: str, params: dict = None):
        from sqlalchemy import text
        return pd.read_sql_query(text(query), db_session, params=params)
    
    monkeypatch.setattr(queries, "run_query", _mock_run_query)


# -------------------------------------------------------------------
# 1. Tests for get_avg_delay_report
# -------------------------------------------------------------------

def test_avg_delay_report_overall(db_session):
    """Verify network-wide daily aggregations when station='ALL'."""
    seed_sample_data(db_session)
    
    df = queries.get_avg_delay_report(date_granularity="Daily", month="ALL", company="ALL", station="ALL")
    
    assert not df.empty, "Query returned no rows"
    assert "arrival_delay" in df.columns
    assert "benchmark_arrival" in df.columns
    # Overall average arrival delay: (10 + 20 + 5) / 3 = 11.67
    assert round(df["arrival_delay"].mean(), 2) == 11.67


def test_avg_delay_report_station_filter(db_session):
    """Verify exact values when filtered to 'Amsterdam Centraal'."""
    seed_sample_data(db_session)
    
    df = queries.get_avg_delay_report(date_granularity="Daily", month="ALL", company="ALL", station="Amsterdam Centraal")
    
    # Amsterdam average arrival delay: (10 + 20) / 2 = 15.00
    assert len(df) == 1
    assert df.iloc[0]["station_name"] == "Amsterdam Centraal"
    assert df.iloc[0]["arrival_delay"] == 15.00


# -------------------------------------------------------------------
# 2. Tests for get_station_cancellations
# -------------------------------------------------------------------

def test_station_cancellations_all(db_session):
    """Verify cancellation metrics across all stations."""
    seed_sample_data(db_session)
    
    df = queries.get_station_cancellations(granularity="Daily", month="ALL", station="ALL")
    
    assert not df.empty
    assert "total_cancelled" in df.columns
    assert "total_fully_cancelled" in df.columns
    assert "total_partially_cancelled" in df.columns

    # From seeded data: stop_id 4 in Utrecht was fully cancelled
    utrecht_row = df[df["station_name"] == "Utrecht Centraal"]
    assert len(utrecht_row) == 1
    assert utrecht_row.iloc[0]["total_cancelled"] == 1
    assert utrecht_row.iloc[0]["total_fully_cancelled"] == 1


def test_station_cancellations_filter(db_session):
    """Verify cancellation counts when filtered by station."""
    seed_sample_data(db_session)
    
    df = queries.get_station_cancellations(granularity="Daily", month="ALL", station="Amsterdam Centraal")
    
    assert len(df) == 1
    assert df.iloc[0]["station_name"] == "Amsterdam Centraal"
    assert df.iloc[0]["total_cancelled"] == 0


# -------------------------------------------------------------------
# 3. Tests for get_service_reliability
# -------------------------------------------------------------------

def test_service_reliability_company_level(db_session):
    """Verify cancellation rate and delay aggregations aggregated by company."""
    seed_sample_data(db_session)
    
    df = queries.get_service_reliability(service_level="Company", company="ALL", service_type="ALL", train="ALL")
    
    assert not df.empty
    assert "cancellation_rate" in df.columns
    assert "avg_delay_trains" in df.columns

    # NS has 4 total stops, 1 cancelled -> (1 / 4) * 100 = 25.00%
    ns_row = df[df["service_level"] == "NS"]
    assert len(ns_row) == 1
    assert ns_row.iloc[0]["cancellation_rate"] == 25.00


def test_service_reliability_filter_by_company(db_session):
    """Verify service reliability filtered by specific company."""
    seed_sample_data(db_session)
    
    df = queries.get_service_reliability(service_level="Company", company="NS", service_type="ALL", train="ALL")
    
    assert len(df) == 1
    assert df.iloc[0]["service_level"] == "NS"


# -------------------------------------------------------------------
# 4. Tests for get_service_delays
# -------------------------------------------------------------------

def test_service_delays_company_level(db_session):
    """Verify delay severity metrics aggregated by service level."""
    seed_sample_data(db_session)
    
    df = queries.get_service_delays(granularity="Monthly", service_level="Company", company="ALL", service_type="ALL", train="ALL")
    
    assert not df.empty
    assert "avg_arrival_delay" in df.columns
    assert "max_arrival_delay" in df.columns
    assert "severe_delay_count" in df.columns

    # From seeded data: stop_id 2 has arrival_delay 20.0 (> 15 mins)
    ns_row = df[df["service_level"] == "NS"]
    assert len(ns_row) == 1
    assert ns_row.iloc[0]["max_arrival_delay"] == 20.0
    assert ns_row.iloc[0]["severe_delay_count"] == 1


# -------------------------------------------------------------------
# Shared / Edge Case Tests
# -------------------------------------------------------------------

def test_query_returns_empty_on_invalid_filter(db_session):
    """Verify query functions return empty DataFrames on non-matching filters."""
    seed_sample_data(db_session)
    
    df = queries.get_avg_delay_report(date_granularity="Daily", month="NonExistentMonth", station="ALL")
    
    assert df is None or df.empty