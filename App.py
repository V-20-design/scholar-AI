import streamlit as st
from google import genai
from google.genai import types
import os, io, time
from fpdf import FPDF
from gtts import gTTS

# --- 1. ENGINE: Global Regional Stability ---
def get_api_key():
    # Priority: Streamlit Secrets -> Environment Variables
    key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return key.strip() if key else None

api_key = get_api_key()

# THE FIX: Using the Global endpoint routing 
# In Kenya, specific versioned suffixes (like -002) can sometimes be restricted 
# to US-Central regions. We use the base canonical IDs here.
client = genai.Client(
    api_key=api_key,
    http_options={'headers': {'x-goog-api-key': api_key}}
)

def safe_gemini_call(prompt, file_uri, mime_type, model_choice):
    # Mapping to Global Canonical IDs for better regional availability
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
                system_instruction="You are 'The Scholar,' an expert Research Professor. Answer with academic rigor.",
                temperature=0.7
            )
        )
        return response.text
    except Exception as e:
        # Final fallback: If even the base ID fails, we try the newest 1.5 Flash alias
        if "404" in str(e) or "unavailable" in str(e).lower():
            try:
                # This specific alias is often the 'Global' default
                res = client.models.generate_content(
                    model="models/gemini-1.5-flash", 
                    contents=[file_part, prompt]
                )
                return res.text
            except:
                st.error("Regional Access Error: Google has restricted this model in your current region.")
        else:
            st.error(f"Professor Busy: {str(e)[:150]}")
        return None

# --- 2. UI CONFIG & STYLING ---
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .main .block-container { 
        background: rgba(255, 255, 255, 0.03); 
        border-radius: 20px; padding: 2rem; 
        border: 1px solid rgba(255, 255, 255, 0.1); 
    }
    .stButton>button { 
        border-radius: 8px; border: 1px solid #4dabf7; 
        background: #1c1f26; color: white; transition: 0.3s; width: 100%; 
    }
    .stButton>button:hover { background: #4dabf7; color: black; }
    </style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    uploaded_file = st.file_uploader("Upload Source (PDF/MP4)", type=['pdf', 'mp4'])
    
    model_choice = st.selectbox("Intelligence Tier", [
        "Gemini 1.5 Flash", 
        "Gemini 1.5 Pro", 
        "Gemini 2.0 Flash"
    ])
    
    if st.button("🧹 Clear & Reset"):
        st.session_state.clear()
        st.rerun()

# --- 4. FILE PROCESSING ---
if uploaded_file:
    if "file_uri" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.status("Professor is indexing the context...") as status:
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                # Upload to Google server via File API
                google_file = client.files.upload(file=temp_path)
                
                # Check processing status
                while google_file.state.name == "PROCESSING":
                    time.sleep(2)
                    google_file = client.files.get(name=google_file.name)
                
                st.session_state.file_uri = google_file.uri
                st.session_state.mime = uploaded_file.type
                st.session_state.file_name = uploaded_file.name
                status.update(label="Context Ready!", state="complete")
            except Exception as e:
                st.error(f"Handshake Failed: {e}")
            finally:
                if os.path.exists(temp_path): os.remove(temp_path)

    st.title("🎓 Scholar Research Lab")
    st.divider()

    col_v, col_a = st.columns([1, 1], gap="large")
    with col_v:
        if "video" in st.session_state.mime: 
            st.video(uploaded_file)
        else: 
            st.info(f"📄 Document Active: {uploaded_file.name}")

    with col_a:
        tabs = st.tabs(["💬 Chat", "🔊 Audio", "📄 Thesis"])

        with tabs[0]: # CHAT
            if "msgs" not in st.session_state: st.session_state.msgs = []
            chat_container = st.container(height=350)
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
            if st.button("🎙️ Generate Audio Summary"):
                with st.spinner("Preparing remarks..."):
                    txt = safe_gemini_call("Summarize this in 2 sentences.", 
                                           st.session_state.file_uri, st.session_state.mime, model_choice)
                    if txt:
                        audio_io = io.BytesIO()
                        gTTS(text=txt, lang='en').write_to_fp(audio_io)
                        st.audio(audio_io.getvalue(), format="audio/mp3")

        with tabs[2]: # REPORT
            if st.button("✨ Draft Formal Report"):
                with st.spinner("Compiling thesis..."):
                    rep = safe_gemini_call("Write a detailed academic report.", 
                                           st.session_state.file_uri, st.session_state.mime, model_choice)
                    if rep:
                        st.markdown(rep)
                        st.session_state.last_report = rep
            
            if "last_report" in st.session_state:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=11)
                pdf.multi_cell(0, 10, txt=st.session_state.last_report.encode('latin-1', 'replace').decode('latin-1'))
                st.download_button("📥 Download Report PDF", pdf.output(dest='S'), "Scholar_Report.pdf")
else:
    st.info("Upload a file in the sidebar to begin.")




















