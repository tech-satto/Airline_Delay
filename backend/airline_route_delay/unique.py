import pandas as pd

# Load dataset
df = pd.read_csv("flights2.csv")

# Create a unique flight ID combining airline + flight number
# df['UNIQUE_FLIGHT_ID'] = df['AIRLINE'].astype(str) + "-" + df['FLIGHT_NUMBER'].astype(str)

# Function to convert HHMM to minutes
def hhmm_to_minutes(hhmm):
    try:
        hhmm = int(hhmm)
        hours = hhmm // 100
        minutes = hhmm % 100
        return hours * 60 + minutes
    except:
        return pd.NA

# Function to convert minutes back to HHMM format
def minutes_to_hhmm(minutes):
    if pd.isna(minutes):
        return pd.NA
    minutes = int(round(minutes))
    hours = (minutes // 60) % 24
    mins = minutes % 60
    return f"{hours:02d}{mins:02d}"

# Convert HHMM columns to minutes
hhmm_cols = ["SCHEDULED_DEPARTURE", "DEPARTURE_TIME", "SCHEDULED_ARRIVAL", "ARRIVAL_TIME"]
for col in hhmm_cols:
    df[col + "_MINUTES"] = df[col].apply(hhmm_to_minutes)

# Define aggregation logic
agg_dict = {
    'DAY_OF_WEEK': lambda x: ','.join(sorted(map(str, sorted(x.unique())))),
    'AIRLINE': lambda x: x.mode()[0] if not x.mode().empty else None,
    'FLIGHT_NUMBER': lambda x: x.mode()[0] if not x.mode().empty else None,
    'TAIL_NUMBER': lambda x: x.mode()[0] if not x.mode().empty else None,
    'ORIGIN_AIRPORT': lambda x: x.mode()[0] if not x.mode().empty else None,
    'DESTINATION_AIRPORT': lambda x: x.mode()[0] if not x.mode().empty else None,
    'SCHEDULED_DEPARTURE_MINUTES': 'mean',
    'DEPARTURE_TIME_MINUTES': 'mean',
    'DEPARTURE_DELAY': 'mean',
    'TAXI_OUT': 'mean',
    'WHEELS_OFF': 'mean',
    'SCHEDULED_TIME': 'mean',
    'ELAPSED_TIME': 'mean',
    'AIR_TIME': 'mean',
    'DISTANCE': 'mean',
    'WHEELS_ON': 'mean',
    'TAXI_IN': 'mean',
    'SCHEDULED_ARRIVAL_MINUTES': 'mean',
    'ARRIVAL_TIME_MINUTES': 'mean',
    'ARRIVAL_DELAY': 'mean',
    'DIVERTED': 'mean',
    'CANCELLED': 'mean',
    'CANCELLATION_REASON': lambda x: x.mode()[0] if not x.mode().empty else None,
    'AIR_SYSTEM_DELAY': 'mean',
    'SECURITY_DELAY': 'mean',
    'AIRLINE_DELAY': 'mean',
    'LATE_AIRCRAFT_DELAY': 'mean',
    'WEATHER_DELAY': 'mean'
}

# Group by unique flight ID
agg_df = df.groupby("UNIQUE_FLIGHT_ID").agg(agg_dict).reset_index()

# Convert minutes back to HHMM for scheduled/actual times
agg_df['SCHEDULED_DEPARTURE'] = agg_df['SCHEDULED_DEPARTURE_MINUTES'].apply(minutes_to_hhmm)
agg_df['DEPARTURE_TIME'] = agg_df['DEPARTURE_TIME_MINUTES'].apply(minutes_to_hhmm)
agg_df['SCHEDULED_ARRIVAL'] = agg_df['SCHEDULED_ARRIVAL_MINUTES'].apply(minutes_to_hhmm)
agg_df['ARRIVAL_TIME'] = agg_df['ARRIVAL_TIME_MINUTES'].apply(minutes_to_hhmm)

# Drop intermediate minute columns
agg_df.drop(columns=[
    'SCHEDULED_DEPARTURE_MINUTES',
    'DEPARTURE_TIME_MINUTES',
    'SCHEDULED_ARRIVAL_MINUTES',
    'ARRIVAL_TIME_MINUTES'
], inplace=True)

# Round numeric columns for readability
numeric_cols = agg_df.select_dtypes(include=['float64']).columns
agg_df[numeric_cols] = agg_df[numeric_cols].round(2)

# Save to CSV
agg_df.to_csv("unique_flights.csv", index=False)

print("✅ unique_flights.csv created successfully!")
