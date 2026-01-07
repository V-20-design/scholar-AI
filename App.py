import streamlit as st
from google import genai
from google.genai import types
import os
import base64
from fpdf import FPDF
from gtts import gTTS
import io

# --- 1. CONFIG & CSS ---
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .main .block-container { background: rgba(255, 255, 255, 0.03); border-radius: 20px; padding: 3rem; border: 1px solid rgba(255, 255, 255, 0.1); }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; background: rgba(77, 171, 247, 0.2); border: 1px solid #4dabf7; margin: 5px; color: #4dabf7; font-size: 0.9rem; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background: #1c1f26; color: white; border: 1px solid #4dabf7; }
    </style>
""", unsafe_allow_html=True)

# --- 2. THE ERROR-PROOF HANDLER ---
def get_api_key():
    return st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=get_api_key())

def get_base64_part(uploaded_file):
    """Converts file to a Base64 string - the most stable way to send data."""
    bytes_data = uploaded_file.getvalue()
    base64_data = base64.b64encode(bytes_data).decode('utf-8')
    return types.Part.from_bytes(
        data=base64.b64decode(base64_data),
        mime_type=uploaded_file.type
    )

@st.cache_data
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, txt=text.encode('ascii', 'ignore').decode('ascii'))
    return bytes(pdf.output())

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Admin Panel")
    uploaded_file = st.file_uploader("Upload Source", type=['pdf', 'mp4'])
    model_choice = st.selectbox("Intelligence", ["gemini-2.0-flash", "gemini-1.5-pro"])
    if st.button("🧹 Reset System"):
        st.session_state.clear()
        st.rerun()

# --- 4. MAIN DASHBOARD ---
if uploaded_file:
    # 20MB limit check
    if len(uploaded_file.getvalue()) > 20 * 1024 * 1024:
        st.error("File size exceeds 20MB. Please use a smaller file for this demo tier.")
        st.stop()

    st.title("🎓 Scholar Research Lab")
    
    # Pre-process the file once
    if "shared_part" not in st.session_state:
        st.session_state.shared_part = get_base64_part(uploaded_file)

    # --- TOPIC MAP ---
    if "topics" not in st.session_state:
        with st.spinner("Professor is scanning material..."):
            try:
                res = client.models.generate_content(
                    model=model_choice,
                    contents=[st.session_state.shared_part, "List 5 academic keywords as a comma-separated list."],
                    config=types.GenerateContentConfig(system_instruction="You are a research professor. Reply only with the list.")
                )
                st.session_state.topics = [t.strip() for t in res.text.split(",")]
            except:
                st.session_state.topics = ["Analysis Ready"]

    # Display Badges
    st.markdown(" ".join([f'<span class="badge">{t}</span>' for t in st.session_state.topics]), unsafe_allow_html=True)
    st.divider()

    col_v, col_a = st.columns([1, 1], gap="large")

    with col_v:
        if "video" in uploaded_file.type: st.video(uploaded_file)
        else: st.info(f"📄 {uploaded_file.name} is active.")

    with col_a:
        tabs = st.tabs(["💬 Chat", "🧠 Tools", "🔊 Voice", "📄 Export"])
        PROF_ROLE = "You are 'The Scholar,' a world-class Research Professor. Use academic rigor and citations."

        with tabs[0]:
            if "msgs" not in st.session_state: st.session_state.msgs = []
            for m in st.session_state.msgs: st.chat_message(m["role"]).write(m["content"])
            if p := st.chat_input("Ask the Professor..."):
                st.session_state.msgs.append({"role": "user", "content": p})
                st.chat_message("user").write(p)
                with st.chat_message("assistant"):
                    r = client.models.generate_content(
                        model=model_choice,
                        contents=[st.session_state.shared_part, p],
                        config=types.GenerateContentConfig(system_instruction=PROF_ROLE)
                    )
                    st.markdown(r.text)
                    st.session_state.msgs.append({"role": "assistant", "content": r.text})

        with tabs[1]:
            if st.button("🚀 Study Plan"):
                r = client.models.generate_content(model=model_choice, contents=[st.session_state.shared_part, "Create a study plan."], config=types.GenerateContentConfig(system_instruction=PROF_ROLE))
                st.markdown(r.text)

        with tabs[2]:
            if st.button("Generate Voice"):
                with st.spinner("Synthesizing..."):
                    sum_txt = client.models.generate_content(model=model_choice, contents=[st.session_state.shared_part, "Summary in 1 sentence."], config=types.GenerateContentConfig(system_instruction=PROF_ROLE)).text
                    tts = gTTS(text=sum_txt, lang='en')
                    audio_io = io.BytesIO()
                    tts.write_to_fp(audio_io)
                    st.audio(audio_io.getvalue(), format="audio/mp3")

        with tabs[3]:
            if st.button("✨ Final Thesis"):
                rep = client.models.generate_content(model=model_choice, contents=[st.session_state.shared_part, "Write a thesis report."], config=types.GenerateContentConfig(system_instruction=PROF_ROLE)).text
                st.session_state.rep = rep
                st.markdown(rep)
            if "rep" in st.session_state:
                st.download_button("📥 Download PDF", create_pdf(st.session_state.rep), "Report.pdf")
else:
    st.info("Upload a source to begin.")








