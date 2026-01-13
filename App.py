import streamlit as st
from google import genai
from google.genai import types
import os, io, time
from fpdf import FPDF
from gtts import gTTS

# --- 1. ENGINE: Vertex AI Configuration ---
def get_config():
    # Pulling from Streamlit Secrets
    project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT")
    api_key = st.secrets.get("GOOGLE_API_KEY")
    return {"api_key": api_key, "project_id": project_id, "location": "us-central1"}

cfg = get_config()

# UI STYLING
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .main .block-container { 
        background: rgba(255, 255, 255, 0.03); 
        border-radius: 15px; padding: 2rem; 
        border: 1px solid rgba(255, 255, 255, 0.1); 
    }
    .stButton>button { border-radius: 8px; border: 1px solid #4dabf7; background: #1c1f26; color: white; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# BLOCKER: Configuration Check
if not cfg["project_id"] or not cfg["api_key"]:
    st.title("🎓 ScholarAI Setup")
    st.warning("⚠️ Action Required: Add credentials to Streamlit Secrets.")
    st.info("Check the chat for instructions on finding your Project ID.")
    st.stop()

# INITIALIZE CLIENT (VERTEX MODE)
try:
    client = genai.Client(
        api_key=cfg["api_key"], 
        vertexai=True, 
        project=cfg["project_id"], 
        location=cfg["location"]
    )
except Exception as e:
    st.error(f"Initialization Failed: {e}")
    st.stop()

def safe_gemini_call(prompt, file_uri, mime_type, model_choice):
    model_map = {"Gemini 1.5 Flash": "gemini-1.5-flash", "Gemini 1.5 Pro": "gemini-1.5-pro"}
    try:
        file_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)
        response = client.models.generate_content(
            model=model_map.get(model_choice, "gemini-1.5-flash"),
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an expert Professor. Provide citations.",
                temperature=0.3
            )
        )
        return response.text
    except Exception as e:
        st.error(f"Request Error: {str(e)[:150]}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    st.success(f"Project: {cfg['project_id']}")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    model_choice = st.selectbox("Model", ["Gemini 1.5 Flash", "Gemini 1.5 Pro"])
    if st.button("🧹 Reset Session"):
        st.session_state.clear()
        st.rerun()

# --- MAIN INTERFACE ---
if uploaded_file:
    if "file_uri" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.status("Professor is reading...") as status:
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f: f.write(uploaded_file.getbuffer())
            try:
                g_file = client.files.upload(file=temp_path)
                while g_file.state.name == "PROCESSING":
                    time.sleep(4)
                    g_file = client.files.get(name=g_file.name)
                st.session_state.file_uri = g_file.uri
                st.session_state.mime = uploaded_file.type
                st.session_state.file_name = uploaded_file.name
                status.update(label="Analysis Ready!", state="complete")
            finally:
                if os.path.exists(temp_path): os.remove(temp_path)

    st.title("🎓 Scholar Research Lab")
    col_v, col_a = st.columns(2)
    with col_v:
        if "video" in st.session_state.mime: st.video(uploaded_file)
        else: st.info(f"📄 Active: {uploaded_file.name}")
    
    with col_a:
        tabs = st.tabs(["💬 Chat", "🎙️ Audio", "📄 Thesis"])
        with tabs[0]:
            if p := st.chat_input("Ask the Professor..."):
                ans = safe_gemini_call(p, st.session_state.file_uri, st.session_state.mime, model_choice)
                if ans: st.chat_message("assistant").write(ans)
        
        with tabs[1]:
            if st.button("🔊 Generate Summary"):
                txt = safe_gemini_call("Summarize in 2 sentences.", st.session_state.file_uri, st.session_state.mime, model_choice)
                if txt: st.audio(io.BytesIO(gTTS(text=txt, lang='en')._p_write_to_fp()))
        
        with tabs[2]:
            if st.button("✨ Draft Report"):
                rep = safe_gemini_call("Draft a formal report.", st.session_state.file_uri, st.session_state.mime, model_choice)
                if rep:
                    st.markdown(rep)
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=11)
                    pdf.multi_cell(0, 10, txt=rep.encode('latin-1', 'replace').decode('latin-1'))
                    st.download_button("📥 Download PDF", pdf.output(dest='S'), "Report.pdf")
else:
    st.info("Upload a source file to start the lab.")
























