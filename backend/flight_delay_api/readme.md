//input
{
  "date": "2015-06-15",
  "airline": "AA",
  "origin": "ATL",
  "destination": "LAX",
  "sched_departure": 1330
}


//output
{
    "flight": {
        "date": "2015-06-15",
        "airline": "AA",
        "origin": "ATL",
        "destination": "LAX",
        "sched_departure": 1330
    },
    "prob_delay": 0.2150767594575882,
    "alternative_flights": [
        {
            "airline": "AA",
            "departure": 715,
            "prob_delay": 0.12
        },
        {
            "airline": "DL",
            "departure": 959,
            "prob_delay": 0.12
        },
        {
            "airline": "DL",
            "departure": 1206,
            "prob_delay": 0.14
        },
        {
            "airline": "DL",
            "departure": 1100,
            "prob_delay": 0.14
        },
        {
            "airline": "DL",
            "departure": 1208,
            "prob_delay": 0.14
        }
    ]
}