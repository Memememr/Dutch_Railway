import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st
import os

# Removed hardcoded database credentials.
# Make own secrets.toml file and fill your own credentials
# See .streamlit/secrets.toml.example



CSV_FILE = os.path.join("data", "dutch_railway_raw.csv")

# Load credentials from .streamlit/secrets.toml
# For any use of special characters in the password
db_conf = st.secrets["mysql"]
DB_URI = f"mysql+pymysql://{db_conf['user']}:{db_conf['password']}@{db_conf['host']}:{db_conf['port']}/{db_conf['database']}"
engine = create_engine(DB_URI)

with engine.begin() as conn:
    # Temporarily disable foreign keys to allow truncating referenced tables
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))  
    conn.execute(text("TRUNCATE TABLE fact_train_stop;"))
    conn.execute(text("TRUNCATE TABLE dim_station;"))
    conn.execute(text("TRUNCATE TABLE dim_service;"))
    conn.execute(text("TRUNCATE TABLE dim_date;"))
    conn.execute(text("TRUNCATE TABLE dim_time;"))
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

print("\nExisting tables entries deleted and auto-increments reset.\n")

raw_df = pd.read_csv(CSV_FILE)
print(f"Dutch Railway Dataset loaded: '{CSV_FILE}'")
print(f"Entries extracted: {len(raw_df):,}\n")


# Auditing initial columns, you can enable this triple quoted section
# to see the unique values of each column in the original dataset.

'''
for col in raw_df.columns:
    uniques = raw_df[col].unique()
    try:
        sorted_uniques = sorted(uniques.tolist(), key=lambda x: (x is None, x))
    except TypeError:
        sorted_uniques = uniques.tolist()
        
    print(f"Attribute Field: '{col}'")
    print(f"  ├─ Storage Data Type:   {raw_df[col].dtype}")
    print(f"  ├─ Unique Value Count:  {len(uniques):,}")
    print(f"  └─ Distinct Values:     {sorted_uniques}")
    print("-" * 80 + "\n")
'''

cleaned_df = raw_df.copy()

# String Cleanups

cleaned_df['Service:RDT-ID'] = cleaned_df['Service:RDT-ID'].astype(str).str.strip()
cleaned_df['Stop:RDT-ID'] = cleaned_df['Stop:RDT-ID'].astype(str).str.strip()
cleaned_df['Service:Type'] = cleaned_df['Service:Type'].astype(str).str.strip().str.title()
cleaned_df['Service:Train number'] = cleaned_df['Service:Train number'].astype(str).str.strip()

# Station code and name have some unknown values, standardize them to UNK and Unknown respectively
cleaned_df['Stop:Station code'] = cleaned_df['Stop:Station code'].fillna('UNK').astype(str).str.strip().str.upper()
cleaned_df['Stop:Station name'] = cleaned_df['Stop:Station name'].fillna('Unknown').astype(str).str.strip()

# In company, notice that '200' is present, this is a FlixTrain service, so standardize it as such.
# Will keep searching if this is persistent with how Dutch Railway documents companies.
cleaned_df['Service:Company'] = cleaned_df['Service:Company'].astype(str).str.strip()
company_mapping = {'200': 'FlixTrain'}
cleaned_df['Service:Company'] = cleaned_df['Service:Company'].replace(company_mapping)

# Date and Time Standardization
cleaned_df['Service:Date'] = pd.to_datetime(cleaned_df['Service:Date'], format='%Y-%m-%d', errors='coerce')
cleaned_df['Stop:Arrival time'] = pd.to_datetime(cleaned_df['Stop:Arrival time'], utc=True, errors='coerce')
cleaned_df['Stop:Departure time'] = pd.to_datetime(cleaned_df['Stop:Departure time'], utc=True, errors='coerce')

