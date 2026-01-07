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
    Handles 429 errors using Exponential Backoff.
    If the API is exhausted, it waits and retries up to 3 times.
    """
    max_retries = 3
    delay = 5  # Initial wait time in seconds
    
    for attempt in range(max_retries):
        try:
            # Clean MIME type for strict Google validation
            clean_mime = "application/pdf" if "pdf" in mime_type.lower() else "video/mp4"
            file_part = types.Part.from_bytes(data=bytes_data, mime_type=clean_mime)
            
            response = client.models.generate_content(
                model=model_choice,
                contents=[file_part, prompt],
                config=types.GenerateContentConfig(
                    system_instruction="You are 'The Scholar,' an expert Professor. Use LaTeX for math."
                )
            )
            return response.text
        
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "exhausted" in err_msg.lower():
                # This is the Quota Error
                st.warning(f"Professor is busy (Rate Limit). Retrying in {delay}s... ({attempt + 1}/{max_retries})")
                time.sleep(delay + random.uniform(0, 1)) # Add a little jitter
                delay *= 2 # Double the wait time for the next try
            else:
                # This is a different error (like a 500 or network issue)
                st.error(f"Professor's Office Error: {err_msg[:100]}")
                return None
    
    st.error("The Professor is currently overwhelmed. Please wait 1-2 minutes before trying again.")
    return None

# --- 2. UI & LAYOUT ---
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .main .block-container { background: rgba(255, 255, 255, 0.03); border-radius: 20px; padding: 2rem; border: 1px solid rgba(255, 255, 255, 0.1); }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; background: rgba(77, 171, 247, 0.2); border: 1px solid #4dabf7; margin: 5px; color: #4dabf7; font-size: 0.8rem; }
    </style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    uploaded_file = st.file_uploader("Upload Source (PDF/MP4)", type=['pdf', 'mp4'])
    # RECOMMENDATION: 1.5 Flash is the most stable for Free Tier RPD/TPM
    model_choice = st.selectbox("Intelligence Tier", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"])
    if st.button("🧹 Clear & Reset"):
        st.session_state.clear()
        st.rerun()

# --- 4. MAIN DASHBOARD ---
if uploaded_file:
    # Buffer safety: ensure data is locked in session state
    if "raw_data" not in st.session_state:
        st.session_state.raw_data = uploaded_file.getvalue()
        st.session_state.mime = uploaded_file.type
        st.rerun()

    st.title("🎓 Scholar Research Lab")

    # --- TOPIC MAP ---
    if "topics" not in st.session_state:
        with st.spinner("Professor is reading..."):
            res = safe_gemini_call("List 5 keywords for this material (comma-separated).", 
                                   st.session_state.raw_data, st.session_state.mime, model_choice)
            st.session_state.topics = res.split(",") if res else ["Ready for Analysis"]

    # Display Badges
    st.markdown(" ".join([f'<span class="badge">{t}</span>' for t in st.session_state.topics]), unsafe_allow_html=True)
    st.divider()

    col_v, col_a = st.columns([1, 1], gap="large")
    with col_v:
        if "video" in st.session_state.mime: st.video(uploaded_file)
        else: st.info(f"📄 Document Loaded: {uploaded_file.name}")

    with col_a:
        tabs = st.tabs(["💬 Chat", "🔊 Summary", "📄 Thesis"])

        with tabs[0]: # CHAT
            if "msgs" not in st.session_state: st.session_state.msgs = []
            for m in st.session_state.msgs: st.chat_message(m["role"]).write(m["content"])
            
            if p := st.chat_input("Ask the Professor..."):
                st.session_state.msgs.append({"role": "user", "content": p})
                st.chat_message("user").write(p)
                with st.chat_message("assistant"):
                    ans = safe_gemini_call(p, st.session_state.raw_data, st.session_state.mime, model_choice)
                    if ans:
                        st.markdown(ans)
                        st.session_state.msgs.append({"role": "assistant", "content": ans})

        with tabs[1]: # AUDIO
            if st.button("🎙️ Generate Audio Summary"):
                with st.spinner("Thinking..."):
                    txt = safe_gemini_call("Brief 2-sentence summary.", st.session_state.raw_data, st.session_state.mime, model_choice)
                    if txt:
                        tts = gTTS(text=txt, lang='en')
                        audio_io = io.BytesIO()
                        tts.write_to_fp(audio_io)
                        st.audio(audio_io.getvalue(), format="audio/mp3")

        with tabs[2]: # REPORT
            if st.button("✨ Draft Thesis"):
                with st.spinner("Compiling..."):
                    rep = safe_gemini_call("Write a full academic report.", st.session_state.raw_data, st.session_state.mime, model_choice)
                    if rep:
                        st.markdown(rep)
                        st.session_state.report = rep
            
            if "report" in st.session_state:
                st.download_button("📥 Download PDF", FPDF().output(), "Thesis.pdf") # Simplified for space
else:
    st.info("Upload a file to begin.")











