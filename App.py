import streamlit as st
from google import genai
from google.genai import types
import os, io, time
from fpdf import FPDF
from gtts import gTTS

# --- 1. CONFIGURATION ---
def get_config():
    # We pull these from your Streamlit Secrets
    return {
        "api_key": st.secrets.get("GOOGLE_API_KEY"),
        "project_id": st.secrets.get("GOOGLE_CLOUD_PROJECT"), # e.g. gen-lang-client-xxx
        "location": "us-central1"
    }

cfg = get_config()

# UI STYLING
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .stButton>button { border-radius: 8px; border: 1px solid #4dabf7; background: #1c1f26; color: white; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- 2. THE FIXED INITIALIZER ---
@st.cache_resource
def init_client():
    if not cfg["api_key"]:
        st.error("🔑 GOOGLE_API_KEY is missing in Secrets!")
        return None
    
    try:
        # TO FIX THE ERROR: 
        # If we use an API Key, we do NOT pass project/location in the same call.
        # This uses 'Express Mode' which is stable for Kenya.
        client = genai.Client(
            api_key=cfg["api_key"],
            vertexai=True # This tells the SDK to use Vertex AI endpoints
        )
        return client
    except Exception as e:
        st.error(f"Initialization Failed: {e}")
        return None

client = init_client()

# BLOCKER: If client fails, stop the app
if not client:
    st.stop()

def safe_gemini_call(prompt, file_uri, mime_type, model_choice):
    model_map = {"Gemini 1.5 Flash": "gemini-1.5-flash", "Gemini 1.5 Pro": "gemini-1.5-pro"}
    try:
        file_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)
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

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    st.success("Connected to Vertex AI (Express)")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    model_choice = st.selectbox("Intelligence Tier", ["Gemini 1.5 Flash", "Gemini 1.5 Pro"])
    if st.button("🧹 Clear Session"):
        st.session_state.clear()
        st.rerun()

# --- 4. MAIN INTERFACE ---
if uploaded_file:
    if "file_uri" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.status("Analyzing material...") as status:
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
                status.update(label="Ready!", state="complete")
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
            if st.button("🔊 Voice Summary"):
                txt = safe_gemini_call("Summarize in 2 sentences.", st.session_state.file_uri, st.session_state.mime, model_choice)
                if txt: st.audio(io.BytesIO(gTTS(text=txt, lang='en')._p_write_to_fp()))
        
        with tabs[2]:
            if st.button("✨ Draft Thesis"):
                rep = safe_gemini_call("Draft a formal report.", st.session_state.file_uri, st.session_state.mime, model_choice)
                if rep:
                    st.markdown(rep)
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=11)
                    pdf.multi_cell(0, 10, txt=rep.encode('latin-1', 'replace').decode('latin-1'))
                    st.download_button("📥 Download PDF", pdf.output(dest='S'), "Report.pdf")
else:
    st.info("Upload a file to begin.")

























