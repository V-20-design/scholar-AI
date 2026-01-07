import streamlit as st
from google import genai
from google.genai import types
import os, base64, io
from fpdf import FPDF
from gtts import gTTS

# --- 1. CONFIG & UI ---
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .main .block-container { background: rgba(255, 255, 255, 0.03); border-radius: 20px; padding: 3rem; border: 1px solid rgba(255, 255, 255, 0.1); }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; background: rgba(77, 171, 247, 0.2); border: 1px solid #4dabf7; margin: 5px; color: #4dabf7; font-size: 0.9rem; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background: #1c1f26; color: white; border: 1px solid #4dabf7; }
    </style>
""", unsafe_allow_html=True)

# --- 2. THE ERROR-PROOF ENGINE ---
def get_api_key():
    return st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=get_api_key())

def get_fresh_part(bytes_data, mime_type):
    """Creates a fresh Google Part directly from bytes to avoid session corruption."""
    return types.Part.from_bytes(data=bytes_data, mime_type=mime_type)

@st.cache_data
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, txt=text.encode('ascii', 'ignore').decode('ascii'))
    return bytes(pdf.output())

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    uploaded_file = st.file_uploader("Upload Source (Max 20MB)", type=['pdf', 'mp4'])
    model_choice = st.selectbox("Intelligence Tier", ["gemini-2.0-flash", "gemini-1.5-pro"])
    if st.button("🧹 Clear All Data"):
        st.session_state.clear()
        st.rerun()

# --- 4. MAIN LOGIC ---
if uploaded_file:
    # 1. Store RAW bytes in session state (safest way to keep data)
    if "raw_bytes" not in st.session_state:
        st.session_state.raw_bytes = uploaded_file.getvalue()
        st.session_state.mime_type = uploaded_file.type

    if len(st.session_state.raw_bytes) > 20 * 1024 * 1024:
        st.error("File exceeds 20MB limit for direct analysis.")
        st.stop()

    st.title("🎓 Scholar Research Lab")
    PROF_ROLE = "You are 'The Scholar,' a world-class Research Professor. Use academic rigor, LaTeX, and citations."

    # --- TOPIC MAP (One-time run) ---
    if "topics" not in st.session_state:
        with st.spinner("Professor is initializing..."):
            try:
                # We create the Part INSIDE the call
                res = client.models.generate_content(
                    model=model_choice,
                    contents=[
                        get_fresh_part(st.session_state.raw_bytes, st.session_state.mime_type),
                        "List 5 academic keywords for this as a comma-separated list."
                    ],
                    config=types.GenerateContentConfig(system_instruction="Provide only the list.")
                )
                st.session_state.topics = [t.strip() for t in res.text.split(",")]
            except Exception as e:
                st.session_state.topics = ["Ready for Analysis"]

    # Display UI
    st.markdown(" ".join([f'<span class="badge">{t}</span>' for t in st.session_state.topics]), unsafe_allow_html=True)
    st.divider()

    col_v, col_a = st.columns([1, 1], gap="large")
    with col_v:
        if "video" in st.session_state.mime_type: st.video(uploaded_file)
        else: st.info(f"📄 Document {uploaded_file.name} is loaded.")

    with col_a:
        tabs = st.tabs(["💬 Chat", "🧠 Tools", "🔊 Voice", "📄 Report"])

        with tabs[0]: # CHAT
            if "msgs" not in st.session_state: st.session_state.msgs = []
            for m in st.session_state.msgs: st.chat_message(m["role"]).write(m["content"])
            
            if p := st.chat_input("Ask Professor..."):
                st.session_state.msgs.append({"role": "user", "content": p})
                st.chat_message("user").write(p)
                with st.chat_message("assistant"):
                    try:
                        r = client.models.generate_content(
                            model=model_choice,
                            contents=[get_fresh_part(st.session_state.raw_bytes, st.session_state.mime_type), p],
                            config=types.GenerateContentConfig(system_instruction=PROF_ROLE)
                        )
                        st.markdown(r.text)
                        st.session_state.msgs.append({"role": "assistant", "content": r.text})
                    except Exception as e:
                        st.error("The Professor encountered a connection error. Try a shorter prompt.")

        with tabs[1]: # TOOLS
            if st.button("🚀 Study Plan"):
                with st.spinner("Drafting..."):
                    r = client.models.generate_content(
                        model=model_choice, 
                        contents=[get_fresh_part(st.session_state.raw_bytes, st.session_state.mime_type), "Create a 10-min study plan."],
                        config=types.GenerateContentConfig(system_instruction=PROF_ROLE)
                    )
                    st.markdown(r.text)

        with tabs[2]: # VOICE
            if st.button("Generate Audio Summary"):
                with st.spinner("Synthesizing..."):
                    sum_txt = client.models.generate_content(
                        model=model_choice, 
                        contents=[get_fresh_part(st.session_state.raw_bytes, st.session_state.mime_type), "Brief 2-sentence summary."],
                        config=types.GenerateContentConfig(system_instruction=PROF_ROLE)
                    ).text
                    tts = gTTS(text=sum_txt, lang='en')
                    audio_io = io.BytesIO()
                    tts.write_to_fp(audio_io)
                    st.audio(audio_io.getvalue(), format="audio/mp3")

        with tabs[3]: # EXPORT
            if st.button("✨ Full Report"):
                with st.spinner("Compiling..."):
                    rep = client.models.generate_content(
                        model=model_choice, 
                        contents=[get_fresh_part(st.session_state.raw_bytes, st.session_state.mime_type), "Write a full academic report."],
                        config=types.GenerateContentConfig(system_instruction=PROF_ROLE)
                    ).text
                    st.session_state.rep = rep
                    st.markdown(rep)
            if "rep" in st.session_state:
                st.download_button("📥 Download PDF", create_pdf(st.session_state.rep), "Report.pdf")
else:
    st.info("Upload a file to initialize the Lab.")









