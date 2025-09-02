import pandas as pd
import datetime
import joblib
from xgboost import XGBClassifier
from .config import DATA_PATH, MODEL_PATH, ENCODER_PATH

# Load dataset, but use only 40%
def get_sampled_df():
    full_df = pd.read_csv(DATA_PATH, low_memory=False)
    return full_df.sample(frac=0.4, random_state=42).reset_index(drop=True)

# Load XGBoost model
xgb_model = XGBClassifier()
xgb_model.load_model(MODEL_PATH)

# Load LabelEncoders
le_dict = joblib.load(ENCODER_PATH)

# ... rest of your code unchanged ...

def preprocess_input(flight_date, airline, origin, destination, sched_departure):
    """Return probability of delay for a single flight."""
    date_obj = datetime.datetime.strptime(flight_date, "%Y-%m-%d")
    month = date_obj.month
    day = date_obj.day
    day_of_week = date_obj.isoweekday()

    # Load sampled dataframe lazily
    df = get_sampled_df()

    # Distance lookup
    distance = df[(df["ORIGIN_AIRPORT"]==origin) & (df["DESTINATION_AIRPORT"]==destination)]["DISTANCE"].mean()
    distance = int(distance) if not pd.isna(distance) else int(df["DISTANCE"].mean())

    input_df = pd.DataFrame({
        "MONTH": [month],
        "DAY": [day],
        "DAY_OF_WEEK": [day_of_week],
        "AIRLINE": [airline],
        "FLIGHT_NUMBER": [0],  # dummy
        "ORIGIN_AIRPORT": [origin],
        "DESTINATION_AIRPORT": [destination],
        "SCHEDULED_DEPARTURE": [sched_departure],
        "DISTANCE": [distance]
    })

    # Encode categorical
    for col in ["AIRLINE", "ORIGIN_AIRPORT", "DESTINATION_AIRPORT"]:
        input_df[col] = input_df[col].astype(str)
        le = le_dict[col]
        input_df[col] = le.transform(input_df[col]) if input_df[col].iloc[0] in le.classes_ else 0

    prob_delay = xgb_model.predict_proba(input_df)[:,1][0]
    return float(prob_delay)

def suggest_alternatives(user_input, top_n=5):
    origin = user_input["origin"]
    dest = user_input["destination"]
    date_str = user_input["date"]

    # Load sampled dataframe lazily
    df = get_sampled_df()

    candidates = df[(df["ORIGIN_AIRPORT"]==origin) & (df["DESTINATION_AIRPORT"]==dest)]
    if len(candidates) > 20:
        candidates = candidates.sample(20, random_state=42)

    results = []
    for _, row in candidates.iterrows():
        prob_delay = preprocess_input(
            flight_date=date_str,
            airline=row["AIRLINE"],
            origin=row["ORIGIN_AIRPORT"],
            destination=row["DESTINATION_AIRPORT"],
            sched_departure=row["SCHEDULED_DEPARTURE"]
        )
        results.append({
            "airline": row["AIRLINE"],
            "departure": row["SCHEDULED_DEPARTURE"],
            "prob_delay": float(round(prob_delay, 2))
        })

    results = sorted(results, key=lambda x: x["prob_delay"])[:top_n]
    return results
