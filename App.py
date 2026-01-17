import streamlit as st
from google import genai
from google.genai import types
import json, os, io

# --- 1. AUTHENTICATION ---
@st.cache_resource
def init_scholar():
    project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT")
    sa_json = st.secrets.get("SERVICE_ACCOUNT_JSON")
    
    if not sa_json or not project_id:
        st.error("❌ Missing Credentials in Streamlit Secrets!")
        return None

    try:
        # Load credentials for Vertex AI
        os.environ["GOOGLE_APPLICATION_CREDENTIALS_DICT"] = sa_json
        
        # Initialize Client
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location="us-central1" # Stable region
        )
        return client
    except Exception as e:
        st.error(f"❌ Connection Setup Failed: {e}")
        return None

# UI STYLING
st.set_page_config(page_title="ScholarAI Pro", layout="wide", page_icon="🎓")
client = init_scholar()

# --- 2. RESEARCH ENGINE (Enhanced with Debugging) ---
def scholar_ask(prompt, file_bytes, mime):
    if not client:
        return "System not initialized."
    
    try:
        # Convert bytes for Vertex AI
        part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        
        # Call the model
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an expert research assistant.",
                temperature=0.2
            )
        )
        
        if not response.text:
            return "The Professor analyzed the file but provided an empty response."
        return response.text

    except Exception as e:
        # Capture specific errors like "Permission Denied" or "Quota Exceeded"
        error_msg = str(e)
        if "403" in error_msg:
            st.error("🚫 Permission Denied: Ensure the Service Account has 'Vertex AI User' role.")
        elif "429" in error_msg:
            st.error("⏳ Quota Exceeded: Too many requests at once.")
        else:
            st.error(f"⚠️ AI Error: {error_msg}")
        return None

# --- 3. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab")
st.markdown("---")

if client:
    st.sidebar.success("✅ Professor is Online")
else:
    st.sidebar.error("❌ Professor is Offline")

uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])

if uploaded_file:
    # Avoid re-reading the file on every click
    if "file_data" not in st.session_state or st.session_state.get("last_file") != uploaded_file.name:
        st.session_state.file_data = uploaded_file.read()
        st.session_state.last_file = uploaded_file.name
        st.session_state.mime = uploaded_file.type

    col1, col2 = st.columns([1, 1])
    with col1:
        if "video" in st.session_state.mime:
            st.video(st.session_state.file_data)
        else:
            st.info(f"📄 Analyzing: {uploaded_file.name}")
            
    with col2:
        query = st.chat_input("Ask a question about the material...")
        if query:
            with st.status("The Scholar is thinking...", expanded=True) as status:
                st.write("Reading file parts...")
                ans = scholar_ask(query, st.session_state.file_bytes if hasattr(st.session_state, 'file_bytes') else st.session_state.file_data, st.session_state.mime)
                if ans:
                    status.update(label="Analysis Complete!", state="complete", expanded=False)
                    st.chat_message("assistant").write(ans)
                else:
                    status.update(label="Analysis Failed", state="error")
else:
    st.info("👋 Please upload a document or video to start.")



























