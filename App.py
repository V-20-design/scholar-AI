import streamlit as st
from google import genai
from google.genai import types
import os
import base64
from fpdf import FPDF
from gtts import gTTS
import io

# --- 1. PREMIUM UI ---
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")

def inject_premium_css():
    st.markdown("""
        <style>
        .stApp { background-color: #0e1117; color: #ffffff; }
        .main .block-container {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(15px);
            border-radius: 24px;
            padding: 3rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .stMetric { background: rgba(77, 171, 247, 0.1); padding: 10px; border-radius: 12px; border-left: 5px solid #4dabf7; }
        .badge {
            display: inline-block; padding: 4px 12px; border-radius: 20px;
            background: rgba(77, 171, 247, 0.2); border: 1px solid #4dabf7;
            margin: 5px; color: #4dabf7; font-size: 0.9rem;
        }
        .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: 600; }
        </style>
    """, unsafe_allow_html=True)

inject_premium_css()

# --- 2. ENGINE ---
def get_api_key():
    return st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=get_api_key())

PROFESSOR_ROLE = "You are 'The Scholar,' a world-class Research Professor. Use academic rigor, citations, and LaTeX."

@st.cache_data(show_spinner=False)
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, txt=text.encode('ascii', 'ignore').decode('ascii'))
    return bytes(pdf.output())

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Admin")
    uploaded_file = st.file_uploader("Source Material", type=['pdf', 'mp4'])
    model_choice = st.selectbox("Intelligence", ["gemini-2.0-flash", "gemini-1.5-pro"])
    if st.button("🧹 Reset Lab"):
        st.session_state.clear()
        st.rerun()

# --- 4. MAIN LOGIC ---
if uploaded_file:
    # Check file size (20MB Limit for Inline Data)
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    
    if file_size_mb > 20:
        st.error(f"❌ File too large ({file_size_mb:.1f}MB). Award-winning speed requires files under 20MB.")
        st.stop()

    file_bytes = uploaded_file.getvalue()
    shared_part = types.Part.from_bytes(data=file_bytes, mime_type=uploaded_file.type)

    st.title("🎓 Scholar Research Lab")
    
    # --- TOPIC MAP FEATURE (MANUAL TRIGGER FOR STABILITY) ---
    if "topic_map" not in st.session_state:
        if st.button("🔍 Initialize Professor Analysis"):
            with st.spinner("Analyzing core concepts..."):
                try:
                    res = client.models.generate_content(
                        model=model_choice,
                        contents=[shared_part, "List 5 academic keywords for this as a comma-separated list."],
                        config=types.GenerateContentConfig(system_instruction="Only the list.")
                    )
                    st.session_state.topic_map = [t.strip() for t in res.text.split(",") if t.strip()]
                    st.rerun()
                except Exception as e:
                    st.error("The Professor is having trouble reading this specific file format. Try a smaller PDF.")
    
    if "topic_map" in st.session_state:
        badge_html = "".join([f'<span class="badge">{t}</span>' for t in st.session_state.topic_map])
        st.markdown(badge_html, unsafe_allow_html=True)

    st.divider()

    col_view, col_action = st.columns([1, 1], gap="large")

    with col_view:
        if "video" in uploaded_file.type: st.video(uploaded_file)
        else: st.success(f"Indexed: {uploaded_file.name}")

    with col_action:
        t1, t2, t3, t4 = st.tabs(["💬 Chat", "🧠 Tools", "🔊 Voice", "📄 Report"])

        with t1:
            if "messages" not in st.session_state: st.session_state.messages = []
            for m in st.session_state.messages: st.chat_message(m["role"]).write(m["content"])
            
            if prompt := st.chat_input("Ask..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.chat_message("user").write(prompt)
                try:
                    resp = client.models.generate_content(
                        model=model_choice,
                        contents=[shared_part, prompt],
                        config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)
                    )
                    st.chat_message("assistant").write(resp.text)
                    st.session_state.messages.append({"role": "assistant", "content": resp.text})
                except: st.error("Context lost. Please re-upload.")

        with t2:
            if st.button("🚀 Study Plan"):
                res = client.models.generate_content(model=model_choice, contents=[shared_part, "Create a study plan."], config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE))
                st.markdown(res.text)

        with t3:
            if st.button("Generate Audio Summary"):
                summary = client.models.generate_content(model=model_choice, contents=[shared_part, "Summary in 2 sentences."], config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)).text
                tts = gTTS(text=summary, lang='en')
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                st.audio(audio_fp.getvalue(), format="audio/mp3")

        with t4:
            if st.button("✨ Final Report"):
                report = client.models.generate_content(model=model_choice, contents=[shared_part, "Write a thesis."], config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)).text
                st.session_state.report = report
                st.markdown(report)
            if "report" in st.session_state:
                st.download_button("📥 Download", create_pdf(st.session_state.report), "Report.pdf")
else:
    st.info("Upload a file to begin.")