# Standardizing null values for delays in minutes to 0, and converting to integer for loading into the table.
numeric_cols = ['Stop:Arrival delay', 'Stop:Departure delay', 'Service:Maximum delay']
for col in numeric_cols:
    if col in cleaned_df.columns:
        cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce').fillna(0).astype(int)

# Handles boolean columns to have unified TRUE and FALSE values.
bool_cols = [
    'Service:Completely cancelled',
    'Service:Partly cancelled',
    'Stop:Arrival cancelled',
    'Stop:Departure cancelled'
]
for col in bool_cols:
    if col in cleaned_df.columns:
        cleaned_df[col] = cleaned_df[col].astype(str).str.upper().isin(['TRUE', '1', '1.0'])

# dim_date table true to the schema
unique_dates = pd.Series(cleaned_df['Service:Date'].dropna().unique()).sort_values()
dim_date = pd.DataFrame({
    'date_key': unique_dates.dt.strftime('%Y%m%d').astype(int),
    'full_date': unique_dates.dt.date,
    'day': unique_dates.dt.day,
    'day_of_week': unique_dates.dt.day_name(),
    'week_number': unique_dates.dt.isocalendar().week.astype(int),
    'month': unique_dates.dt.month,
    'month_name': unique_dates.dt.month_name(),
    'quarter': unique_dates.dt.quarter,
    'year': unique_dates.dt.year,
    'is_weekend': unique_dates.dt.dayofweek >= 5
})

# dim_station table true to the schema
dim_station_raw = cleaned_df[['Stop:Station code', 'Stop:Station name']].drop_duplicates().dropna()
dim_station = pd.DataFrame({
    'station_code': dim_station_raw['Stop:Station code'],
    'station_name': dim_station_raw['Stop:Station name']
}).reset_index(drop=True)

# dim_service table true to the schema
dim_service_raw = cleaned_df[['Service:Train number', 'Service:Type', 'Service:Company']].drop_duplicates().dropna()
dim_service = pd.DataFrame({
    'train_number': dim_service_raw['Service:Train number'],
    'service_type': dim_service_raw['Service:Type'],
    'company': dim_service_raw['Service:Company']
}).reset_index(drop=True)

# dim_time table true to the schema
time_range = pd.date_range("00:00", "23:59", freq="min")
dim_time = pd.DataFrame({
    'time_key': time_range.strftime('%H%M%S').astype(int),
    'full_time': time_range.time,
    'hour': time_range.hour,
    'minute': time_range.minute,
    'time_period': pd.cut(
        time_range.hour, 
        bins=[-1, 5, 11, 16, 21, 24], 
        labels=['Night', 'Morning', 'Afternoon', 'Evening', 'Night'], 
        ordered=False
    )
})

# Load dimension tables into the database
with engine.begin() as conn:
    dim_date.to_sql('dim_date', con=conn, if_exists='append', index=False)

    dim_station.to_sql('dim_station', con=conn, if_exists='append', index=False)

    dim_service.to_sql('dim_service', con=conn, if_exists='append', index=False)

    dim_time.to_sql('dim_time', con=conn, if_exists='append', index=False)

# Fetch surrogate keys generated by MySQL AUTO_INCREMENT
with engine.connect() as conn:
    db_dim_station = pd.read_sql("SELECT station_key, station_code FROM dim_station", con=conn)
    db_dim_service = pd.read_sql("SELECT service_key, train_number, service_type, company FROM dim_service", con=conn)

# Fact table assembly
fact_df = cleaned_df.copy()

# Date Key Mapping
fact_df['date_key'] = fact_df['Service:Date'].dt.strftime('%Y%m%d').astype(int)

# Earlier problems were seen with formatting of time values, this ensures keys exactly match integer HHMMSS format.
# Handling of null values is done by re-aligning the series with the original index and assigning None to NaNs.
fact_df['arrival_time_key'] = (
    fact_df['Stop:Arrival time']
    .dt.strftime('%H%M%S')
    .dropna()
    .astype(int)
)

