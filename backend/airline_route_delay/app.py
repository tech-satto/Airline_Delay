from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
CORS(app)  # enable CORS so frontend can call APIs

# ========= Load dataset =========
try:
    df = pd.read_csv("unique_flights.csv")
except Exception as e:
    raise RuntimeError(f"Could not load dataset: {e}")

# ========= API 0: Get available dropdown options =========
@app.route("/available-options", methods=["GET"])
def available_options():
    airlines = df["AIRLINE"].dropna().unique().tolist()
    origins = df["ORIGIN_AIRPORT"].dropna().unique().tolist()
    destinations = df["DESTINATION_AIRPORT"].dropna().unique().tolist()

    return jsonify({
        "airlines": sorted(airlines),
        "origins": sorted(origins),
        "destinations": sorted(destinations)
    })

# ========= API 1: Airline Delay Stats =========
@app.route("/airline-delay-stats", methods=["GET"])
def airline_delay_stats():
    airline = request.args.get("airline")
    if not airline:
        return jsonify({"error": "Please provide an airline code"}), 400

    airline_df = df[df["AIRLINE"] == airline]
    if airline_df.empty:
        return jsonify({"error": "Airline not found"}), 404

    total_flights = len(airline_df)
    avg_arrival_delay = airline_df["ARRIVAL_DELAY"].mean()
    avg_departure_delay = airline_df["DEPARTURE_DELAY"].mean()

    # Delay causes
    delay_causes = {}
    for col in ["AIR_SYSTEM_DELAY", "SECURITY_DELAY", "AIRLINE_DELAY", "LATE_AIRCRAFT_DELAY", "WEATHER_DELAY"]:
        if col in airline_df.columns:
            delay_causes[col.lower()] = airline_df[col].mean()

    # Ranking logic
    airline_group = df.groupby("AIRLINE").agg(
        avg_arrival_delay=("ARRIVAL_DELAY", "mean"),
        avg_departure_delay=("DEPARTURE_DELAY", "mean")
    ).reset_index()

    airline_group["rank_by_arrival"] = airline_group["avg_arrival_delay"].rank(method="min")
    airline_group["rank_by_departure"] = airline_group["avg_departure_delay"].rank(method="min")

    this_airline = airline_group[airline_group["AIRLINE"] == airline].iloc[0]

    response = {
        "airline": airline,
        "total_flights": int(total_flights),
        "avg_arrival_delay": round(avg_arrival_delay, 2),
        "avg_departure_delay": round(avg_departure_delay, 2),
        "delays_by_cause": {k: round(v, 2) for k, v in delay_causes.items()},
        "ranking": {
            "rank_by_arrival_delay": int(this_airline["rank_by_arrival"]),
            "rank_by_departure_delay": int(this_airline["rank_by_departure"]),
            "total_airlines": int(airline_group.shape[0])
        }
    }
    return jsonify(response)

# ========= API 2: Route Performance =========
@app.route("/route-performance", methods=["GET"])
def route_performance():
    origin = request.args.get("origin")
    destination = request.args.get("destination")
    airline = request.args.get("airline")  # NEW LINE

    if not origin or not destination:
        return jsonify({
            "error": "Please provide origin and destination, e.g., /route-performance?origin=JFK&destination=LAX"
        }), 400

    route_data = df[
        (df["ORIGIN_AIRPORT"] == origin) &
        (df["DESTINATION_AIRPORT"] == destination)
    ]
    if airline:  # If airline filter is provided
        route_data = route_data[route_data["AIRLINE"] == airline]

    if route_data.empty:
        return jsonify({"error": f"No data found for route {origin} -> {destination}"}), 404

    # Count airlines on this route (without airline filter)
    num_airlines = df[
        (df["ORIGIN_AIRPORT"] == origin) &
        (df["DESTINATION_AIRPORT"] == destination)
    ]["AIRLINE"].nunique()

    route_stats = {
        "total_flights": int(len(route_data)),
        "avg_arrival_delay": round(route_data["ARRIVAL_DELAY"].mean(), 2),
        "avg_departure_delay": round(route_data["DEPARTURE_DELAY"].mean(), 2),
        "num_airlines": int(num_airlines),  # NEW
        "delay_distribution": {
            "0-15min": int(((route_data["ARRIVAL_DELAY"] <= 15) & (route_data["ARRIVAL_DELAY"] > 0)).sum()),
            "15-60min": int(((route_data["ARRIVAL_DELAY"] > 15) & (route_data["ARRIVAL_DELAY"] <= 60)).sum()),
            "60+min": int((route_data["ARRIVAL_DELAY"] > 60).sum())
        }
    }
    return jsonify(route_stats)

# ========= Run App =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
