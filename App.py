import streamlit as st
from google import genai
from google.genai import types
import os
import base64
from fpdf import FPDF

# --- 1. MANDATORY TOP-LEVEL CONFIG ---
st.set_page_config(
    page_title="ScholarAI", 
    page_icon="🎓", 
    layout="wide"
)

# --- 2. UI STYLING (DARK ACADEMY) ---
def inject_dark_academy_css():
    st.markdown(
        """
        <style>
        .stApp { background-color: #0e1117; }
        .main .block-container {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 3rem;
            margin-top: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
        }
        h1, h2, h3 { color: #ffffff !important; font-weight: 700 !important; }
        .stMarkdown p, .stMarkdown li { color: #ced4da !important; font-size: 1.05rem !important; }
        [data-testid="stMetricValue"] { color: #4dabf7 !important; font-weight: 700 !important; }
        
        .stButton>button {
            background-color: #1c1f26; color: #ffffff; border-radius: 10px;
            border: 1px solid #4dabf7; transition: all 0.3s ease;
            width: 100%; height: 3em;
        }
        .stButton>button:hover {
            border-color: #ffffff; color: #4dabf7; background-color: #252a34; transform: translateY(-2px);
        }
        
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] { color: #ced4da; }
        section[data-testid="stSidebar"] { background-color: #16191f !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

inject_dark_academy_css()

# --- 3. AUTH & UTILS ---
def get_api_key():
    # Priority 1: Streamlit Secrets (Best for GitHub/Cloud)
    if hasattr(st, "secrets") and "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"].strip()
    # Priority 2: Local Environment
    return os.getenv("GOOGLE_API_KEY")

def create_pdf_bytes(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    # Filter text for FPDF compatibility
    clean_text = text.encode('ascii', 'ignore').decode('ascii')
    pdf.multi_cell(0, 10, txt=clean_text)
    return bytes(pdf.output())

# --- 4. SIDEBAR CONTROLS ---
api_key = get_api_key()

with st.sidebar:
    st.title("🛡️ Scholar Admin")
    if not api_key:
        st.warning("Please add GOOGLE_API_KEY to Secrets.")
        st.stop()
    
    st.success("API Key Active")
    model_choice = st.radio("Intelligence Level", ["Gemini 2.0 Flash (Fast)", "Gemini 1.5 Pro (Deep)"])
    MODEL_ID = "gemini-2.0-flash" if "Flash" in model_choice else "gemini-1.5-pro" 
    
    uploaded_file = st.file_uploader("Upload Material", type=['pdf', 'mp4'])
    
    st.divider()
    if st.button("🧹 Reset Lab Session"):
        st.session_state.clear()
        st.rerun()

# Initialize Client
client = genai.Client(api_key=api_key)

# --- 5. ENGINE & DASHBOARD ---
if uploaded_file:
    # STABLE DATA LOADING: Using Bytes to prevent "Redacted ClientError"
    file_bytes = uploaded_file.read()
    shared_file_part = types.Part.from_bytes(
        data=file_bytes, 
        mime_type=uploaded_file.type
    )

    # Dashboard Header
    st.title("🎓 Scholar Research Lab")
    m1, m2, m3 = st.columns(3)
    m1.metric("Engine", "Professor Edition")
    m2.metric("Input", uploaded_file.type.split('/')[-1].upper())
    m3.metric("Context", "Ready (Stateless)")
    st.divider()

    col_viewer, col_tools = st.columns([1, 1], gap="large")

    with col_viewer:
        st.subheader("📁 Reference Media")
        if "mp4" in uploaded_file.type:
            st.video(uploaded_file)
        else:
            st.info(f"Indexing complete: {uploaded_file.name}")
            st.markdown("> **Professor's Note:** Full document context is now active in memory.")

    with col_tools:
        tab1, tab2, tab3 = st.tabs(["💬 Deep Chat", "🧠 AI Study Tools", "📄 Export"])

        with tab1:
            chat_container = st.container(height=450)
            if "messages" not in st.session_state: st.session_state.messages = []
            
            with chat_container:
                for msg in st.session_state.messages:
                    st.chat_message(msg["role"]).write(msg["content"])

            if user_prompt := st.chat_input("Ask your Professor..."):
                st.session_state.messages.append({"role": "user", "content": user_prompt})
                chat_container.chat_message("user").write(user_prompt)
                
                with chat_container.chat_message("assistant"):
                    # SYSTEM INSTRUCTION: Hardcoded persona for consistency
                    sys_instr = "You are a Senior Research Professor. Provide academic, rigorous, and deep-dive answers based strictly on the provided file."
                    
                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=[shared_file_part, f"{sys_instr}\n\nUser Question: {user_prompt}"]
                    )
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})

        with tab2:
            st.subheader("Automated Study Tools")
            c1, c2 = st.columns(2)
            
            if c1.button("🚀 Instant Study Plan"):
                with st.spinner("Analyzing..."):
                    res = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=[shared_file_part, "Act as a Professor and create a structured study plan for this."]
                    )
                    st.markdown(f"### Study Strategy\n{res.text}")

            if c2.button("🔥 Smart Flashcards"):
                with st.spinner("Extracting..."):
                    res = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=[shared_file_part, "Generate 5 high-level academic flashcards from this material."]
                    )
                    st.markdown(f"### Practice Set\n{res.text}")

        with tab3:
            st.subheader("Final Documentation")
            if st.button("✨ Compile Full Research Report"):
                with st.spinner("Writing deep-dive guide..."):
                    report = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=[shared_file_part, "Generate a comprehensive, academic research report based on this material."]
                    )
                    st.session_state.last_report = report.text
                    st.markdown(st.session_state.last_report)
            
            if "last_report" in st.session_state:
                st.download_button(
                    "📥 Download Report as PDF", 
                    create_pdf_bytes(st.session_state.last_report), 
                    f"ScholarAI_Report.pdf"
                )
else:
    st.header("Welcome to the Lab")
    st.info("Upload a PDF or Video in the sidebar to initialize the AI Scholar Professor.")


