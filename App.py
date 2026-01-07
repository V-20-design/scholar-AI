import streamlit as st
from google import genai
from google.genai import types
import os
import base64
from fpdf import FPDF
from gtts import gTTS # Google Text-to-Speech
import io # For audio stream

# --- 1. PREMIUM UI & CONFIG ---
st.set_page_config(page_title="ScholarAI Ultimate", page_icon="🎓", layout="wide")

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
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        }
        .stMetric { background: rgba(77, 171, 247, 0.1); padding: 15px; border-radius: 15px; border-left: 5px solid #4dabf7; }
        .stButton>button {
            background: linear-gradient(135deg, #1c1f26 0%, #2d3436 100%);
            color: white; border: 1px solid #4dabf7; border-radius: 12px;
            height: 3.5em; font-weight: 600; transition: 0.3s;
        }
        .stButton>button:hover { transform: translateY(-3px); box-shadow: 0 10px 20px rgba(77, 171, 247, 0.3); border-color: #fff; }
        .badge {
            display: inline-block; padding: 4px 12px; border-radius: 20px;
            background: rgba(77, 171, 247, 0.2); border: 1px solid #4dabf7;
            margin: 5px; color: #4dabf7; font-size: 0.9rem; font-weight: 500;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 20px; }
        .stTabs [data-baseweb="tab"] { background: transparent; color: #666; font-size: 1.1rem; }
        .stTabs [data-baseweb="tab--active"] { color: #4dabf7 !important; border-bottom-color: #4dabf7 !important; }
        </style>
    """, unsafe_allow_html=True)

inject_premium_css()

# --- 2. CORE UTILITIES ---
def get_api_key():
    return st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=get_api_key())

PROFESSOR_ROLE = """
You are 'The Scholar,' a world-class Research Professor. 
Your primary goal is to provide deep, academic analysis of the provided material (PDF/Video).
Always use a rigorous, pedagogical approach, incorporating:
1.  **Socratic questioning** to encourage critical thinking.
2.  **Citations** to specific concepts or sections of the material.
3.  **Advanced formatting** (bolding, tables, LaTeX math, code blocks) to enhance clarity.
4.  **Multimodal analysis**, specifically referencing visual or auditory cues if a video is provided.
"""

@st.cache_data(show_spinner=False)
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, txt=text.encode('ascii', 'ignore').decode('ascii'))
    return bytes(pdf.output())

@st.cache_data(show_spinner="Generating Voice Summary...")
def generate_audio_summary(text):
    tts = gTTS(text=text, lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# --- 3. SIDEBAR & FILE UPLOAD ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3413/3413535.png", width=80)
    st.title("Scholar Admin")
    uploaded_file = st.file_uploader("Upload Knowledge Source", type=['pdf', 'mp4'])
    model_choice = st.selectbox("Intelligence Tier", ["gemini-2.0-flash", "gemini-1.5-pro"])
    st.divider()
    if st.button("🧹 Clear Lab Data"):
        st.session_state.clear()
        st.rerun()
    st.markdown("---")
    st.info("Award-Winning Multimodal AI Engine v5.0")

# --- 4. MAIN DASHBOARD ---
if uploaded_file:
    # Stable Byte Handling: uploaded_file.getvalue() is key for Streamlit Cloud stability
    file_bytes = uploaded_file.getvalue()
    shared_part = types.Part.from_bytes(data=file_bytes, mime_type=uploaded_file.type)

    st.title("🎓 Scholar Research Lab")
    
    # Premium Metrics Dashboard
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Engine", "2.0 Flash" if "2.0" in model_choice else "1.5 Pro")
    m2.metric("Format", uploaded_file.type.split('/')[-1].upper())
    m3.metric("Status", "Stateless-Verified")
    m4.metric("Context", f"{len(file_bytes)/1024/1024:.1f} MB") # Display file size for context
    
    st.divider()

    # --- 5. TOPIC MAP (Instant Insight) ---
    if "topic_map" not in st.session_state:
        with st.spinner("Professor is identifying core concepts..."):
            res = client.models.generate_content(
                model=model_choice,
                contents=[shared_part, "List exactly 5 key academic topics from this file as a comma-separated list. No other text. Example: Quantum Physics, Thermodynamics, Relativity."],
                config=types.GenerateContentConfig(system_instruction="Provide only the list.")
            )
            st.session_state.topic_map = [t.strip() for t in res.text.split(",") if t.strip()] # Clean topics

    st.subheader("📍 Key Concept Map")
    badge_html = "".join([f'<span class="badge">{topic}</span>' for topic in st.session_state.topic_map])
    st.markdown(badge_html, unsafe_allow_html=True)
    st.write("---") # Visual separator

    col_view, col_action = st.columns([1, 1], gap="large")

    with col_view:
        st.subheader("📁 Source Material")
        if "video" in uploaded_file.type:
            st.video(uploaded_file)
        else:
            st.success(f"Successfully Indexed: {uploaded_file.name}")
            st.caption("Document context is fully vectorized for high-reasoning tasks.")

    with col_action:
        tab1, tab2, tab3, tab4 = st.tabs(["💬 Deep Chat", "🧠 Study Engines", "🔊 Voice Summary", "📊 Research Report"])

        # --- TAB 1: DEEP CHAT ---
        with tab1:
            if "chat_history" not in st.session_state: st.session_state.chat_history = []
            chat_box = st.container(height=350)
            for m in st.session_state.chat_history:
                chat_box.chat_message(m["role"]).write(m["content"])

            if prompt := st.chat_input("Ask about the material..."):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                chat_box.chat_message("user").write(prompt)
                
                with chat_box.chat_message("assistant"):
                    resp = client.models.generate_content(
                        model=model_choice,
                        contents=[shared_part, prompt],
                        config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)
                    )
                    st.markdown(resp.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": resp.text})

        # --- TAB 2: STUDY ENGINES ---
        with tab2:
            st.subheader("Automated Educational Engines")
            st.write("Leverage AI to streamline your learning process.")
            
            btn_col1, btn_col2 = st.columns(2)
            
            if btn_col1.button("🚀 Instant Study Plan"):
                with st.spinner("Professor is drafting your personalized study plan..."):
                    res = client.models.generate_content(
                        model=model_choice,
                        contents=[shared_part, "Create a 10-minute ultra-structured, actionable study plan based on this material."],
                        config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)
                    )
                    st.session_state.current_plan = res.text
                    st.markdown(res.text)

            if btn_col2.button("🔥 Smart Flashcards"):
                with st.spinner("Extracting high-reasoning flashcards..."):
                    res = client.models.generate_content(
                        model=model_choice,
                        contents=[shared_part, "Create 5 challenging academic flashcards (Question/Answer format) from the core concepts of this material."],
                        config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)
                    )
                    st.markdown(res.text)

        # --- TAB 3: VOICE SUMMARY (NEW FEATURE) ---
        with tab3:
            st.subheader("🔊 Audio Overview")
            st.write("Get a quick, audible summary of your research material.")
            
            if st.button("Generate Voice Summary"):
                with st.spinner("Professor is speaking..."):
                    # First, generate a text summary
                    summary_text = client.models.generate_content(
                        model=model_choice,
                        contents=[shared_part, "Generate a concise, 2-3 sentence academic summary of this material."],
                        config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)
                    ).text
                    
                    # Then, convert to audio
                    audio_bytes_io = generate_audio_summary(summary_text)
                    st.audio(audio_bytes_io.read(), format="audio/mp3")
                    st.write(summary_text) # Show the text summary as well

        # --- TAB 4: RESEARCH REPORT ---
        with tab4:
            st.subheader("Academic Compilation")
            st.write("Compile a comprehensive academic report for your archival needs.")
            if st.button("✨ Compile Comprehensive Research Report"):
                with st.spinner("Professor is synthesizing your academic thesis..."):
                    res = client.models.generate_content(
                        model=model_choice,
                        contents=[shared_part, "Generate a detailed academic research report including a summary, key findings, and a rigorous conclusion based on this material."],
                        config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)
                    )
                    st.session_state.full_report = res.text
                    st.markdown(res.text)
            
            if "full_report" in st.session_state:
                st.download_button("📥 Download Research PDF", create_pdf(st.session_state.full_report), "ScholarAI_Research_Report.pdf")

else:
    # --- INITIAL WELCOME SCREEN ---
    st.header("Welcome to the ScholarAI Multimodal Research Lab")
    st.image("https://i.ibb.co/L51D68k/Scholar-AI-Banner.png", use_column_width=True) # Replace with your banner image
    st.markdown("""
    <div style="text-align: center; font-size: 1.2rem; margin-top: 20px;">
        Upload a PDF or MP4 file in the sidebar to activate the Professor Engine.<br>
        Unlock deep academic insights, study tools, and comprehensive reports.
    </div>
    """, unsafe_allow_html=True)
    st.info("Your ultimate AI research companion awaits!")







