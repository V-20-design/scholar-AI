import streamlit as st
from google import genai
from google.genai import types
import os, io, time
from fpdf import FPDF
from gtts import gTTS

# --- 1. ENGINE: Professional Vertex AI Auth ---
def get_config():
    return {
        "api_key": st.secrets.get("GOOGLE_API_KEY"),
        "project_id": st.secrets.get("GOOGLE_CLOUD_PROJECT"),
        "location": "us-central1"
    }

cfg = get_config()

# UI STYLING
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")

# INITIALIZE CLIENT (VERTEX MODE)
@st.cache_resource
def init_client():
    if not cfg["api_key"] or not cfg["project_id"]:
        return None
    try:
        # Vertex AI mode (no project/location conflict with API Key in 2026 SDK)
        return genai.Client(
            api_key=cfg["api_key"],
            vertexai=True,
            project=cfg["project_id"],
            location=cfg["location"]
        )
    except Exception as e:
        st.error(f"Auth Error: {e}")
        return None

client = init_client()

if not client:
    st.warning("⚠️ Action Required: Add credentials to Streamlit Secrets.")
    st.stop()

# --- NEW: FIXED FILE HANDLING FOR VERTEX AI ---
def safe_gemini_call(prompt, file_bytes, mime_type, model_choice):
    model_map = {"Gemini 1.5 Flash": "gemini-1.5-flash", "Gemini 1.5 Pro": "gemini-1.5-pro"}
    try:
        # Instead of a URI from an upload, we send the bytes directly
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        
        response = client.models.generate_content(
            model=model_map.get(model_choice, "gemini-1.5-flash"),
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
    st.success(f"Project: {cfg['project_id']}")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    model_choice = st.selectbox("Intelligence Tier", ["Gemini 1.5 Flash", "Gemini 1.5 Pro"])
    if st.button("🧹 Clear Session"):
        st.session_state.clear()
        st.rerun()

# --- MAIN INTERFACE ---
if uploaded_file:
    # We store the bytes in session state instead of a file URI
    if "file_bytes" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        st.session_state.file_bytes = uploaded_file.read()
        st.session_state.mime = uploaded_file.type
        st.session_state.file_name = uploaded_file.name
        st.toast("Document Indexed!")

    st.title("🎓 Scholar Research Lab")
    col_v, col_a = st.columns(2)
    
    with col_v:
        if "video" in st.session_state.mime: 
            st.video(st.session_state.file_bytes)
        else: 
            st.info(f"📄 Active: {st.session_state.file_name}")
    
    with col_a:
        tabs = st.tabs(["💬 Chat", "🎙️ Audio", "📄 Thesis"])
        with tabs[0]:
            if p := st.chat_input("Ask the Professor..."):
                ans = safe_gemini_call(p, st.session_state.file_bytes, st.session_state.mime, model_choice)
                if ans: st.chat_message("assistant").write(ans)
        
        with tabs[1]:
            if st.button("🔊 Voice Summary"):
                txt = safe_gemini_call("Summarize in 2 sentences.", st.session_state.file_bytes, st.session_state.mime, model_choice)
                if txt: st.audio(io.BytesIO(gTTS(text=txt, lang='en')._p_write_to_fp()))
        
        with tabs[2]:
            if st.button("✨ Draft Thesis"):
                rep = safe_gemini_call("Draft a formal report.", st.session_state.file_bytes, st.session_state.mime, model_choice)
                if rep:
                    st.markdown(rep)
                    pdf = FPDF()
                    pdf.add_page(); pdf.set_font("Arial", size=11)
                    pdf.multi_cell(0, 10, txt=rep.encode('latin-1', 'replace').decode('latin-1'))
                    st.download_button("📥 Download PDF", pdf.output(dest='S'), "Report.pdf")
else:
    st.info("Upload a file to begin.")

























