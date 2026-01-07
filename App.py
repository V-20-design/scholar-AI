import streamlit as st
from google import genai
from google.genai import types
import os
import time
from dotenv import load_dotenv, set_key
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
        
        /* Button Styling */
        .stButton>button {
            background-color: #1c1f26; color: #ffffff; border-radius: 10px;
            border: 1px solid #343a40; transition: all 0.3s ease;
            width: 100%; height: 3em;
        }
        .stButton>button:hover {
            border-color: #4dabf7; color: #4dabf7; background-color: #252a34; transform: translateY(-2px);
        }
        
        /* Tabs and Sidebar */
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] { color: #ced4da; }
        section[data-testid="stSidebar"] { background-color: #16191f !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

inject_dark_academy_css()

# --- 3. AUTH & ENVIRONMENT ---
env_path = ".env"
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)

def get_api_key():
    # Priority 1: Streamlit Cloud Secrets
    if hasattr(st, "secrets") and "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"].strip()
    # Priority 2: Local .env file
    key = os.getenv("GOOGLE_API_KEY")
    if key: return key.strip()
    return None

def create_pdf_bytes(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    # Deep clean text for FPDF compatibility
    clean_text = text.encode('ascii', 'ignore').decode('ascii')
    pdf.multi_cell(0, 10, txt=clean_text)
    return bytes(pdf.output())

# --- 4. SIDEBAR CONTROLS ---
api_key = get_api_key()

with st.sidebar:
    st.title("🛡️ Scholar Admin")
    if not api_key:
        new_key = st.text_input("Enter Gemini API Key", type="password")
        if st.button("Unlock Lab"):
            if new_key:
                # Save locally for development, but Cloud will use Secrets
                if not os.path.exists(env_path): open(env_path, 'a').close()
                set_key(env_path, "GOOGLE_API_KEY", new_key.strip())
                st.rerun()
        st.stop()
    
    st.success("API Key Active")
    model_choice = st.radio("Intelligence Level", ["Gemini 2.0 Flash (Fast)", "Gemini 1.5 Pro (Deep)"])
    # Stability IDs for 2026
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
    # Handle File Upload & Processing
    if "file_uri" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.status("Gemini 3 Processing Context...") as status:
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f: f.write(uploaded_file.getbuffer())
            
            my_file = client.files.upload(file=temp_path)
            while my_file.state.name == "PROCESSING":
                time.sleep(2)
                my_file = client.files.get(name=my_file.name)
            
            st.session_state.file_uri = my_file.uri
            st.session_state.mime_type = uploaded_file.type
            st.session_state.file_name = uploaded_file.name
            os.remove(temp_path)
            status.update(label="Context Fully Loaded!", state="complete")

    # Define shared file part
    shared_file_part = types.Part.from_uri(
        file_uri=st.session_state.file_uri, 
        mime_type=st.session_state.mime_type
    )

    # Dashboard Header
    st.title("🎓 Scholar Research Lab")
    m1, m2, m3 = st.columns(3)
    m1.metric("Engine", "Pro Edition" if "pro" in MODEL_ID else "Flash Edition")
    m2.metric("Input", uploaded_file.type.split('/')[-1].upper())
    m3.metric("Context", "Ready (2M Tokens)")
    st.divider()

    col_viewer, col_tools = st.columns([1, 1], gap="large")

    with col_viewer:
        st.subheader("📁 Reference Media")
        if "mp4" in st.session_state.mime_type:
            st.video(uploaded_file)
        else:
            st.info(f"Loaded: {st.session_state.file_name}")
            st.markdown("> **Note:** PDF context is fully indexed. You can ask questions about specific pages or data points in the chat.")

    with col_tools:
        tab1, tab2, tab3 = st.tabs(["💬 Deep Chat", "🧠 AI Study Tools", "📄 Export"])

        with tab1:
            chat_container = st.container(height=450)
            if "messages" not in st.session_state: st.session_state.messages = []
            
            with chat_container:
                for msg in st.session_state.messages:
                    st.chat_message(msg["role"]).write(msg["content"])

            if user_prompt := st.chat_input("Ask about your file..."):
                st.session_state.messages.append({"role": "user", "content": user_prompt})
                chat_container.chat_message("user").write(user_prompt)
                
                with chat_container.chat_message("assistant"):
                    res_box = st.empty()
                    full_res = ""
                    for chunk in client.models.generate_content_stream(
                        model=MODEL_ID,
                        contents=[shared_file_part, user_prompt]
                    ):
                        full_res += chunk.text
                        res_box.markdown(full_res + "▌")
                    res_box.markdown(full_res)
                    st.session_state.messages.append({"role": "assistant", "content": full_res})

        with tab2:
            st.subheader("Automated Assistance")
            c1, c2 = st.columns(2)
            
            if c1.button("🚀 Instant Study Plan"):
                with st.spinner("Analyzing..."):
                    res = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=[shared_file_part, "Create a structured 10-minute study plan for this material."]
                    )
                    st.markdown(f"### Study Strategy\n{res.text}")

            if c2.button("🔥 Smart Flashcards"):
                with st.spinner("Extracting..."):
                    res = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=[shared_file_part, "Create 5 practice flashcards (Question/Answer) for the core concepts."]
                    )
                    st.markdown(f"### Practice Set\n{res.text}")

        with tab3:
            st.subheader("Final Documentation")
            if st.button("✨ Compile Full Research Report"):
                with st.spinner("Generating deep-dive guide..."):
                    report = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=[shared_file_part, "Generate a comprehensive, academic study report based on this file."]
                    )
                    st.session_state.last_report = report.text
                    st.markdown(st.session_state.last_report)
            
            if "last_report" in st.session_state:
                st.download_button(
                    "📥 Download Report as PDF", 
                    create_pdf_bytes(st.session_state.last_report), 
                    f"ScholarAI_{st.session_state.file_name}.pdf"
                )
else:
    st.header("Research Lab Offline")
    st.info("Please upload a PDF or MP4 file in the sidebar to initialize the AI Scholar.")

