import streamlit as st
from google import genai
from google.genai import types
import os, io, time, random
from fpdf import FPDF
from gtts import gTTS

# --- 1. ENGINE: The Resilient Professor ---
def get_api_key():
    return st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=get_api_key())

def safe_gemini_call(prompt, bytes_data, mime_type, model_choice):
    """
    Handles 429 (Rate Limit), 404 (Model ID), and 400 (MIME) errors.
    """
    max_retries = 3
    delay = 5 
    
    # Use the specific canonical IDs for the GenAI SDK
    # Map friendly names to actual API identifiers
    model_map = {
        "Gemini 1.5 Flash (Fast)": "gemini-1.5-flash",
        "Gemini 1.5 Pro (Deep)": "gemini-1.5-pro",
        "Gemini 2.0 Flash (Latest)": "gemini-2.0-flash"
    }
    target_model = model_map.get(model_choice, "gemini-1.5-flash")
    
    for attempt in range(max_retries):
        try:
            # Re-verify MIME Type logic
            clean_mime = "application/pdf" if "pdf" in mime_type.lower() else "video/mp4"
            file_part = types.Part.from_bytes(data=bytes_data, mime_type=clean_mime)
            
            response = client.models.generate_content(
                model=target_model,
                contents=[file_part, prompt],
                config=types.GenerateContentConfig(
                    system_instruction="You are 'The Scholar,' an expert Research Professor. Answer with academic rigor."
                )
            )
            return response.text
        
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg:
                st.warning(f"Quota reached. Retrying in {delay}s...")
                time.sleep(delay + random.uniform(0, 1))
                delay *= 2 
            elif "404" in err_msg:
                # If the specific version fails, fallback to the base version
                st.error(f"Endpoint Error: {target_model} not reachable. Defaulting to stable tier...")
                target_model = "gemini-1.5-flash"
            else:
                st.error(f"Professor's Office Error: {err_msg[:100]}")
                return None
    return None

# --- 2. UI CONFIG ---
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .main .block-container { background: rgba(255, 255, 255, 0.03); border-radius: 20px; padding: 2rem; border: 1px solid rgba(255, 255, 255, 0.1); }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; background: rgba(77, 171, 247, 0.2); border: 1px solid #4dabf7; margin: 5px; color: #4dabf7; font-weight: 500; font-size: 0.8rem; }
    .stButton>button { border-radius: 8px; border: 1px solid #4dabf7; background: #1c1f26; color: white; transition: 0.3s; }
    .stButton>button:hover { background: #4dabf7; color: black; }
    </style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    uploaded_file = st.file_uploader("Upload Source (PDF/MP4)", type=['pdf', 'mp4'])
    
    # Using friendly names to avoid ID confusion
    model_choice = st.selectbox("Intelligence Tier", [
        "Gemini 1.5 Flash (Fast)", 
        "Gemini 1.5 Pro (Deep)", 
        "Gemini 2.0 Flash (Latest)"
    ])
    
    if st.button("🧹 Clear & Reset"):
        st.session_state.clear()
        st.rerun()

# --- 4. MAIN DASHBOARD ---
if uploaded_file:
    if "raw_data" not in st.session_state:
        st.session_state.raw_data = uploaded_file.getvalue()
        st.session_state.mime = uploaded_file.type
        st.rerun()

    st.title("🎓 Scholar Research Lab")

    # --- TOPIC MAP ---
    if "topics" not in st.session_state:
        with st.spinner("Professor is reading..."):
            res = safe_gemini_call("List 5 academic keywords for this material (comma-separated).", 
                                   st.session_state.raw_data, st.session_state.mime, model_choice)
            st.session_state.topics = res.split(",") if res else ["Ready"]

    st.markdown(" ".join([f'<span class="badge">{t}</span>' for t in st.session_state.topics]), unsafe_allow_html=True)
    st.divider()

    col_v, col_a = st.columns([1, 1], gap="large")
    with col_v:
        if "video" in st.session_state.mime: 
            st.video(uploaded_file)
        else: 
            st.info(f"📄 Document Loaded: {uploaded_file.name}")

    with col_a:
        tabs = st.tabs(["💬 Chat", "🔊 Summary", "📄 Thesis"])

        with tabs[0]: # CHAT
            if "msgs" not in st.session_state: st.session_state.msgs = []
            for m in st.session_state.msgs: st.chat_message(m["role"]).write(m["content"])
            
            if p := st.chat_input("Ask the Professor..."):
                st.session_state.msgs.append({"role": "user", "content": p})
                st.chat_message("user").write(p)
                ans = safe_gemini_call(p, st.session_state.raw_data, st.session_state.mime, model_choice)
                if ans:
                    st.chat_message("assistant").write(ans)
                    st.session_state.msgs.append({"role": "assistant", "content": ans})

        with tabs[1]: # AUDIO
            if st.button("🎙️ Generate Audio Summary"):
                with st.spinner("Professor is speaking..."):
                    txt = safe_gemini_call("Summarize in 2 sentences.", st.session_state.raw_data, st.session_state.mime, model_choice)
                    if txt:
                        tts = gTTS(text=txt, lang='en')
                        audio_io = io.BytesIO()
                        tts.write_to_fp(audio_io)
                        st.audio(audio_io.getvalue(), format="audio/mp3")

        with tabs[2]: # REPORT
            if st.button("✨ Draft Thesis"):
                with st.spinner("Compiling academic report..."):
                    rep = safe_gemini_call("Write a full academic report.", st.session_state.raw_data, st.session_state.mime, model_choice)
                    if rep:
                        st.markdown(rep)
else:
    st.info("Upload a file to begin.")













