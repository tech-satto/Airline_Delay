# chatbot_server.py
import os, re
from typing import Dict, Any
from datetime import datetime
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser as dateparser

# ---- Load lite analytics data (required) ----
DATA_PATH = "artifacts/flights_2015_lite.parquet"
DF = pd.read_parquet(DATA_PATH).copy()
DF["DELAYED_15"] = (DF["ARRIVAL_DELAY"] > 15).astype(int)
DF["DEP_HOUR"]   = (DF["SCHEDULED_DEPARTURE"] // 100).clip(0, 23)

# ---- Optional: load ML model + encoders if you get them later ----
MODEL, ENCODERS = None, None
try:
    import joblib
    if os.path.exists("artifacts/model.pkl") and os.path.exists("artifacts/encoders.pkl"):
        MODEL    = joblib.load("artifacts/model.pkl")
        ENCODERS = joblib.load("artifacts/encoders.pkl")  # {"AIRLINE":..., "ORIGIN_AIRPORT":..., "DESTINATION_AIRPORT":...}
except Exception:
    MODEL, ENCODERS = None, None

# ---- Precomputed historical backoffs (fast) ----
g1 = DF.groupby(["AIRLINE","ORIGIN_AIRPORT","DESTINATION_AIRPORT","MONTH","DEP_HOUR"])["DELAYED_15"].mean()
g2 = DF.groupby(["AIRLINE","ORIGIN_AIRPORT","DESTINATION_AIRPORT","DEP_HOUR"])["DELAYED_15"].mean()
g3 = DF.groupby(["ORIGIN_AIRPORT","DESTINATION_AIRPORT","DEP_HOUR"])["DELAYED_15"].mean()
g4 = DF.groupby(["ORIGIN_AIRPORT","DESTINATION_AIRPORT"])["DELAYED_15"].mean()
g5 = DF.groupby(["ORIGIN_AIRPORT","DEP_HOUR"])["DELAYED_15"].mean()
g6 = DF.groupby(["DESTINATION_AIRPORT","DEP_HOUR"])["DELAYED_15"].mean()
g7 = DF.groupby(["DEP_HOUR"])["DELAYED_15"].mean()
g8 = DF["DELAYED_15"].mean()

def dep_hour_from_hhmm(hhmm: int) -> int:
    try: return int(hhmm)//100
    except: return 0

def parse_free_text(txt: str) -> Dict[str,Any]:
    t = txt.strip()
    out = {}
    m_air = re.search(r"\b([A-Z]{2})\b", t.upper())
    if m_air: out["airline"] = m_air.group(1)
    codes = re.findall(r"\b[A-Z]{3}\b", t.upper())
    if len(codes)>=2:
        out["origin"], out["destination"] = codes[0], codes[1]
    m_time = re.search(r"(\d{1,2}):(\d{2})(\s*[ap]m)?", t, re.I)
    if m_time:
        hh, mm = int(m_time.group(1)), int(m_time.group(2))
        ampm = (m_time.group(3) or "").lower()
        if "pm" in ampm and hh < 12: hh += 12
        if "am" in ampm and hh == 12: hh = 0
        out["sched_departure"] = hh*100 + mm
    try:
        d = dateparser.parse(t, default=datetime(2015,1,1))
        out["date"] = d.strftime("%Y-%m-%d")
        out["month"] = d.month
        out["day_of_week"] = d.isoweekday()
    except Exception:
        pass
    return out

def historical_probability(airline, origin, dest, month, dep_hour) -> float:
    k1 = (airline, origin, dest, month, dep_hour)
    k2 = (airline, origin, dest, dep_hour)
    k3 = (origin, dest, dep_hour)
    k4 = (origin, dest)
    k5 = (origin, dep_hour)
    k6 = (dest, dep_hour)
    if k1 in g1.index: return float(g1.loc[k1])
    if k2 in g2.index: return float(g2.loc[k2])
    if k3 in g3.index: return float(g3.loc[k3])
    if k4 in g4.index: return float(g4.loc[k4])
    if k5 in g5.index: return float(g5.loc[k5])
    if k6 in g6.index: return float(g6.loc[k6])
    return float(g7.loc[dep_hour]) if dep_hour in g7.index else float(g8)

def model_probability(payload: Dict[str,Any]) -> float:
    dt = dateparser.parse(payload["date"])
    month = dt.month
    dep_hour = dep_hour_from_hhmm(int(payload["sched_departure"]))
    ctx = {
        "MONTH": month,
        "DAY": dt.day,
        "DAY_OF_WEEK": dt.isoweekday(),
        "AIRLINE": str(payload["airline"]).upper(),
        "ORIGIN_AIRPORT": str(payload["origin"]).upper(),
        "DESTINATION_AIRPORT": str(payload["destination"]).upper(),
        "DEP_HOUR": dep_hour
    }
    # If a real model + encoders are present, use them
    if MODEL is not None and ENCODERS is not None:
        X = pd.DataFrame([ctx])
        for c in ["AIRLINE","ORIGIN_AIRPORT","DESTINATION_AIRPORT"]:
            le = ENCODERS[c]
            val = X[c].iloc[0]
            X[c] = le.transform([val])[0] if val in le.classes_ else 0
        # distance (route mean fallback)
        dist = DF[(DF["ORIGIN_AIRPORT"]==ctx["ORIGIN_AIRPORT"]) &
                  (DF["DESTINATION_AIRPORT"]==ctx["DESTINATION_AIRPORT"])]["DISTANCE"].mean()
        if pd.isna(dist): dist = DF["DISTANCE"].mean()
        X["DISTANCE"] = float(dist)
        feats = ["MONTH","DAY","DAY_OF_WEEK","AIRLINE","ORIGIN_AIRPORT","DESTINATION_AIRPORT","DEP_HOUR","DISTANCE"]
        X = X[feats]
        proba = float(MODEL.predict_proba(X)[:,1][0])
        return proba
    # otherwise, historical backoff
    return historical_probability(ctx["AIRLINE"], ctx["ORIGIN_AIRPORT"], ctx["DESTINATION_AIRPORT"], ctx["MONTH"], ctx["DEP_HOUR"])

# ---- FastAPI app ----
app = FastAPI(title="Flight Chatbot", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatIn(BaseModel):
    message: str
    context: Dict[str,Any] = {}

class ChatOut(BaseModel):
    reply: str
    intent: str
    context: Dict[str,Any] = {}
    actions: Dict[str,Any] = {}

def route_intent(text:str)->str:
    t = text.lower()
    if any(w in t for w in ["predict", "probability", "chance", "will my flight"]): return "PREDICT"
    if "explain" in t or "why" in t: return "EXPLAIN"
    if any(w in t for w in ["worst origin", "airport delays", "by airport"]): return "ANALYTICS_ORIGIN"
    if any(w in t for w in ["airline delays", "by airline"]): return "ANALYTICS_AIRLINE"
    if "by hour" in t or "time of day" in t: return "ANALYTICS_HOUR"
    if "routes" in t or "city pair" in t: return "ANALYTICS_ROUTE"
    if "parse" in t: return "PARSE"
    if "help" in t: return "HELP"
    return "UNKNOWN"

def run_analytics(intent:str)->str:
    df = DF
    if intent=="ANALYTICS_ORIGIN":
        ans = (df.groupby("ORIGIN_AIRPORT")["DELAYED_15"].mean()*100).round(1).sort_values(ascending=False).head(10)
        return "Worst origin airports (top 10):\n" + ans.astype(str).add("%").to_string()
    if intent=="ANALYTICS_AIRLINE":
        ans = (df.groupby("AIRLINE")["DELAYED_15"].mean()*100).round(1).sort_values(ascending=False).head(10)
        return "Worst airlines by delay rate (top 10):\n" + ans.astype(str).add("%").to_string()
    if intent=="ANALYTICS_HOUR":
        ans = (df.groupby("DEP_HOUR")["DELAYED_15"].mean()*100).round(1)
        return "Delay rate by departure hour:\n" + ans.astype(str).add("%").to_string()
    tmp = df.copy()
    tmp["ROUTE"] = tmp["ORIGIN_AIRPORT"] + "→" + tmp["DESTINATION_AIRPORT"]
    ans = (tmp.groupby("ROUTE")["DELAYED_15"].mean()*100).round(1).sort_values(ascending=False).head(10)
    return "Worst routes (top 10):\n" + ans.astype(str).add("%").to_string()

@app.post("/chat", response_model=ChatOut)
def chat(req: ChatIn):
    msg = req.message.strip()
    ctx = dict(req.context or {})
    intent = route_intent(msg)

    if intent=="PARSE":
        fields = parse_free_text(msg)
        ctx.update(fields)
        return ChatOut(reply=f"Parsed fields: {fields}. Now say 'predict' to get probability.",
                       intent="PARSE", context=ctx)

    if intent=="PREDICT":
        needed = ["date","airline","origin","destination","sched_departure"]
        if not all(k in ctx for k in needed):
            ctx.update({k:v for k,v in parse_free_text(msg).items() if v is not None})
        if not all(k in ctx for k in needed):
            return ChatOut(reply="Please provide: airline (IATA), origin (IATA), destination (IATA), date (YYYY-MM-DD), time (HH:MM). "
                                 "Example: 'predict AA ATL to LAX 2015-06-15 13:30'",
                           intent="HELP", context=ctx)
        proba = model_probability(ctx)
        try:
            dt = dateparser.parse(ctx["date"])
            ctx["month"] = dt.month
        except: pass
        ctx["dep_hour"] = dep_hour_from_hhmm(int(ctx["sched_departure"]))
        ctx["last_delay_probability"] = proba
        reply = f"Delay probability: {proba*100:.1f}%. On-time probability: {(1-proba)*100:.1f}%. Say 'explain' for a short reason."
        return ChatOut(reply=reply, intent="PREDICT", context=ctx,
                       actions={"delay_probability": proba, "ontime_probability": 1-proba})

    if intent=="EXPLAIN":
        p = ctx.get("last_delay_probability")
        if p is None:
            return ChatOut(reply="Predict first, then I can explain. Try: 'predict AA ATL to LAX 2015-06-15 13:30'",
                           intent="HELP", context=ctx)
        airline = ctx.get("airline","?"); origin = ctx.get("origin","?"); dest = ctx.get("destination","?")
        month = ctx.get("month","?"); hour = ctx.get("dep_hour","?")
        text = (f"Estimated delay risk is {float(p):.0%} for {airline} {origin}→{dest} "
                f"(month {month}, hour {hour}). Recommendation: try earlier departures, "
                f"buffer connections, or alternate airports on this route/time.")
        return ChatOut(reply=text, intent="EXPLAIN", context=ctx)

    if intent in ["ANALYTICS_ORIGIN","ANALYTICS_AIRLINE","ANALYTICS_HOUR","ANALYTICS_ROUTE"]:
        return ChatOut(reply=run_analytics(intent), intent="ANALYTICS", context=ctx)

    help_text = ("I can:\n"
                 "• Predict delay: 'predict AA ATL to LAX 2015-06-15 13:30'\n"
                 "• Explain the prediction: 'explain'\n"
                 "• Analytics: 'worst origin airports', 'airline delays', 'delay by hour', 'worst routes'\n"
                 "• Parse free text: 'parse AA tomorrow 1:30pm ATL to LAX'\n")
    return ChatOut(reply=help_text, intent="HELP", context=ctx)
