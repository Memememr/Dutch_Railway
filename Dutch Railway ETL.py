from datetime import date, time
import pandas as pd
from sqlalchemy import create_engine, text


# Note: Hi! To use this ETL script with your database (MySQL), edit the confugations below if needed:
MYSQL_USER = "root"
MYSQL_PASSWORD = "20241217"                          
MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
# Name is set by the schema itself
MYSQL_DATABASE = "train_dw"                  

CSV_FILE = "dutch_railway_raw.csv"

# For any use of special characters in the password
DB_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
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
cleaned_df['Service:Train number'] = cleaned_df['Service:Train number'].astype(str).str.strip()

# Station code and name have some unknown values, standardize them to UNK and Unknown respectively
cleaned_df['Stop:Station code'] = cleaned_df['Stop:Station code'].fillna('UNK').astype(str).str.strip().str.upper()
cleaned_df['Stop:Station name'] = cleaned_df['Stop:Station name'].fillna('Unknown').astype(str).str.strip()

# Standardizing company names
# In company, notice that there are companies reffered to as numeric codes.
# After further research, I stumbled upon a list of Dutch Railway companies and their corresponding codes.
# Codes are here: https://reisinformatiegroep.nl/ndovloket/Data/DownloadDocumentation/2
# All unnecessary spaces are removed with casing preserved as is as some companies have their full names while others have initials.
cleaned_df['Service:Company'] = cleaned_df['Service:Company'].astype(str).str.strip()
company_mapping = {
    # Mapping numeric codes to corresponding company names
    # Note however, that there are some codes not in the list so it's left as is
    '3': 'BBA',
    '12': 'SBM',
    '14': 'Novio',
    '15': 'Oad',
    '20': 'Stadsvervoer Oss',
    '21': 'Stadsvervoer Nederland',
    '22': 'GVB',
    '23': 'HTM',
    '24': 'Ret',
    '25': 'GVU',
    '26': 'Wagenborg',
    '27': 'Teso',
    '28': 'Rederij NACO',
    '29': 'Waterbus',
    '30': 'Provinciale Stoombootdiensten',
    '36': 'Svd',
    '37': 'R-net',
    '41': 'Largo Recorrido Renfe',
    '46': 'Limex',
    '47': 'Rederij Doeksen',
    '50': 'Veren (OVR)',
    '51': 'Arr.- Breng',
    '52': 'Breng',
    '53': 'Mti',
    '54': 'Valleilijn',
    '55': 'Blauwnet',
    '56': 'Eurobahn',
    '056': 'Eurobahn',
    '58': 'RRReis',
    '60': 'ABRN',
    '61': 'VIAS',
    '83': 'Ferrovie dello Stato',
    '100': 'NS',
    '200': 'NS International',
    '210': 'European Sleeper',
    '310': 'EETC',
    '400': 'Syntus',
    '500': 'Arriva',
    '501': 'Hermes',
    '600': 'Connexxion',
    '750': 'Qbuzz',
    '751': 'U-OV',
    '803': 'Arriva Noord',
    '806': 'Noordned (OVR)',
    '850': 'STENA',
    '900': 'British Rail',
    '910': 'DB',
    '911': 'Keolis',
    '920': 'NMBS',
    '930': 'Danske Statsbaner',
    '940': 'Schweizerische Bundesbahn',
    '941': 'Zwitserland Smallspoor',
    '942': 'ceske drahy',
    '950': 'Oestereichische Bahn',
    '951': 'Eurostar',
    '960': 'Overig Internationaal',
    '962': 'Locon Benelux',
    '970': 'Chemins de Fer Luxembourg',
    '980': 'Franse Spoorwegen',

    # Umbrella companies mapped to main company name 
    'Blauwnet A': 'Blauwnet',
    'Blauwnet K': 'Blauwnet',
    'RRReis A': 'RRReis',
    'RRReis K': 'RRReis',
    'R-net NS': 'R-net',
    'R-net Qb': 'R-net',

    # Standardizing company names
    'Deutsche B': 'DB',
    'EB': 'Eurobahn',
    'Eu Sleeper': 'European Sleeper',
    'NS Int': 'NS International',
    'TCS OV': 'TCS',

    # Existing companies mapped to themselves for when other services are added, consistency is ensured.
    'Arriva': 'Arriva',
    'Blauwnet': 'Blauwnet',
    'Breng': 'Breng',
    'Chemins de Fer Luxembourg': 'Chemins de Fer Luxembourg',
    'DB': 'DB',
    'Eurobahn': 'Eurobahn',
    'Keolis': 'Keolis',
    'NMBS': 'NMBS',
    'NS': 'NS',
    'NS International': 'NS International',
    'R-net': 'R-net',
    'RRReis': 'RRReis',
    'TCS': 'TCS',
    'VIAS': 'VIAS'
}
cleaned_df['Service:Company'] = cleaned_df['Service:Company'].replace(company_mapping)


