import streamlit as st
from google import genai
from google.genai import types
import json, os, io

# --- 1. AUTHENTICATION ---
def init_scholar():
    project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT")
    sa_json = st.secrets.get("SERVICE_ACCOUNT_JSON")
    
    if not sa_json or not project_id:
        st.error("Missing Credentials! Please check Streamlit Secrets.")
        return None

    try:
        # Load the credentials from the secret
        os.environ["GOOGLE_APPLICATION_CREDENTIALS_DICT"] = sa_json
        
        # Initialize the Vertex AI Client
        return genai.Client(
            vertexai=True,
            project=project_id,
            location="us-central1"
        )
    except Exception as e:
        st.error(f"Professor Connection Failed: {e}")
        return None

# UI STYLING
st.set_page_config(page_title="ScholarAI Pro", layout="wide", page_icon="🎓")
client = init_scholar()

if not client:
    st.stop()

# --- 2. RESEARCH ENGINE ---
def scholar_ask(prompt, file_bytes, mime):
    try:
        # Vertex AI uses direct byte parts for maximum stability
        part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an expert research assistant.",
                temperature=0.2
            )
        )
        return response.text
    except Exception as e:
        st.error(f"Scholar Error: {e}")
        return None

# --- 3. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab")
st.markdown("---")

uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])

if uploaded_file:
    file_bytes = uploaded_file.read()
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if "video" in uploaded_file.type:
            st.video(file_bytes)
        else:
            st.info(f"📄 Analyzing: {uploaded_file.name}")
            
    with col2:
        if query := st.chat_input("Ask the Professor..."):
            with st.spinner("Analyzing material..."):
                ans = scholar_ask(query, file_bytes, uploaded_file.type)
                if ans:
                    st.chat_message("assistant").write(ans)
else:
    st.info("👋 Welcome! Please upload your material to start the session.")


























