
import streamlit as st
from google import genai
from google.genai import types
import io, time

# --- 1. CONFIGURATION ---
def get_config():
    return {
        "api_key": st.secrets.get("GOOGLE_API_KEY"),
        "project_id": st.secrets.get("GOOGLE_CLOUD_PROJECT"),
        "location": "us-central1"
    }

cfg = get_config()

# UI STYLING
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")

# --- 2. THE FIXED INITIALIZER ---
@st.cache_resource
def init_client():
    if not cfg["api_key"]:
        return None
    try:
        # THE FIX: We only pass the api_key and vertexai=True.
        # We do NOT pass project/location inside the Client() if using api_key.
        # This triggers "Vertex AI Express Mode" which is stable in Kenya.
        return genai.Client(
            api_key=cfg["api_key"],
            vertexai=True 
        )
    except Exception as e:
        st.error(f"Auth Error: {e}")
        return None

client = init_client()

if not client:
    st.warning("⚠️ Action Required: Please add your GOOGLE_API_KEY to Streamlit Secrets.")
    st.stop()

# --- 3. UPDATED FILE HANDLING (Vertex Friendly) ---
def safe_scholar_call(prompt, file_bytes, mime_type, model_choice):
    model_id = "gemini-1.5-flash" if "Flash" in model_choice else "gemini-1.5-pro"
    try:
        # We send bytes directly to avoid the 'upload' error from earlier
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        response = client.models.generate_content(
            model=model_id,
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an expert Research Professor.",
                temperature=0.3
            )
        )
        return response.text
    except Exception as e:
        st.error(f"Professor Busy: {str(e)[:150]}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    st.success("Connected via Vertex AI Express")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    model_choice = st.selectbox("Intelligence Tier", ["Gemini 1.5 Flash", "Gemini 1.5 Pro"])

# --- MAIN LAB ---
if uploaded_file:
    if "file_bytes" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        st.session_state.file_bytes = uploaded_file.read()
        st.session_state.mime = uploaded_file.type
        st.session_state.file_name = uploaded_file.name
        st.toast("Source Material Indexed!")

    st.title("🎓 Scholar Research Lab")
    col_v, col_a = st.columns(2)
    
    with col_v:
        if "video" in st.session_state.mime: 
            st.video(st.session_state.file_bytes)
        else: 
            st.info(f"📄 Active: {st.session_state.file_name}")
    
    with col_a:
        p = st.chat_input("Ask the Professor...")
        if p:
            with st.spinner("Scholar is thinking..."):
                ans = safe_scholar_call(p, st.session_state.file_bytes, st.session_state.mime, model_choice)
                if ans: st.chat_message("assistant").write(ans)
else:
    st.info("Upload a file to begin your research session.")

