fact_df['arrival_time_key'] = fact_df['arrival_time_key'].reindex(fact_df.index)
fact_df['arrival_time_key'] = fact_df['arrival_time_key'].astype(object).where(fact_df['arrival_time_key'].notnull(), None)

fact_df['departure_time_key'] = (
    fact_df['Stop:Departure time']
    .dt.strftime('%H%M%S')
    .dropna()
    .astype(int)
)
fact_df['departure_time_key'] = fact_df['departure_time_key'].reindex(fact_df.index)
fact_df['departure_time_key'] = fact_df['departure_time_key'].astype(object).where(fact_df['departure_time_key'].notnull(), None)

# Lookup surrogate keys for station and service dimensions
fact_df = fact_df.merge(
    db_dim_station, 
    left_on='Stop:Station code', 
    right_on='station_code', 
    how='left'
)

fact_df = fact_df.merge(
    db_dim_service, 
    left_on=['Service:Train number', 'Service:Type', 'Service:Company'], 
    right_on=['train_number', 'service_type', 'company'], 
    how='left'
)

# Final fact table assembly
fact_table = pd.DataFrame({
    'date_key': fact_df['date_key'],
    'station_key': fact_df['station_key'],
    'service_key': fact_df['service_key'],
    'arrival_time_key': fact_df['arrival_time_key'],
    'departure_time_key': fact_df['departure_time_key'],
    'service_rdt_id': fact_df['Service:RDT-ID'],
    'stop_rdt_id': fact_df['Stop:RDT-ID'],
    'arrival_delay': fact_df['Stop:Arrival delay'],
    'departure_delay': fact_df['Stop:Departure delay'],
    'arrival_cancelled': fact_df['Stop:Arrival cancelled'],
    'departure_cancelled': fact_df['Stop:Departure cancelled'],
    'service_maximum_delay': fact_df['Service:Maximum delay'],
    'service_completely_cancelled': fact_df['Service:Completely cancelled'],
    'service_partly_cancelled': fact_df['Service:Partly cancelled'],
    'stop_count': 1
})

# Auditing final columns, you can enable this triple quoted section
# to see the unique values of each column in the fact and dimension tbales/

'''
def print_full_entity_audit(entity_name, df, columns_to_audit=None):
    print(f"--- [{entity_name.upper()} ENTITY AUDIT] ---")
    print(f"Total Record Count: {len(df):,}")
    
    cols = columns_to_audit if columns_to_audit else df.columns
    for col in cols:
        uniques = df[col].unique()
        try:
            sorted_uniques = sorted(uniques.tolist(), key=lambda x: (x is None, x))
        except TypeError:
            sorted_uniques = uniques.tolist()
            
        print(f"Attribute Field: '{col}'")
        print(f"  ├─ Storage Data Type:   {df[col].dtype}")
        print(f"  ├─ Total Unique Count:  {len(uniques):,}")
        print(f"  └─ Full Uniques List:\n     {sorted_uniques}")
        print("-" * 75)
    print("\n")


# 1. dim_date table
print_full_entity_audit("dim_date", dim_date)

# 2. dim_time table
print_full_entity_audit("dim_time", dim_time)

# 3. dim_station table
print_full_entity_audit("dim_station", dim_station)

# 4. dim_service table
print_full_entity_audit("dim_service", dim_service)

# 5. fact_train_stop table
fact_target_cols = [
    'arrival_cancelled', 
    'departure_cancelled', 
    'service_completely_cancelled', 
    'service_partly_cancelled',
    'arrival_delay', 
    'departure_delay', 
    'service_maximum_delay'
]
print_full_entity_audit("fact_train_stop", fact_table)
'''

with engine.begin() as conn:
    print(f"Loading entries into 'fact_train_stop' {len(fact_table):,} rows\n")
    fact_table.to_sql('fact_train_stop', con=conn, if_exists='append', index=False, chunksize=10000)

print("ETL pipeline completed, Go ahead and check the database! Good luck!")