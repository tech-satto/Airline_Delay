import pandas as pd
import sqlite3

# Load parquet
df = pd.read_parquet("flights_2015_lite.parquet")

# Save into SQLite
conn = sqlite3.connect("flights.db")
df.to_sql("flights", conn, if_exists="replace", index=False)
conn.close()

print("✅ flights.db created successfully")
