import streamlit as st
from google import genai
from google.genai import types
import json, os, io

# --- 1. AUTHENTICATION ---
@st.cache_resource
def init_scholar():
    # Make sure these match your Streamlit Secrets exactly
    project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT")
    sa_json_str = st.secrets.get("SERVICE_ACCOUNT_JSON")
    
    if not sa_json_str or not project_id:
        st.error("❌ Credentials missing in Streamlit Secrets!")
        return None

    try:
        # 1. Parse the string into a Python Dictionary
        sa_info = json.loads(sa_json_str)
        
        # 2. Initialize the Client by passing the 'vertexai' flag 
        # The SDK will look for credentials in the environment or we can 
        # provide the project/location explicitly for Vertex.
        # To fix the metadata error, we must ensure the environment is clean:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS_DICT"] = sa_json_str
        
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location="us-central1"
        )
        return client
    except Exception as e:
        st.error(f"❌ Initialization Failed: {e}")
        return None

# UI CONFIG
st.set_page_config(page_title="ScholarAI Pro", layout="wide", page_icon="🎓")
client = init_scholar()

# --- 2. THE RESEARCH FUNCTION ---
def scholar_ask(prompt, file_bytes, mime):
    try:
        # Convert bytes to a Part for Vertex AI
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        
        # Call Gemini 1.5 Flash
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an expert research assistant.",
                temperature=0.2
            )
        )
        return response.text
    except Exception as e:
        st.error(f"⚠️ Professor Error: {str(e)[:200]}")
        return None

# --- 3. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab")

if client:
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])

    if uploaded_file:
        # Store file in session state to prevent reloading
        if "active_file" not in st.session_state or st.session_state.active_file_name != uploaded_file.name:
            st.session_state.active_file = uploaded_file.read()
            st.session_state.active_file_name = uploaded_file.name
            st.session_state.active_mime = uploaded_file.type

        col1, col2 = st.columns(2)
        with col1:
            if "video" in st.session_state.active_mime:
                st.video(st.session_state.active_file)
            else:
                st.info(f"📄 Document Loaded: {st.session_state.active_file_name}")
                
        with col2:
            query = st.chat_input("Ask a question about this material...")
            if query:
                with st.spinner("Scholar is processing..."):
                    ans = scholar_ask(query, st.session_state.active_file, st.session_state.active_mime)
                    if ans:
                        st.chat_message("assistant").write(ans)
    else:
        st.info("👋 Welcome! Please upload a document or video to begin.")
else:
    st.warning("Please verify your Service Account JSON is correctly pasted into Streamlit Secrets.")




























