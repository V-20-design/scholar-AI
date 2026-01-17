import streamlit as st
from google import genai
from google.genai import types
import json, os, io

# --- 1. AUTHENTICATION ---
@st.cache_resource
def init_scholar():
    project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT")
    sa_json_str = st.secrets.get("SERVICE_ACCOUNT_JSON")
    
    if not sa_json_str or not project_id:
        st.error("❌ Credentials missing in Streamlit Secrets!")
        return None

    try:
        # Clean up the string in case of accidental hidden characters
        clean_json = sa_json_str.strip()
        
        # Initialize the Client for Vertex AI (Kenya-stable)
        # We pass the JSON string via the standard environment variable
        os.environ["GOOGLE_APPLICATION_CREDENTIALS_DICT"] = clean_json
        
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location="us-central1"
        )
        return client
    except json.JSONDecodeError as je:
        st.error(f"❌ JSON Format Error: Check your triple quotes in Secrets. Detail: {je}")
        return None
    except Exception as e:
        st.error(f"❌ Initialization Failed: {e}")
        return None

# UI CONFIG
st.set_page_config(page_title="ScholarAI Pro", layout="wide", page_icon="🎓")
client = init_scholar()

# --- 2. THE RESEARCH FUNCTION ---
def scholar_ask(prompt, file_bytes, mime):
    try:
        # Send bytes directly to Vertex AI
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' a research assistant.",
                temperature=0.2
            )
        )
        return response.text
    except Exception as e:
        st.error(f"⚠️ Professor Error: {str(e)[:250]}")
        return None

# --- 3. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab")

if client:
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])

    if uploaded_file:
        # Keep file in memory to prevent re-reads
        if "file_cache" not in st.session_state or st.session_state.cache_name != uploaded_file.name:
            st.session_state.file_cache = uploaded_file.read()
            st.session_state.cache_name = uploaded_file.name
            st.session_state.cache_mime = uploaded_file.type

        col1, col2 = st.columns(2)
        with col1:
            if "video" in st.session_state.cache_mime:
                st.video(st.session_state.file_cache)
            else:
                st.info(f"📄 Document Loaded: {st.session_state.cache_name}")
                
        with col2:
            query = st.chat_input("Ask the Professor...")
            if query:
                with st.spinner("Scholar is processing..."):
                    ans = scholar_ask(query, st.session_state.file_cache, st.session_state.cache_mime)
                    if ans:
                        st.chat_message("assistant").write(ans)
    else:
        st.info("👋 Welcome! Please upload a file to begin.")
else:
    st.warning("Awaiting proper configuration in Streamlit Secrets.")





























