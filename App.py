import streamlit as st
from google import genai
from google.genai import types
import os
import base64
from fpdf import FPDF

# --- 1. TOP-LEVEL CONFIG ---
st.set_page_config(page_title="ScholarAI", page_icon="🎓", layout="wide")

# --- 2. UI STYLING ---
def inject_custom_css():
    st.markdown("""
        <style>
        .stApp { background-color: #0e1117; }
        .main .block-container {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 3rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        h1, h2, h3 { color: #ffffff !important; font-weight: 700 !important; }
        .stMarkdown p, .stMarkdown li { color: #ced4da !important; font-size: 1.05rem !important; }
        [data-testid="stMetricValue"] { color: #4dabf7 !important; font-weight: 700 !important; }
        .stButton>button {
            background-color: #1c1f26; color: #ffffff; border-radius: 10px;
            border: 1px solid #4dabf7; width: 100%; height: 3em;
        }
        .stButton>button:hover { border-color: #ffffff; background-color: #252a34; }
        section[data-testid="stSidebar"] { background-color: #16191f !important; }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- 3. AUTH & UTILS ---
def get_api_key():
    if hasattr(st, "secrets") and "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"].strip()
    return os.getenv("GOOGLE_API_KEY")

def create_pdf_bytes(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    clean_text = text.encode('ascii', 'ignore').decode('ascii')
    pdf.multi_cell(0, 10, txt=clean_text)
    return bytes(pdf.output())

# --- 4. SIDEBAR ---
api_key = get_api_key()
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    if not api_key:
        st.error("Missing API Key! Add it to Streamlit Secrets.")
        st.stop()
    
    model_choice = st.radio("Intelligence Level", ["Gemini 2.0 Flash (Fast)", "Gemini 1.5 Pro (Deep)"])
    MODEL_ID = "gemini-2.0-flash" if "Flash" in model_choice else "gemini-1.5-pro" 
    uploaded_file = st.file_uploader("Upload Material", type=['pdf', 'mp4'])
    
    if st.button("🧹 Reset Lab"):
        st.session_state.clear()
        st.rerun()

client = genai.Client(api_key=api_key)

# --- 5. MAIN ENGINE ---
if uploaded_file:
    # THE FIX: Read file as bytes instead of using client.files.upload()
    file_bytes = uploaded_file.read()
    shared_file_part = types.Part.from_bytes(data=file_bytes, mime_type=uploaded_file.type)

    # Professor Persona Configuration
    PROFESSOR_ROLE = (
        "You are a Senior Research Professor. Your goal is to provide academic, "
        "rigorous, and deep-dive answers based on the provided material. "
        "Maintain a sophisticated but encouraging educational tone."
    )

    st.title("🎓 Scholar Research Lab")
    m1, m2, m3 = st.columns(3)
    m1.metric("Engine", "Professor Edition")
    m2.metric("Input", uploaded_file.type.split('/')[-1].upper())
    m3.metric("Status", "Stateless (Stable)")
    st.divider()

    col_viewer, col_tools = st.columns([1, 1], gap="large")

    with col_viewer:
        st.subheader("📁 Reference Media")
        if "mp4" in uploaded_file.type:
            st.video(uploaded_file)
        else:
            st.info(f"Context Active: {uploaded_file.name}")

    with col_tools:
        tab1, tab2, tab3 = st.tabs(["💬 Deep Chat", "🧠 AI Study Tools", "📄 Export"])

        with tab1:
            chat_container = st.container(height=400)
            if "messages" not in st.session_state: st.session_state.messages = []
            
            for msg in st.session_state.messages:
                chat_container.chat_message(msg["role"]).write(msg["content"])

            if user_prompt := st.chat_input("Ask your Professor..."):
                st.session_state.messages.append({"role": "user", "content": user_prompt})
                chat_container.chat_message("user").write(user_prompt)
                
                with chat_container.chat_message("assistant"):
                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=[shared_file_part, user_prompt],
                        config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)
                    )
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})

        with tab2:
            st.subheader("Automated Assistance")
            c1, c2 = st.columns(2)
            
            if c1.button("🚀 Instant Study Plan"):
                with st.spinner("Professor is drafting..."):
                    res = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=[shared_file_part, "Create a structured study plan."],
                        config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)
                    )
                    st.markdown(res.text)

            if c2.button("🔥 Smart Flashcards"):
                with st.spinner("Extracting concepts..."):
                    res = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=[shared_file_part, "Generate 5 academic flashcards."],
                        config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)
                    )
                    st.markdown(res.text)

        with tab3:
            if st.button("✨ Compile Full Report"):
                with st.spinner("Writing..."):
                    report = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=[shared_file_part, "Write a comprehensive research report."],
                        config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)
                    )
                    st.session_state.last_report = report.text
                    st.markdown(st.session_state.last_report)
            
            if "last_report" in st.session_state:
                st.download_button("📥 Download PDF", create_pdf_bytes(st.session_state.last_report), "Scholar_Report.pdf")
else:
    st.header("Welcome to the Lab")
    st.info("Upload a file in the sidebar to start.")




