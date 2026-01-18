import streamlit as st
from google import genai
from google.genai import types
from google.oauth2 import service_account  # The secret weapon
import json, os

# --- 1. AUTHENTICATION (The Permanent Fix) ---
@st.cache_resource
def init_scholar():
    project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT")
    sa_json_str = st.secrets.get("SERVICE_ACCOUNT_JSON")
    
    if not sa_json_str or not project_id:
        st.error("❌ Missing Secrets!")
        return None

    try:
        # 1. Manually create credentials to bypass metadata server lookup
        sa_info = json.loads(sa_json_str)
        creds = service_account.Credentials.from_service_account_info(sa_info)
        
        # 2. Pass these specific credentials directly to the client
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location="us-central1",
            credentials=creds  # <--- This stops the error you saw
        )
        return client
    except Exception as e:
        st.error(f"❌ Handshake Failed: {e}")
        return None

# --- UI SETUP ---
st.set_page_config(page_title="ScholarAI Pro", layout="wide", page_icon="🎓")
client = init_scholar()

# --- 2. THE STREAMING ENGINE ---
def scholar_stream(prompt, file_bytes, mime):
    try:
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        # Using stream=True makes the app feel responsive even on slow connections
        return client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an expert professor.",
                temperature=0.0
            )
        )
    except Exception as e:
        st.error(f"⚠️ Professor Error: {str(e)[:150]}")
        return None

# --- 3. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab")

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.header("📂 Data Source")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    if st.button("🗑️ Clear Memory"):
        st.session_state.history = []
        st.rerun()

if uploaded_file and client:
    # Use getvalue() for safety in memory
    f_bytes = uploaded_file.getvalue()
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        if "video" in uploaded_file.type:
            st.video(f_bytes)
        else:
            st.success(f"📄 {uploaded_file.name} is ready.")

    with col2:
        # Show past chat
        for msg in st.session_state.history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # New Query
        if user_query := st.chat_input("Ask the Professor..."):
            with st.chat_message("user"):
                st.write(user_query)
            
            with st.chat_message("assistant"):
                res_box = st.empty()
                full_text = ""
                
                with st.spinner("Processing..."):
                    stream = scholar_stream(user_query, f_bytes, uploaded_file.type)
                    if stream:
                        for chunk in stream:
                            if chunk.text:
                                full_text += chunk.text
                                res_box.markdown(full_text + "▌")
                        res_box.markdown(full_text)
                    
            st.session_state.history.append({"role": "user", "content": user_query})
            st.session_state.history.append({"role": "assistant", "content": full_text})
else:
    st.info("👋 Upload a file in the sidebar to begin.")
































