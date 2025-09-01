import streamlit as st
import requests
from datetime import datetime
import re

# ---- CONFIG ----
API_URL = "http://127.0.0.1:8020/chat"   # FastAPI backend
st.set_page_config(page_title="Flight Chatbot", page_icon="✈️", layout="centered")

# ---- CSS for styled chat with avatars and highlights ----
st.markdown("""
<style>
.chat-container {
    display: flex;
    flex-direction: column;
}
.chat-row {
    display: flex;
    align-items: flex-end;
    margin: 5px 0;
}
.avatar {
    width: 35px;
    height: 35px;
    border-radius: 50%;
    background-color: #ECECEC;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    margin: 0 8px;
}
.user-bubble {
    background-color: #DCF8C6;
    margin-left: auto;
    text-align: right;
    color: black;
    padding: 10px 15px;
    border-radius: 12px;
    max-width: 70%;
}
.bot-bubble {
    background-color: #075E54;
    margin-right: auto;
    text-align: left;
    color: white;
    padding: 10px 15px;
    border-radius: 12px;
    max-width: 70%;
}
.timestamp {
    font-size: 11px;
    opacity: 0.7;
    margin-top: 3px;
    text-align: right;
}
.highlight-delay {
    color: #FF4C4C;  /* red */
    font-weight: bold;
}
.highlight-ontime {
    color: #00C851;  /* green */
    font-weight: bold;
}
.highlight-cheap {
    color: #00C851;  /* green for cheap */
    font-weight: bold;
}
.highlight-alt {
    color: #FFBB33;  /* yellow for alternatives */
    font-weight: bold;
}
.highlight-explain {
    color: #FFD700;  /* gold for explain */
    font-style: italic;
}
</style>
""", unsafe_allow_html=True)

# ---- Session State ----
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "context" not in st.session_state:
    st.session_state.context = {}

st.title("✈️ Flight Chatbot")

# ---- Chat Input ----
user_message = st.chat_input("Type your message...")

if user_message:
    now = datetime.now().strftime("%H:%M")
    # Save user message
    st.session_state.chat_history.append({"role": "user", "content": user_message, "time": now})

    # Send to FastAPI with context
    try:
        resp = requests.post(API_URL, json={
            "message": user_message,
            "context": st.session_state.context
        })
        data = resp.json()
        bot_reply = data.get("reply", "⚠️ No response from server")

        # 🔑 Update context so it persists across turns
        if "context" in data:
            st.session_state.context = data["context"]

    except Exception as e:
        bot_reply = f"⚠️ Error contacting API: {e}"

    now = datetime.now().strftime("%H:%M")
    # Save bot reply
    st.session_state.chat_history.append({"role": "bot", "content": bot_reply, "time": now})

# ---- Display Chat ----
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.markdown(
            f"<div class='chat-row' style='justify-content:flex-end;'>"
            f"<div class='user-bubble'>{msg['content']}<div class='timestamp'>{msg['time']}</div></div>"
            f"<div class='avatar'>🧑</div></div>",
            unsafe_allow_html=True,
        )
    else:
        # Format bot reply
        content = msg["content"]

        # Highlight predictions
        if "Delay probability" in content:
            delay_match = re.search(r"Delay probability: ([0-9.]+)%", content)
            ontime_match = re.search(r"On-time probability: ([0-9.]+)%", content)
            if delay_match and ontime_match:
                delay = f"<span class='highlight-delay'>❌ Delay {delay_match.group(1)}%</span>"
                ontime = f"<span class='highlight-ontime'>✅ On-time {ontime_match.group(1)}%</span>"
                content = f"{delay}<br>{ontime}<br><i>Say 'explain' for a short reason.</i>"

        # Highlight "explain" answers
        if "Estimated delay risk" in content:
            content = f"<span class='highlight-explain'>💡 {content}</span>"

        # Highlight cheap flights
        if "Cheapest options" in content or "cheap-ish" in content:
            lines = content.split("\n")
            highlighted = []
            for line in lines:
                if "·" in line:
                    highlighted.append(f"<span class='highlight-cheap'>🟢 {line}</span>")
                else:
                    highlighted.append(line)
            content = "<br>".join(highlighted)

        # Highlight alternatives
        if "lower-risk options" in content or "Tip: earlier departures" in content:
            lines = content.split("\n")
            highlighted = []
            for line in lines:
                if "·" in line:
                    highlighted.append(f"<span class='highlight-alt'>🟡 {line}</span>")
                else:
                    highlighted.append(line)
            content = "<br>".join(highlighted)

        st.markdown(
            f"<div class='chat-row' style='justify-content:flex-start;'>"
            f"<div class='avatar'>🤖</div>"
            f"<div class='bot-bubble'>{content}<div class='timestamp'>{msg['time']}</div></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
st.markdown("</div>", unsafe_allow_html=True)