# Standardizing service types
# All are title case and have unnecessary spaces removed.
cleaned_df['Service:Type'] = cleaned_df['Service:Type'].astype(str).str.strip().str.title()
service_type_mapping = {
    # Same service so mapping to one name for consistency
    'Ice': 'Ice International',
    
    # Existing services mapped to themselves for when other services are needed, consistency is ensured.
    'Belbus Ipv Trein': 'Belbus Ipv Trein',
    'Bus': 'Bus',
    'Eurocity': 'Eurocity',
    'Eurocity Direct': 'Eurocity Direct',
    'European Sleeper': 'European Sleeper',
    'Eurostar': 'Eurostar',
    'Ice International': 'Ice International',
    'Int. Trein': 'Int. Trein',
    'Intercity': 'Intercity',
    'Intercity Direct': 'Intercity Direct',
    'Metro Ipv Trein': 'Metro Ipv Trein',
    'Nachttrein': 'Nachttrein',
    'Nightjet': 'Nightjet',
    'Ov-Bus Ipv Trein': 'Ov-Bus Ipv Trein',
    'Snelbus Ipv Trein': 'Snelbus Ipv Trein',
    'Sneltrein': 'Sneltrein',
    'Sprinter': 'Sprinter',
    'Stopbus Ipv Trein': 'Stopbus Ipv Trein',
    'Stoptrein': 'Stoptrein',
    'Taxibus Ipv Trein': 'Taxibus Ipv Trein'
}

cleaned_df['Service:Type'] = cleaned_df['Service:Type'].replace(service_type_mapping)

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
unknown_date_row = pd.DataFrame([{
    'date_key': -1,
    'full_date': date(1000, 1, 1),
    'day': -1,
    'day_of_week': 'N/A',
    'week_number': -1,
    'month': -1,
    'month_name': 'N/A',
    'quarter': -1,
    'year': -1,
    'is_weekend': False
}])

dim_date = pd.concat([unknown_date_row, dim_date], ignore_index=True)

# dim_station table true to the schema & accounting for unknown station keys
dim_station_raw = cleaned_df[['Stop:Station code', 'Stop:Station name']].drop_duplicates(subset=['Stop:Station code']).dropna()

unknown_station_row = pd.DataFrame([{
    'station_code': 'UNK',
    'station_name': 'Unknown Station'
}])

dim_station = pd.concat([
    unknown_station_row, 
    pd.DataFrame({
        'station_code': dim_station_raw['Stop:Station code'],
        'station_name': dim_station_raw['Stop:Station name']
    })
], ignore_index=True)

# dim_service table true to the schema & accounting for unknown service keys 
dim_service_raw = cleaned_df[['Service:Train number', 'Service:Type', 'Service:Company']].drop_duplicates().dropna()

unknown_service_row = pd.DataFrame([{
    'train_number': 'UNK',
    'service_type': 'Unknown',
    'company': 'Unknown'
}])

dim_service = pd.concat([
    unknown_service_row,
    pd.DataFrame({
        'train_number': dim_service_raw['Service:Train number'],
        'service_type': dim_service_raw['Service:Type'],
        'company': dim_service_raw['Service:Company']
    })
], ignore_index=True)

