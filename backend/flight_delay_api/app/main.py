from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.model_utils import preprocess_input, suggest_alternatives

app = FastAPI(title="Flight Delay Predictor API")

# Enable CORS - Always add this for frontend-backend compatibility!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev, allow everything. For production, set your frontend URL.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FlightRequest(BaseModel):
    date: str
    airline: str
    origin: str
    destination: str
    sched_departure: int

@app.get("/")
def root():
    return {"message": "Flight Delay API is running!"}

@app.post("/predict")
def predict_delay(flight: FlightRequest):
    prob_delay = preprocess_input(
        flight_date=flight.date,
        airline=flight.airline,
        origin=flight.origin,
        destination=flight.destination,
        sched_departure=flight.sched_departure
    )
    alternatives = suggest_alternatives(flight.dict())
    response_prob = round(prob_delay, 2) if isinstance(prob_delay, float) else prob_delay
    return {
        "flight": flight.dict(),
        "prob_delay": response_prob,
        "delay_probability": response_prob,            # <-- CRUCIAL for your JS!
        "alternative_flights": alternatives
    }
