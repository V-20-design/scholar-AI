import streamlit as st
from google import genai
from google.genai import types
import os, io, time
from fpdf import FPDF
from gtts import gTTS

# --- 1. ENGINE: Vertex AI Migration ---
def get_config():
    # To use Vertex AI, you need your Google Cloud Project ID
    return {
        "api_key": st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        "project_id": st.secrets.get("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT"),
        "location": "us-central1" # Stable global location
    }

cfg = get_config()

# THE REGIONAL FIX: Use Vertex AI mode
# Setting vertexai=True bypasses the AI Studio regional restrictions
client = genai.Client(
    api_key=cfg["api_key"],
    vertexai=True,
    project=cfg["project_id"],
    location=cfg["location"]
)

def safe_gemini_call(prompt, file_uri, mime_type, model_choice):
    # Vertex AI uses simplified model naming
    model_map = {
        "Gemini 1.5 Flash": "gemini-1.5-flash",
        "Gemini 1.5 Pro": "gemini-1.5-pro",
        "Gemini 2.0 Flash": "gemini-2.0-flash-exp"
    }
    target_model = model_map.get(model_choice, "gemini-1.5-flash")
    
    try:
        file_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)
        response = client.models.generate_content(
            model=target_model,
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

# --- 2. UI STYLING ---
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

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    st.info(f"📍 Region: {cfg['location']} (Vertex AI)")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    model_choice = st.selectbox("Intelligence Tier", ["Gemini 1.5 Flash", "Gemini 1.5 Pro", "Gemini 2.0 Flash"])
    if st.button("🧹 Clear & Reset"):
        st.session_state.clear()
        st.rerun()

# --- 4. THE HANDSHAKE ---
if uploaded_file:
    if "file_uri" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.status("Linking Context via Vertex...") as status:
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            try:
                # Vertex AI handles file uploads through a similar File API
                g_file = client.files.upload(file=temp_path)
                while g_file.state.name == "PROCESSING":
                    time.sleep(4)
                    g_file = client.files.get(name=g_file.name)
                
                st.session_state.file_uri = g_file.uri
                st.session_state.mime = uploaded_file.type
                st.session_state.file_name = uploaded_file.name
                status.update(label="Handshake Successful!", state="complete")
            except Exception as e:
                st.error(f"Handshake Failed: {str(e)}")
                st.stop()
            finally:
                if os.path.exists(temp_path): os.remove(temp_path)

    # --- 5. DASHBOARD ---
    st.title("🎓 Scholar Research Lab")
    col_v, col_a = st.columns([1, 1], gap="large")

    with col_v:
        if "video" in st.session_state.mime: st.video(uploaded_file)
        else: st.info(f"📄 Active File: {st.session_state.file_name}")

    with col_a:
        tabs = st.tabs(["💬 Chat", "🎙️ Audio", "📄 Thesis"])
        with tabs[0]:
            if "msgs" not in st.session_state: st.session_state.msgs = []
            for m in st.session_state.msgs: st.chat_message(m["role"]).write(m["content"])
            if p := st.chat_input("Ask the Professor..."):
                st.session_state.msgs.append({"role": "user", "content": p})
                st.chat_message("user").write(p)
                ans = safe_gemini_call(p, st.session_state.file_uri, st.session_state.mime, model_choice)
                if ans:
                    st.chat_message("assistant").write(ans)
                    st.session_state.msgs.append({"role": "assistant", "content": ans})
        
        with tabs[1]:
            if st.button("🔊 Voice Summary"):
                txt = safe_gemini_call("Summary in 2 sentences.", st.session_state.file_uri, st.session_state.mime, model_choice)
                if txt:
                    audio_io = io.BytesIO()
                    gTTS(text=txt, lang='en').write_to_fp(audio_io)
                    st.audio(audio_io.getvalue())

        with tabs[2]:
            if st.button("✨ Draft Thesis"):
                rep = safe_gemini_call("Generate a formal report.", st.session_state.file_uri, st.session_state.mime, model_choice)
                if rep:
                    st.markdown(rep)
                    st.session_state.last_rep = rep
            if "last_rep" in st.session_state:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=11)
                pdf.multi_cell(0, 10, txt=st.session_state.last_rep.encode('latin-1', 'replace').decode('latin-1'))
                st.download_button("📥 Download PDF", pdf.output(dest='S'), "Report.pdf")
else:
    st.info("Upload a file to begin.")






















