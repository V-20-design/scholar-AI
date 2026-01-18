import streamlit as st
from google import genai
from google.genai import types
import json, os

# --- 1. AUTHENTICATION ---
@st.cache_resource
def init_scholar():
    project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT")
    sa_json_str = st.secrets.get("SERVICE_ACCOUNT_JSON")
    
    if not sa_json_str or not project_id:
        st.error("❌ Missing Secrets: Check GOOGLE_CLOUD_PROJECT and SERVICE_ACCOUNT_JSON.")
        return None

    try:
        # Pass the Service Account JSON via environment
        os.environ["GOOGLE_APPLICATION_CREDENTIALS_DICT"] = sa_json_str.strip()
        
        # Initialize Vertex AI Client
        return genai.Client(
            vertexai=True,
            project=project_id,
            location="us-central1"
        )
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}")
        return None

# --- UI SETUP ---
st.set_page_config(page_title="ScholarAI Pro", layout="wide", page_icon="🎓")
client = init_scholar()

# --- 2. RESEARCH ENGINE ---
def scholar_ask(prompt, file_bytes, mime):
    try:
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' a research professor.",
                temperature=0.2
            )
        )
        return response.text
    except Exception as e:
        err = str(e)
        if "403" in err: return "🚫 API Error: Enable 'Vertex AI API' in Google Console."
        return f"⚠️ Error: {err[:200]}"

# --- 3. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab")

if client:
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])

    if uploaded_file:
        if "file_data" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
            st.session_state.file_data = uploaded_file.read()
            st.session_state.file_name = uploaded_file.name
            st.session_state.mime_type = uploaded_file.type

        col1, col2 = st.columns(2)
        with col1:
            if "video" in st.session_state.mime_type:
                st.video(st.session_state.file_data)
            else:
                st.info(f"📄 File: {st.session_state.file_name}")
                
        with col2:
            if user_query := st.chat_input("Ask the Professor..."):
                with st.spinner("Analyzing..."):
                    answer = scholar_ask(user_query, st.session_state.file_data, st.session_state.mime_type)
                    if answer: st.chat_message("assistant").write(answer)
    else:
        st.info("👋 Upload a file to begin.")





























