import streamlit as st
from google import genai
from google.genai import types
import os, io, time, random
from fpdf import FPDF
from gtts import gTTS

# --- 1. CORE ENGINE: High-Compatibility Initialization ---
def get_api_key():
    # Priority: Streamlit Secrets -> Environment Variables
    key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return key.strip() if key else None

api_key = get_api_key()

if not api_key:
    st.error("🔑 API Key Missing! Add 'GOOGLE_API_KEY' to your Streamlit Secrets or .env file.")
    st.stop()

# FORCE GLOBAL ENDPOINT: This prevents the 'Unreachable' routing error
client = genai.Client(
    api_key=api_key,
    http_options={'headers': {'x-goog-api-key': api_key}}
)

def safe_gemini_call(prompt, file_uri, mime_type, model_choice):
    """
    Final stabilized call logic using absolute model IDs and safety overrides.
    """
    # Use standard strings to let Google's load balancer handle routing
    model_map = {
        "Gemini 1.5 Flash": "gemini-1.5-flash",
        "Gemini 1.5 Pro": "gemini-1.5-pro",
        "Gemini 2.0 Flash": "gemini-2.0-flash-exp"
    }
    target_model = model_map.get(model_choice, "gemini-1.5-flash")
    
    try:
        # Create the file reference part
        file_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)
        
        # Generation with manual safety bypass to prevent 400 ClientErrors
        response = client.models.generate_content(
            model=target_model,
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an expert Research Professor. Provide rigorous academic analysis.",
                temperature=0.3,
                safety_settings=[
                    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                ]
            )
        )
        return response.text

    except Exception as e:
        # Emergency Ping Test: Checks if the API is reachable at all
        try:
            client.models.generate_content(model="gemini-1.5-flash", contents=["ping"])
            st.error(f"Professor is busy: File context error. Details: {str(e)[:100]}")
        except:
            st.error("Professor's Office unreachable: Check your API Key or Internet connection.")
        return None

# --- 2. UI STYLING (DARK ACADEMIA) ---
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .main .block-container { 
        background: rgba(255, 255, 255, 0.03); 
        border-radius: 20px; 
        padding: 2rem; 
        border: 1px solid rgba(255, 255, 255, 0.1); 
    }
    .badge { 
        display: inline-block; padding: 4px 12px; border-radius: 20px; 
        background: rgba(77, 171, 247, 0.2); border: 1px solid #4dabf7; 
        margin: 5px; color: #4dabf7; font-weight: 500; font-size: 0.8rem; 
    }
    .stButton>button { 
        border-radius: 8px; border: 1px solid #4dabf7; 
        background: #1c1f26; color: white; transition: 0.3s; width: 100%; 
    }
    .stButton>button:hover { background: #4dabf7; color: black; transform: translateY(-2px); }
    </style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    uploaded_file = st.file_uploader("Upload Source (PDF/MP4)", type=['pdf', 'mp4'])
    
    model_choice = st.selectbox("Intelligence Tier", ["Gemini 1.5 Flash", "Gemini 1.5 Pro", "Gemini 2.0 Flash"])
    
    if st.button("🧹 Reset Lab"):
        st.session_state.clear()
        st.rerun()

# --- 4. MAIN LOGIC ---
if uploaded_file:
    # UPLOAD & INDEXING: Using File API for stability
    if "file_uri" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.status("Professor is reading the source...") as status:
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                # Upload to Google servers
                google_file = client.files.upload(file=temp_path)
                
                # Wait for indexing to complete
                while google_file.state.name == "PROCESSING":
                    time.sleep(2)
                    google_file = client.files.get(name=google_file.name)
                
                st.session_state.file_uri = google_file.uri
                st.session_state.mime = uploaded_file.type
                st.session_state.file_name = uploaded_file.name
                st.session_state.topics = None
                status.update(label="Context Ready!", state="complete")
            except Exception as e:
                st.error(f"File Indexing Failed: {e}")
            finally:
                if os.path.exists(temp_path): os.remove(temp_path)

    st.title("🎓 Scholar Research Lab")

    # Keyword Generation
    if not st.session_state.get("topics"):
        res = safe_gemini_call("List 5 academic keywords for this material (comma-separated).", 
                               st.session_state.file_uri, st.session_state.mime, model_choice)
        st.session_state.topics = res.split(",") if res else ["Academic"]

    st.markdown(" ".join([f'<span class="badge">{t.strip()}</span>' for t in st.session_state.topics]), unsafe_allow_html=True)
    st.divider()

    col_v, col_a = st.columns([1, 1], gap="large")
    with col_v:
        if "video" in st.session_state.mime: 
            st.video(uploaded_file)
        else: 
            st.info(f"📄 Document Active: {uploaded_file.name}")

    with col_a:
        tabs = st.tabs(["💬 Chat", "🎙️ Audio", "📄 Report"])

        with tabs[0]: # CHAT
            chat_container = st.container(height=350)
            if "msgs" not in st.session_state: st.session_state.msgs = []
            for m in st.session_state.msgs: 
                chat_container.chat_message(m["role"]).write(m["content"])
            
            if p := st.chat_input("Ask the Professor..."):
                st.session_state.msgs.append({"role": "user", "content": p})
                chat_container.chat_message("user").write(p)
                
                ans = safe_gemini_call(p, st.session_state.file_uri, st.session_state.mime, model_choice)
                if ans:
                    chat_container.chat_message("assistant").write(ans)
                    st.session_state.msgs.append({"role": "assistant", "content": ans})

        with tabs[1]: # AUDIO
            if st.button("🔊 Generate Voice Summary"):
                with st.spinner("Preparing vocal remarks..."):
                    txt = safe_gemini_call("Summarize this in 3 sentences.", 
                                           st.session_state.file_uri, st.session_state.mime, model_choice)
                    if txt:
                        audio_io = io.BytesIO()
                        gTTS(text=txt, lang='en').write_to_fp(audio_io)
                        st.audio(audio_io.getvalue(), format="audio/mp3")

        with tabs[2]: # PDF REPORT
            if st.button("✨ Draft Thesis"):
                with st.spinner("Writing report..."):
                    rep = safe_gemini_call("Write a full academic report on this file.", 
                                           st.session_state.file_uri, st.session_state.mime, model_choice)
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
    st.info("Upload a PDF or Video in the sidebar to begin.")