# dim_time table true to the schema
time_range = pd.date_range("00:00", "23:59", freq="min")

dim_time = pd.DataFrame({
    'time_key': time_range.strftime('%H%M%S').astype(int),
    'full_time': time_range.time,
    'hour': time_range.hour,
    'minute': time_range.minute,
    'time_period': pd.Series(
        pd.cut(
            time_range.hour, 
            bins=[-1, 5, 11, 16, 21, 24], 
            labels=['Late Night', 'Morning', 'Afternoon', 'Evening', 'Night'], 
            ordered=False
        )
    ).astype(str).replace({'Late Night': 'Night'})
})

unknown_time_row = pd.DataFrame([{
    'time_key': -1,
    'full_time': time(0, 0, 0),
    'hour': -1,
    'minute': -1,
    'time_period': 'N/A'
}])

dim_time = pd.concat([unknown_time_row, dim_time], ignore_index=True)

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

# Date and Time Mapping
# Handling of null values done by filling with -1 to represent unknown times in the fact table.
fact_df['date_key'] = (
    fact_df['Service:Date']
    .dt.strftime('%Y%m%d')
    .fillna('-1')
    .astype('int64')
)

# Earlier problems were seen with formatting of time values, this ensures keys exactly match integer HHMMSS format.
fact_df['arrival_time_key'] = (
    fact_df['Stop:Arrival time']
    .dt.strftime('%H%M00')
    .fillna('-1')
    .astype('int64')
)

fact_df['departure_time_key'] = (
    fact_df['Stop:Departure time']
    .dt.strftime('%H%M00')
    .fillna('-1')
    .astype('int64')
)

# Lookup surrogate keys for station and service dimensions
fact_df = fact_df.merge(
    db_dim_station, 
    left_on='Stop:Station code', 
    right_on='station_code', 
    how='left'
)

# Numeric value, station key: handling of null values done by filling with -1 to represent unknown station keys
fact_df['station_key'] = fact_df['station_key'].fillna('-1').astype('int64')

fact_df = fact_df.merge(
    db_dim_service, 
    left_on=['Service:Train number', 'Service:Type', 'Service:Company'], 
    right_on=['train_number', 'service_type', 'company'], 
    how='left'
)

# Numeric value, service key: handling of null values done by filling with -1 to represent unknown service keys
fact_df['service_key'] = fact_df['service_key'].fillna('-1').astype('int64')

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
# to see the first 1000 unique values of each column in the fact and dimension tables

'''
def print_full_entity_audit(entity_name, df, columns_to_audit=None, max_uniques_to_print=1000):
    print(f"--- [{entity_name.upper()} ENTITY AUDIT] ---")
    print(f"Total Record Count: {len(df):,}")
    
    cols = columns_to_audit if columns_to_audit else df.columns
    for col in cols:
        uniques = df[col].unique()
        unique_count = len(uniques)
        
        print(f"Attribute Field: '{col}'")
        print(f"  ├─ Storage Data Type:   {df[col].dtype}")
        print(f"  ├─ Total Unique Count:  {unique_count:,}")
        
        # Filter: Only print the list if unique entries are strictly under threshold
        if unique_count < max_uniques_to_print:
            try:
                sorted_uniques = sorted(uniques.tolist(), key=lambda x: (x is None, str(x)))
            except TypeError:
                sorted_uniques = uniques.tolist()
            print(f"  └─ Full Uniques List:\n     {sorted_uniques}")
        else:
            print(f"  └─ Full Uniques List:   [SUPPRESSED - Exceeds {max_uniques_to_print:,} entries]")
            
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
print_full_entity_audit("fact_train_stop", fact_table, columns_to_audit=fact_target_cols)
'''

with engine.begin() as conn:
    print(f"Loading entries into 'fact_train_stop' {len(fact_table):,} rows\n")
    fact_table.to_sql('fact_train_stop', con=conn, if_exists='append', index=False, chunksize=10000)

print("ETL pipeline completed, Go ahead and check the database! Good luck!")
