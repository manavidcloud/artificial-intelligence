# app_ui.py
import streamlit as st
import requests

st.set_page_config(page_title="Agentic Banking Chat", page_icon="🤖")

st.title("🏦 AI Banking Assistant Lab")
st.caption("Chat UI -> Backend API -> AI Agent <-> LLM -> Bank APIs")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input Field
if user_input := st.chat_input("Type your question (e.g., 'What is my balance?')..."):
    # Render User Message in UI
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Call Backend API
    backend_url = "http://127.0.0.1:8000/api/chat"
    payload = {"user_id": "usr_101", "message": user_input}

    try:
        response = requests.post(backend_url, json=payload)
        if response.status_code == 200:
            bot_reply = response.json()["reply"]
        else:
            bot_reply = "Error: Backend API returned an invalid response."
    except Exception as e:
        bot_reply = f"Failed to connect to Backend API. Make sure backend.py is running! Error: {e}"

    # Render Bot Reply in UI
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    with st.chat_message("assistant"):
        st.markdown(bot_reply)