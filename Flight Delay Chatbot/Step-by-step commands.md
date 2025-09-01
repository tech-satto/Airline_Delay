***Step-by-step commands***







***For API part (Uvicorn):***



conda activate flights



cd "C:\\Users\\Shivyansh Rai\\artifacts"



python -m uvicorn chatbot\_server:app --reload --port 8020



Uvicorn running on http://127.0.0.1:8020 





***For Streamlit UI:***



conda activate flights



cd "C:\\Users\\Shivyansh Rai\\artifacts"



streamlit run chat\_ui.py





Local URL: http://localhost:8501



Network URL: http://192.168.0.146:8501

