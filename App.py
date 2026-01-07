import streamlit as st
from google import genai
from google.genai import types
import os, io, time, random
from fpdf import FPDF
from gtts import gTTS

# --- 1. ENGINE: The Resilient Professor ---
def get_api_key():
    # Priority: Streamlit Secrets -> Environment Variables
    key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return key.strip() if key else None

# Initialize Client
api_key = get_api_key()
if not api_key:
    st.error("Missing API Key. Please add GOOGLE_API_KEY to secrets or .env")
    st.stop()

client = genai.Client(api_key=api_key)

def safe_gemini_call(prompt, file_uri, mime_type, model_choice):
    """
    Handles file-based generation with fallback logic for endpoint stability.
    """
    # 2026 Canonical Stable IDs
    model_map = {
        "Gemini 1.5 Flash (Fast)": "gemini-1.5-flash-002",
        "Gemini 1.5 Pro (Deep)": "gemini-1.5-pro-002",
        "Gemini 2.0 Flash (Latest)": "gemini-2.0-flash-exp"
    }
    target_model = model_map.get(model_choice, "gemini-1.5-flash-002")
    
    try:
        # Reference the file already uploaded to Google
        file_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)
        
        response = client.models.generate_content(
            model=target_model,
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an expert Research Professor. Answer with academic rigor.",
                safety_settings=[
                    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE')
                ],
                temperature=0.7
            )
        )
        return response.text
    except Exception as e:
        err_str = str(e).lower()
        # Fallback if specific version -002 is not reachable
        if "404" in err_str or "not reachable" in err_str:
            try:
                st.warning("Switching to base model tier...")
                res = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=[types.Part.from_uri(file_uri=file_uri, mime_type=mime_type), prompt]
                )
                return res.text
            except:
                st.error("Professor's Office is closed: API Endpoints unreachable.")
        else:
            st.error(f"Logic Error: {str(e)[:150]}")
        return None

# --- 2. UI CONFIG & CSS ---
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .main .block-container { background: rgba(255, 255, 255, 0.03); border-radius: 20px; padding: 2rem; border: 1px solid rgba(255, 255, 255, 0.1); }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; background: rgba(77, 171, 247, 0.2); border: 1px solid #4dabf7; margin: 5px; color: #4dabf7; font-weight: 500; font-size: 0.8rem; }
    .stButton>button { border-radius: 8px; border: 1px solid #4dabf7; background: #1c1f26; color: white; transition: 0.3s; width: 100%; }
    .stButton>button:hover { background: #4dabf7; color: black; transform: translateY(-2px); }
    </style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    uploaded_file = st.file_uploader("Upload Source (PDF/MP4)", type=['pdf', 'mp4'])
    
    model_choice = st.selectbox("Intelligence Tier", [
        "Gemini 1.5 Flash (Fast)", 
        "Gemini 1.5 Pro (Deep)", 
        "Gemini 2.0 Flash (Latest)"
    ])
    
    if st.button("🧹 Clear & Reset"):
        # Cleanup uploaded files from Google servers if needed
        st.session_state.clear()
        st.rerun()

# --- 4. FILE PROCESSING ---
if uploaded_file:
    # Use File API for stability instead of sending raw bytes every time
    if "file_uri" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.status("Professor is indexing the context...") as status:
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Upload to Google server
            google_file = client.files.upload(file=temp_path)
            
            # Critical: Wait for File API to process (especially for video)
            while google_file.state.name == "PROCESSING":
                time.sleep(2)
                google_file = client.files.get(name=google_file.name)
            
            st.session_state.file_uri = google_file.uri
            st.session_state.mime = uploaded_file.type
            st.session_state.file_name = uploaded_file.name
            st.session_state.topics = None # Reset topics for new file
            os.remove(temp_path)
            status.update(label="Context Ready!", state="complete")

    st.title("🎓 Scholar Research Lab")

    # Generate Topics only once
    if not st.session_state.get("topics"):
        res = safe_gemini_call("List 5 academic keywords for this material (comma-separated).", 
                               st.session_state.file_uri, st.session_state.mime, model_choice)
        st.session_state.topics = res.split(",") if res else ["Ready"]

    st.markdown(" ".join([f'<span class="badge">{t.strip()}</span>' for t in st.session_state.topics]), unsafe_allow_html=True)
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
            st.subheader("Vocal Summary")
            if st.button("🎙️ Generate Audio Summary"):
                with st.spinner("Professor is preparing remarks..."):
                    txt = safe_gemini_call("Summarize this in 3 clear sentences for a podcast.", 
                                           st.session_state.file_uri, st.session_state.mime, model_choice)
                    if txt:
                        tts = gTTS(text=txt, lang='en')
                        audio_io = io.BytesIO()
                        tts.write_to_fp(audio_io)
                        st.audio(audio_io.getvalue(), format="audio/mp3")

        with tabs[2]: # REPORT
            st.subheader("Academic Thesis")
            if st.button("✨ Draft Formal Report"):
                with st.spinner("Compiling thesis..."):
                    rep = safe_gemini_call("Write a detailed academic report including Introduction, Key Findings, and Conclusion.", 
                                           st.session_state.file_uri, st.session_state.mime, model_choice)
                    if rep:
                        st.markdown(rep)
                        st.session_state.last_report = rep
            
            if "last_report" in st.session_state:
                # Helper for PDF generation (FPDF)
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=11)
                pdf.multi_cell(0, 10, txt=st.session_state.last_report.encode('latin-1', 'replace').decode('latin-1'))
                st.download_button("📥 Download Report PDF", pdf.output(dest='S'), "Scholar_Report.pdf")
else:
    st.info("Please upload a research paper or educational video in the sidebar to begin.")














