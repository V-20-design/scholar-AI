import streamlit as st
from google import genai
from google.genai import types
import os, io, time
from fpdf import FPDF
from gtts import gTTS

# --- 1. DIAGNOSTIC & ENGINE ---
def get_api_key():
    return st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

api_key = get_api_key()

# THE FIX: Using a more permissive connection configuration
client = genai.Client(
    api_key=api_key,
    http_options={
        'headers': {'x-goog-api-key': api_key},
        'timeout': 30  # Increased timeout for slow cloud nodes
    }
)

def safe_gemini_call(prompt, file_uri, mime_type, model_choice):
    # Mapping to global canonical IDs
    model_map = {
        "Gemini 1.5 Flash": "gemini-1.5-flash",
        "Gemini 1.5 Pro": "gemini-1.5-pro",
        "Gemini 2.0 Flash": "gemini-2.0-flash-exp"
    }
    target_model = model_map.get(model_choice, "gemini-1.5-flash")
    
    try:
        # Step 1: Attempt generation
        file_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)
        response = client.models.generate_content(
            model=target_model,
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an expert Professor.",
                temperature=0.3
            )
        )
        return response.text

    except Exception as e:
        # DIAGNOSTIC LOGIC
        err_msg = str(e).lower()
        if "api_key_invalid" in err_msg or "403" in err_msg:
            st.error("🚫 API Key Rejected: Check your Google AI Studio billing/quota.")
        elif "404" in err_msg:
            st.error(f"📍 Model {target_model} not found in your region.")
        elif "deadline" in err_msg or "timeout" in err_msg:
            st.error("⏳ Connection Timed Out: Google's servers are slow right now.")
        else:
            st.error(f"📡 Network Error: {str(e)[:100]}")
        return None

# --- 2. UI STYLING ---
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .main .block-container { background: rgba(255, 255, 255, 0.03); border-radius: 20px; padding: 2rem; border: 1px solid rgba(255, 255, 255, 0.1); }
    .stButton>button { border-radius: 8px; border: 1px solid #4dabf7; background: #1c1f26; color: white; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    if not api_key:
        st.warning("No API Key found. Add GOOGLE_API_KEY to Secrets.")
    
    uploaded_file = st.file_uploader("Upload Source (PDF/MP4)", type=['pdf', 'mp4'])
    model_choice = st.selectbox("Intelligence Tier", ["Gemini 1.5 Flash", "Gemini 1.5 Pro", "Gemini 2.0 Flash"])
    
    if st.button("🧹 Reset Lab"):
        st.session_state.clear()
        st.rerun()

# --- 4. FILE UPLOAD LOGIC ---
if uploaded_file:
    if "file_uri" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.status("Linking Context...") as status:
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                # Uploading file to Google's temporary storage
                google_file = client.files.upload(file=temp_path)
                
                # Check processing status
                while google_file.state.name == "PROCESSING":
                    time.sleep(2)
                    google_file = client.files.get(name=google_file.name)
                
                st.session_state.file_uri = google_file.uri
                st.session_state.mime = uploaded_file.type
                st.session_state.file_name = uploaded_file.name
                status.update(label="Handshake Complete!", state="complete")
            except Exception as e:
                st.error(f"Handshake Failed: {e}")
                st.stop()
            finally:
                if os.path.exists(temp_path): os.remove(temp_path)

    st.title("🎓 Scholar Research Lab")
    
    col_v, col_a = st.columns([1, 1], gap="large")
    with col_v:
        if "video" in st.session_state.mime: 
            st.video(uploaded_file)
        else: 
            st.info(f"📄 Document Loaded: {uploaded_file.name}")

    with col_a:
        tabs = st.tabs(["💬 Chat", "🎙️ Audio", "📄 Thesis"])
        
        with tabs[0]:
            if "msgs" not in st.session_state: st.session_state.msgs = []
            container = st.container(height=300)
            for m in st.session_state.msgs: container.chat_message(m["role"]).write(m["content"])
            
            if p := st.chat_input("Ask the Professor..."):
                st.session_state.msgs.append({"role": "user", "content": p})
                container.chat_message("user").write(p)
                ans = safe_gemini_call(p, st.session_state.file_uri, st.session_state.mime, model_choice)
                if ans:
                    container.chat_message("assistant").write(ans)
                    st.session_state.msgs.append({"role": "assistant", "content": ans})

        with tabs[1]:
            if st.button("🔊 Voice Summary"):
                txt = safe_gemini_call("Summarize this in 3 sentences.", st.session_state.file_uri, st.session_state.mime, model_choice)
                if txt:
                    audio_io = io.BytesIO()
                    gTTS(text=txt, lang='en').write_to_fp(audio_io)
                    st.audio(audio_io.getvalue())

        with tabs[2]:
            if st.button("✨ Draft Thesis"):
                rep = safe_gemini_call("Write an academic report.", st.session_state.file_uri, st.session_state.mime, model_choice)
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
    st.info("Upload a file to open the Professor's Office.")
















