import streamlit as st
from google import genai
from google.genai import types
import os, base64, io, time
from fpdf import FPDF
from gtts import gTTS

# --- 1. CONFIG & UI ---
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")

# --- 2. ENGINE (Safe Request Pattern) ---
def get_api_key():
    return st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=get_api_key())

def safe_generate(prompt, bytes_data, mime_type, model="gemini-2.0-flash"):
    """The most stable way to call Gemini with a file."""
    try:
        # Standardize MIME types to avoid ClientError
        clean_mime = "application/pdf" if "pdf" in mime_type.lower() else "video/mp4"
        
        file_part = types.Part.from_bytes(data=bytes_data, mime_type=clean_mime)
        
        response = client.models.generate_content(
            model=model,
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an expert Professor. Use LaTeX for math."
            )
        )
        return response.text
    except Exception as e:
        # If it still fails, we provide a clean message instead of a redacted crash
        st.error(f"Professor's Office Hours: The AI is busy or the file is unreadable. (Error: {str(e)[:50]}...)")
        return None

# --- 3. UI INJECTION ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .main .block-container { background: rgba(255, 255, 255, 0.03); border-radius: 20px; padding: 3rem; border: 1px solid rgba(255, 255, 255, 0.1); }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; background: rgba(77, 171, 247, 0.2); border: 1px solid #4dabf7; margin: 5px; color: #4dabf7; font-size: 0.9rem; }
    </style>
""", unsafe_allow_html=True)

# --- 4. MAIN LOGIC ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    uploaded_file = st.file_uploader("Upload Source", type=['pdf', 'mp4'])
    model_choice = st.selectbox("Intelligence", ["gemini-2.0-flash", "gemini-1.5-pro"])
    if st.button("🧹 Reset Lab"):
        st.session_state.clear()
        st.rerun()

if uploaded_file:
    # Buffer safety: Give Streamlit a moment to settle the file upload
    if "raw_data" not in st.session_state:
        with st.spinner("Securing file buffer..."):
            time.sleep(1) # Crucial for Streamlit Cloud stability
            st.session_state.raw_data = uploaded_file.getvalue()
            st.session_state.mime = uploaded_file.type
            st.rerun()

    st.title("🎓 Scholar Research Lab")
    
    # --- TOPIC MAP ---
    if "topics" not in st.session_state:
        with st.spinner("Analyzing..."):
            res = safe_generate("List 5 academic keywords (comma-separated).", 
                                st.session_state.raw_data, st.session_state.mime, model_choice)
            st.session_state.topics = res.split(",") if res else ["Ready"]

    st.markdown(" ".join([f'<span class="badge">{t}</span>' for t in st.session_state.topics]), unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["💬 Chat", "🔊 Audio Summary", "📄 Thesis Report"])

    with t1:
        if "chat_history" not in st.session_state: st.session_state.chat_history = []
        for m in st.session_state.chat_history: st.chat_message(m["role"]).write(m["content"])
        
        if p := st.chat_input("Ask the Professor..."):
            st.session_state.chat_history.append({"role": "user", "content": p})
            st.chat_message("user").write(p)
            ans = safe_generate(p, st.session_state.raw_data, st.session_state.mime, model_choice)
            if ans:
                st.chat_message("assistant").write(ans)
                st.session_state.chat_history.append({"role": "assistant", "content": ans})

    with t2:
        if st.button("🎙️ Generate Voice"):
            with st.spinner("Synthesizing..."):
                txt = safe_generate("Summarize in 1 short sentence.", st.session_state.raw_data, st.session_state.mime)
                if txt:
                    tts = gTTS(text=txt, lang='en')
                    audio_io = io.BytesIO()
                    tts.write_to_fp(audio_io)
                    st.audio(audio_io.getvalue(), format="audio/mp3")

    with t3:
        if st.button("✨ Draft Thesis"):
            report = safe_generate("Write a full academic thesis report.", st.session_state.raw_data, st.session_state.mime)
            if report:
                st.markdown(report)
                # (PDF Download logic can go here)
else:
    st.info("Upload a file to begin.")










