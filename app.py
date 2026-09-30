import streamlit as st
import requests
import re
import os
import json

API_URL = "http://127.0.0.1:8000/chat"
API_STREAM_URL = "http://127.0.0.1:8000/chat_stream"

st.set_page_config(page_title="Institutional Assistant", page_icon="🎓")
st.title("Hybrid Institutional Intelligence Assistant")
st.write("Ask about academic policies or student enrollment data.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for Debugging Logs
with st.sidebar:
    st.title("🛠️ Agent Debugger")
    st.write("Live logs of the AI's internal thought process:")
    
    # Show logs from the most recent interaction
    if st.session_state.messages:
        latest_msg = st.session_state.messages[-1]
        if latest_msg.get("logs"):
            st.code(latest_msg["logs"], language="text")
        else:
            st.info("No logs generated yet.")
    else:
        st.info("Waiting for first query...")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("screenshots"):
            st.markdown("---")
            st.caption("📸 **Verification Guide:** Here is the source portal snapshot to verify this document:")
            for s in message["screenshots"]:
                if os.path.exists(s):
                    st.image(s, use_container_width=True, caption="Source Webpage Snapshot")

if prompt := st.chat_input("E.g., What is the grading policy or check hostel rules?"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process and add assistant message
    with st.chat_message("assistant"):
        logs = ""
        screenshots = []
        status_container = st.status("Assistant is starting up...", expanded=True)
        try:
            response = requests.post(API_STREAM_URL, json={"query": prompt}, stream=True)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line.decode('utf-8'))
                    if data["type"] == "log":
                        logs += data["content"]
                        text = data["content"].strip()
                        # Detect Agent or Tool activity
                        if "Institutional AI Assistant" in text:
                            status_container.update(label="Assistant is analyzing the request...")
                        elif "Action: PolicyRAGTool" in text:
                            status_container.update(label="Executing RAG Search on documents...")
                        elif "Action: StudentDataTool" in text:
                            status_container.update(label="Executing Python data analysis...")
                    elif data["type"] == "result":
                        answer = data["response"]
                        screenshots = data.get("screenshots", [])
                        status_container.update(label="Complete!", state="complete", expanded=False)
                    elif data["type"] == "error":
                        answer = f"Error: {data['response']}"
                        status_container.update(label="Error occurred", state="error", expanded=False)
        except Exception as e:
            answer = f"Error communicating with backend: {e}"
            status_container.update(label="Failed", state="error", expanded=False)
        
        st.markdown(answer)
        
        # Render verification screenshots for the user
        valid_screenshots = [s for s in screenshots if os.path.exists(s)]
        if valid_screenshots:
            st.markdown("---")
            st.caption("📸 **Verification Guide:** Here is the source portal snapshot where you can find and verify this document yourself:")
            for s in valid_screenshots:
                st.image(s, use_container_width=True, caption="Source Webpage Snapshot")
                
        st.session_state.messages.append({
            "role": "assistant", 
            "content": answer, 
            "logs": logs,
            "screenshots": valid_screenshots
        })
