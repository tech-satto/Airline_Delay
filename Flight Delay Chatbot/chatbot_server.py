import os
from openai import OpenAI
import google.generativeai as genai


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Setup both APIs
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

def ask_llm(prompt: str) -> (str, str):
    """Ask LLM: prefer OpenAI, fallback to Gemini. Returns (reply, provider)."""
    # --- Try OpenAI first ---
    if client.api_key:
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful flight assistant chatbot."},
                    {"role": "user", "content": prompt}
                ]
            )
            return resp.choices[0].message.content, "OpenAI"
        except Exception as e:
            print("OpenAI failed:", e)

    # --- Fallback: Gemini ---
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(prompt)
        return resp.text, "Gemini"
    except Exception as e:
        return f"LLM error: {e}", "Error"



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
DATA_PATH = "flights_2015_lite.parquet"
DF = pd.read_parquet(DATA_PATH).copy()
DF["DELAYED_15"] = (DF["ARRIVAL_DELAY"] > 15).astype(int)
DF["DEP_HOUR"]   = (DF["SCHEDULED_DEPARTURE"] // 100).clip(0, 23)

# ✅ NEW: Valid codes from dataset
VALID_AIRPORTS = set(DF["ORIGIN_AIRPORT"].unique()) | set(DF["DESTINATION_AIRPORT"].unique())
VALID_AIRLINES = set(DF["AIRLINE"].unique())

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

# ---- Lookup tables for airlines & airports ----
AIRLINE_NAMES = {
    "AA": "American Airlines Inc.",
    "DL": "Delta Air Lines Inc.",
    "UA": "United Airlines Inc.",
    "WN": "Southwest Airlines Co.",
    "B6": "JetBlue Airways",
    "NK": "Spirit Air Lines",
    "F9": "Frontier Airlines Inc.",
    "VX": "Virgin America",
    "US": "US Airways Inc.",
    "EV": "Atlantic Southeast Airlines",
    "HA": "Hawaiian Airlines Inc.",
    "OO": "SkyWest Airlines Inc.",
    "AS": "Alaska Airlines Inc.",
    "MQ": "American Eagle Airlines Inc."
}

AIRPORT_NAMES = {
    "ATL": "Hartsfield–Jackson Atlanta International Airport",
    "LAX": "Los Angeles International Airport",
    "ORD": "Chicago O'Hare International Airport",
    "DFW": "Dallas/Fort Worth International Airport",
    "DEN": "Denver International Airport",
    "JFK": "John F. Kennedy International Airport",
    "SFO": "San Francisco International Airport",
    "LAS": "McCarran International Airport",
    "CLT": "Charlotte Douglas International Airport",
    "MIA": "Miami International Airport"
}

def pretty_airline(code: str) -> str:
    return AIRLINE_NAMES.get(code, code)

def pretty_airport(code: str) -> str:
    return AIRPORT_NAMES.get(code, code)


def dep_hour_from_hhmm(hhmm: int) -> int:
    try: return int(hhmm)//100
    except: return 0

# ✅ FIXED parse_free_text()
def parse_free_text(txt: str) -> Dict[str, Any]:
    t = txt.strip()
    out = {}

    # Airline (must be valid)
    m_air = re.findall(r"\b([A-Z0-9]{2})\b", t.upper())
    if m_air:
        for cand in m_air:
            if cand in VALID_AIRLINES:
                out["airline"] = cand
                break

    # Origin + Destination (must be valid airports)
    codes = [c for c in re.findall(r"\b[A-Z]{3}\b", t.upper()) if c in VALID_AIRPORTS]
    if len(codes) >= 2:
        out["origin"], out["destination"] = codes[0], codes[1]

    # Date (YYYY-MM-DD)
    m_date = re.search(r"(\d{4}-\d{2}-\d{2})", t)
    if m_date:
        out["date"] = m_date.group(1)

    # Time (HH:MM with optional am/pm)
    m_time = re.search(r"(\d{1,2}):(\d{2})(\s*[ap]m)?", t, re.I)
    if m_time:
        hh, mm = int(m_time.group(1)), int(m_time.group(2))
        ampm = (m_time.group(3) or "").lower()
        if "pm" in ampm and hh < 12: hh += 12
        if "am" in ampm and hh == 12: hh = 0
        out["sched_departure"] = hh * 100 + mm

    # Add month + weekday
    if "date" in out:
        try:
            d = dateparser.parse(out["date"])
            out["month"] = d.month
            out["day_of_week"] = d.isoweekday()
        except:
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

def suggest_alternatives(ctx: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
    """
    Suggest lower-risk options for the same route & month based on historical delay rates
    grouped by (AIRLINE, DEPARTURE_HOUR). No ML required.
    """
    origin = ctx.get("origin")
    dest   = ctx.get("destination")
    date   = ctx.get("date")
    dep    = ctx.get("sched_departure")

    # Need core fields first
    if not all([origin, dest, date, dep]):
        return {
            "reply": "To suggest alternatives, I need origin, destination, date and time. "
                     "Try a predict first (e.g., 'predict AA ATL to LAX 2015-06-15 13:30').",
            "intent": "ALTERNATIVES",
            "context": ctx,
            "actions": {}
        }

    # Derive month/hour
    try:
        dt = dateparser.parse(date)
        month = dt.month
    except Exception:
        month = ctx.get("month")
    dep_hour = ctx.get("dep_hour") or dep_hour_from_hhmm(int(dep))

    # Same route + same month (seasonality)
    cand = df[(df["ORIGIN_AIRPORT"] == origin) &
              (df["DESTINATION_AIRPORT"] == dest) &
              (df["MONTH"] == month)].copy()

    if cand.empty:
        return {
            "reply": f"No historical flights found for {origin}->{dest} in month {month}. Try a different month/route.",
            "intent": "ALTERNATIVES",
            "context": ctx,
            "actions": {}
        }

    cand["DEPARTURE_HOUR"] = (cand["SCHEDULED_DEPARTURE"] // 100).clip(0, 23).astype(int)
    cand["DELAYED_15"] = (cand["ARRIVAL_DELAY"] > 15).astype(int)

    # Group by (AIRLINE, HOUR): delay rate + sample size
    grp = (cand.groupby(["AIRLINE", "DEPARTURE_HOUR"])
                .agg(delay_rate=("DELAYED_15", "mean"),
                     flights=("DELAYED_15", "size"))
                .reset_index())

    if grp.empty:
        return {
            "reply": "Not enough history to recommend alternatives on this route/month.",
            "intent": "ALTERNATIVES",
            "context": ctx,
            "actions": {}
        }

    # Prefer nearby hours, require some support
    grp["hour_gap"] = (grp["DEPARTURE_HOUR"] - dep_hour).abs()
    ranked = grp[grp["flights"] >= 15].copy()
    if ranked.empty:
        ranked = grp.copy()

    ranked = ranked.sort_values(
        ["delay_rate", "hour_gap", "flights"],
        ascending=[True, True, False]
    ).head(5)

    # Build reply
    lines = []
    for _, r in ranked.iterrows():
        lines.append(
            f"- {pretty_airport(origin)} → {pretty_airport(dest)} · {int(r['DEPARTURE_HOUR']):02d}:00 · "
            f"{pretty_airline(r['AIRLINE'])} · delay≈{r['delay_rate']:.1%} (n={int(r['flights'])})"
        )

    reply = ("Here are lower-risk options from history:<br>" + "<br>".join(lines) +
             "<br>Tip: earlier departures often avoid knock-on delays.")

    return {
        "reply": reply,
        "intent": "ALTERNATIVES",
        "context": ctx,
        "actions": {"alternatives": ranked.to_dict(orient="records")}
    }

def find_next_departures(ctx: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
    """
    List the next N departures after the given time for the same origin->dest and date.
    Uses SCHEDULED_DEPARTURE (HHMM) from the historical file (acts as schedule proxy).
    """
    needed = ["origin", "destination", "date", "sched_departure"]
    if not all(k in ctx for k in needed):
        return {
            "reply": "To list next flights, I need origin, destination, date and time. "
                     "Example: predict AA ATL to LAX 2015-06-15 13:30",
            "intent": "NEXT_FLIGHTS", "context": ctx, "actions": {}
        }

    origin = ctx["origin"]; dest = ctx["destination"]
    try:
        day = dateparser.parse(ctx["date"])
        month = day.month
        day_of_month = day.day
    except Exception:
        return {"reply": "Invalid date format. Use YYYY-MM-DD.",
                "intent": "NEXT_FLIGHTS", "context": ctx, "actions": {}}

    cur_hhmm = int(ctx["sched_departure"])
    cur_minutes = (cur_hhmm // 100) * 60 + (cur_hhmm % 100)

    # same O&D and same MONTH (dataset is 2015; no exact day schedule → we approximate with same month)
    sub = df[(df["ORIGIN_AIRPORT"] == origin) &
             (df["DESTINATION_AIRPORT"] == dest) &
             (df["MONTH"] == month)].copy()
    if sub.empty:
        return {"reply": f"No flights found for {origin}->{dest} in month {month}.",
                "intent": "NEXT_FLIGHTS", "context": ctx, "actions": {}}

    sub["DEP_HHMM"] = sub["SCHEDULED_DEPARTURE"].astype(int)
    sub["DEP_MIN"]  = (sub["DEP_HHMM"] // 100) * 60 + (sub["DEP_HHMM"] % 100)
    sub = sub[sub["DEP_MIN"] >= cur_minutes]          # departures after now
    sub = sub.sort_values("DEP_MIN").head(8)

    if sub.empty:
        return {"reply": "No later departures found today for this route.",
                "intent": "NEXT_FLIGHTS", "context": ctx, "actions": {}}

    lines, items = [], []
    for _, r in sub.iterrows():
        hh = int(r["DEP_HHMM"]) // 100
        mm = int(r["DEP_HHMM"]) % 100
        rate = float((r["ARRIVAL_DELAY"] > 15))
        lines.append(
            f"- {pretty_airport(origin)} → {pretty_airport(dest)} · {hh:02d}:{mm:02d} · {pretty_airline(r['AIRLINE'])}"
        )
        items.append({"AIRLINE": r["AIRLINE"], "HHMM": int(r["DEP_HHMM"])})

    reply = "Next departures (historical schedule approximation):<br>" + "<br>".join(lines)
    return {"reply": reply, "intent": "NEXT_FLIGHTS", "context": ctx, "actions": {"next_flights": items}}

LOW_COST_AIRLINES = {"WN", "NK", "B6"}  # Southwest, Spirit, JetBlue (heuristic)

def cheapest_offline_heuristic(ctx: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
    origin = ctx.get("origin"); dest = ctx.get("destination")
    date   = ctx.get("date")
    if not all([origin, dest, date]):
        return {"reply": "To search cheap options, please provide origin, destination and date.",
                "intent": "CHEAP_FLIGHTS", "context": ctx, "actions": {}}

    # same O&D across the dataset
    sub = df[(df["ORIGIN_AIRPORT"] == origin) & (df["DESTINATION_AIRPORT"] == dest)].copy()
    if sub.empty:
        return {"reply": f"No history found for {origin}->{dest}.", "intent": "CHEAP_FLIGHTS", "context": ctx, "actions": {}}

    # score: shorter distance preferred; low-cost carriers get a small bonus
    sub = sub[["AIRLINE", "DISTANCE", "SCHEDULED_DEPARTURE"]].dropna()
    sub["fare_score"] = (sub["DISTANCE"] / sub["DISTANCE"].max().clip(1)) + \
                        (~sub["AIRLINE"].isin(LOW_COST_AIRLINES)).astype(int) * 0.2

    # group by (AIRLINE, hour)
    sub["HOUR"] = (sub["SCHEDULED_DEPARTURE"] // 100).astype(int)
    grp = (sub.groupby(["AIRLINE", "HOUR"])
              .agg(avg_distance=("DISTANCE","mean"),
                   score=("fare_score","mean"),
                   count=("DISTANCE","size"))
              .reset_index()
              .sort_values(["score","avg_distance"], ascending=[True, True])
              .head(5))

    # Build reply text
    lines = [
        f"- {pretty_airport(origin)} → {pretty_airport(dest)} · {int(r.HOUR):02d}:00 · "
        f"{pretty_airline(r.AIRLINE)} (cheap-ish historically)"
        for _, r in grp.iterrows()
    ]
              
    reply = (
        "📉 Historical cheap options (no live fares in dataset):<br>" 
        + "<br>".join(lines) +
        "<br>💡 Note: This is a demo heuristic. Add a fares API (Amadeus/Skyscanner) for real ticket prices."
    )

    return {"reply": reply, "intent": "CHEAP_FLIGHTS", "context": ctx,
            "actions": {"cheap_candidates": grp.to_dict(orient="records")}}


def cheapest_live_api(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder for a real fares API (Amadeus, Skyscanner, Kiwi, etc.).
    Implement once you have keys; keep the same return shape for the chatbot.
    """
    api_key = os.getenv("FARES_API_KEY")
    if not api_key:
        return {"reply": "No fares API configured. Using heuristic instead.", "intent": "CHEAP_FLIGHTS"}
    # TODO: call your provider here and map to reply/actions
    return {"reply": "Live fares API not wired yet.", "intent": "CHEAP_FLIGHTS"}



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

def route_intent(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["predict", "probability", "chance", "will my flight"]): 
        return "PREDICT"
    if "explain" in t or "why" in t: 
        return "EXPLAIN"
    if "alternatives" in t: 
        return "ALTERNATIVES"
    if any(w in t for w in ["next flights", "next departure", "upcoming flights", "what's next"]): 
        return "NEXT_FLIGHTS"
    if any(w in t for w in ["cheap", "cheapest", "low fare", "lowest price"]): 
        return "CHEAP_FLIGHTS"
    if any(w in t for w in ["worst origin", "airport delays", "by airport"]): 
        return "ANALYTICS_ORIGIN"
    if any(w in t for w in ["airline delays", "by airline"]): 
        return "ANALYTICS_AIRLINE"
    if "by hour" in t or "time of day" in t: 
        return "ANALYTICS_HOUR"
    if "routes" in t or "city pair" in t: 
        return "ANALYTICS_ROUTE"
    if "parse" in t: 
        return "PARSE"
    if "help" in t: 
        return "HELP"

    # 👇 Anything else should go to the LLM
    return "UNKNOWN"



def run_analytics(intent: str) -> str:
    df = DF

    if intent == "ANALYTICS_ORIGIN":
        ans = (df.groupby("ORIGIN_AIRPORT")["DELAYED_15"].mean()*100).round(1).sort_values(ascending=False).head(10)
        lines = [f"• {pretty_airport(airport)}: {rate:.1f}%" for airport, rate in ans.items()]
        return "✈️ Worst origin airports (top 10):\n" + "\n".join(lines)

    if intent == "ANALYTICS_AIRLINE":
        ans = (df.groupby("AIRLINE")["DELAYED_15"].mean()*100).round(1).sort_values(ascending=False).head(10)
        lines = [f"• {pretty_airline(airline)}: {rate:.1f}%" for airline, rate in ans.items()]
        return "🛫 Worst airlines by delay rate:<br>" + "<br>".join(lines)

    if intent == "ANALYTICS_HOUR":
        ans = (df.groupby("DEP_HOUR")["DELAYED_15"].mean()*100).round(1)
        lines = []
        for hour, rate in ans.items():
            if rate >= 20:   # high delay hours
                emoji = "❌"
            elif rate <= 10: # good hours
                emoji = "✅"
            else:
                emoji = "⚠️"
            lines.append(f"{emoji} At {hour:02d}:00 → Delay rate: {rate:.1f}%")
        return "🕑 Delay rate by departure hour:<br>" + "<br>".join(lines)

    if intent == "ANALYTICS_ROUTE":
        tmp = df.copy()
        tmp["ROUTE"] = tmp["ORIGIN_AIRPORT"] + "→" + tmp["DESTINATION_AIRPORT"]
        ans = (tmp.groupby("ROUTE")["DELAYED_15"].mean()*100).round(1).sort_values(ascending=False).head(10)
        lines = [f"• {route}: {rate:.1f}%" for route, rate in ans.items()]
        return "🌍 Worst routes (top 10):<br>" + "<br>".join(lines)


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
        reply = (
            f"Delay probability for {pretty_airline(ctx['airline'])} "
            f"{pretty_airport(ctx['origin'])} → {pretty_airport(ctx['destination'])}: "
            f"{proba*100:.1f}%\n"
            f"On-time probability: {(1-proba)*100:.1f}%\n"
            "Say 'explain' for a short reason."
        )
        return ChatOut(reply=reply, intent="PREDICT", context=ctx,
                       actions={"delay_probability": proba, "ontime_probability": 1-proba})

    if intent=="EXPLAIN":
        p = ctx.get("last_delay_probability")
        if p is None:
            return ChatOut(reply="Predict first, then I can explain. Try: 'predict AA ATL to LAX 2015-06-15 13:30'",
                           intent="HELP", context=ctx)
        airline = ctx.get("airline","?"); origin = ctx.get("origin","?"); dest = ctx.get("destination","?")
        month = ctx.get("month","?"); hour = ctx.get("dep_hour","?")
        text = (
            f"Estimated delay risk is {float(p):.0%} for {pretty_airline(airline)} "
            f"{pretty_airport(origin)} → {pretty_airport(dest)} "
            f"(month {month}, hour {hour}).\n"    
            "💡 Recommendation: try earlier departures, buffer connections, or alternate airports."
        )

        return ChatOut(reply=text, intent="EXPLAIN", context=ctx)
    
    if intent == "ALTERNATIVES":
        return ChatOut(**suggest_alternatives(ctx, DF))
    
    if intent in ["ANALYTICS_ORIGIN","ANALYTICS_AIRLINE","ANALYTICS_HOUR","ANALYTICS_ROUTE"]:
        return ChatOut(reply=run_analytics(intent), intent="ANALYTICS", context=ctx)


    if intent in ["ANALYTICS_ORIGIN","ANALYTICS_AIRLINE","ANALYTICS_HOUR","ANALYTICS_ROUTE"]:
        return ChatOut(reply=run_analytics(intent), intent="ANALYTICS", context=ctx)
    
    if intent == "NEXT_FLIGHTS":
        return ChatOut(**find_next_departures(ctx, DF))

    if intent == "CHEAP_FLIGHTS":
        if not all(k in ctx for k in ["origin", "destination", "date"]):
            ctx.update({k:v for k,v in parse_free_text(msg).items() if v is not None})
        live = cheapest_live_api(ctx)
        if "No fares API" in live.get("reply",""):
             return ChatOut(**cheapest_offline_heuristic(ctx, DF))
        return ChatOut(**live)

    
    # If we couldn't route the intent, ask the LLM
    if intent == "UNKNOWN":
        llm_reply, provider = ask_llm(msg)
        ctx["llm_used"] = provider   # 👈 add flag in context
        return ChatOut(reply=llm_reply, intent="LLM", context=ctx)

    # Otherwise show help (final fallback)
    help_text = (
        "I can:\n"
        "• Predict delay → 'predict AA ATL to LAX 2015-06-15 13:30'\n"
        "• Explain last prediction → 'explain'\n"
        "• Suggest lower-risk options → 'alternatives'\n"
        "• Show next departures → 'next flights'\n"
        "• Find cheaper options → 'cheap flights'\n"
        "• Analytics → 'worst origin airports', 'airline delays', 'delay by hour', 'worst routes'\n"
        "• Parse free text → 'parse AA tomorrow 1:30pm ATL to LAX'\n"
        "• General questions → ask in plain English (LLM-powered: OpenAI + Gemini fallback)\n"
    )
    return ChatOut(reply=help_text, intent="HELP", context=ctx)

@app.get("/")
def health():
    return {"status": "ok", "endpoints": ["/chat", "/docs", "/redoc"]}
