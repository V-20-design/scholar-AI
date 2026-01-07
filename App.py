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
    page_icon="https://cdn-icons-png.flaticon.com/512/2997/2997313.png?v=9", 
    layout="wide"
)

# --- 2. PWA & ICON INJECTION ---
st.markdown(
    """
    <head>
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-title" content="ScholarAI">
        <link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/2997/2997313.png?v=9">
        <link rel="icon" href="https://cdn-icons-png.flaticon.com/512/2997/2997313.png?v=9">
    </head>
    """,
    unsafe_allow_html=True
)

# --- 3. UI STYLING (DARK ACADEMY) ---
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
            border: 1px solid #343a40; transition: all 0.3s ease;
            width: 100%; height: 3em;
        }
        .stButton>button:hover {
            border-color: #4dabf7; color: #4dabf7; background-color: #252a34; transform: translateY(-2px);
        }
        section[data-testid="stSidebar"] { background-color: #16191f !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

inject_dark_academy_css()

# --- 4. AUTH & ENVIRONMENT ---
env_path = ".env"
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)

def get_api_key():
    key = os.getenv("GOOGLE_API_KEY")
    if key: return key.strip()
    if hasattr(st, "secrets") and "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"].strip()
    return None

def create_pdf_bytes(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return bytes(pdf.output())

# --- 5. SIDEBAR ---
api_key = get_api_key()
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    if not api_key:
        new_key = st.text_input("Enter Gemini API Key", type="password")
        if st.button("Unlock Lab"):
            if new_key:
                set_key(env_path, "GOOGLE_API_KEY", new_key.strip())
                st.rerun()
        st.stop()
    
    st.success("API Key Active")
    model_choice = st.radio("Intelligence Level", ["Gemini 3 Flash (Fast)", "Gemini 3 Pro (Deep)"])
    MODEL_ID = "gemini-1.5-flash" if "Flash" in model_choice else "gemini-1.5-pro" 
    uploaded_file = st.file_uploader("Upload Material", type=['pdf', 'mp4'])

    if st.button("🧹 Clear History"):
        st.session_state.messages = []
        if "last_report" in st.session_state: del st.session_state.last_report
        st.rerun()

client = genai.Client(api_key=api_key)

# --- 6. FILE LOGIC ---
if uploaded_file:
    if "file_uri" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.status("Indexing Context...") as status:
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
            status.update(label="File Ready!", state="complete")

    # This is the "Secret Sauce": Defining the shared file reference clearly
    shared_content = [
        types.Part.from_uri(file_uri=st.session_state.file_uri, mime_type=st.session_state.mime_type)
    ]

    st.title("🎓 Scholar Research Lab")
    m1, m2, m3 = st.columns(3)
    m1.metric("Engine", "Gemini 3 Pro" if "pro" in MODEL_ID else "Gemini 3 Flash")
    m2.metric("Format", st.session_state.mime_type.split('/')[-1].upper())
    m3.metric("Status", "Securely Linked")
    st.divider()

    col_viewer, col_tools = st.columns([1, 1], gap="large")

    with col_viewer:
        st.subheader("📁 Reference Media")
        if "mp4" in st.session_state.mime_type:
            st.video(uploaded_file)
        else:
            st.info(f"Loaded: {st.session_state.file_name}")

    with col_tools:
        tab1, tab2, tab3 = st.tabs(["💬 Deep Chat", "🧠 AI Study Tools", "📄 Export"])

        with tab1:
            chat_container = st.container(height=400)
            if "messages" not in st.session_state: st.session_state.messages = []
            for msg in st.session_state.messages:
                chat_container.chat_message(msg["role"]).write(msg["content"])

            if user_prompt := st.chat_input("Ask a question about this file..."):
                st.session_state.messages.append({"role": "user", "content": user_prompt})
                chat_container.chat_message("user").write(user_prompt)
                with chat_container.chat_message("assistant"):
                    res_box = st.empty()
                    full_res = ""
                    # Combined shared_content + user_prompt for stability
                    response = client.models.generate_content_stream(
                        model=MODEL_ID,
                        contents=shared_content + [user_prompt]
                    )
                    for chunk in response:
                        full_res += chunk.text
                        res_box.markdown(full_res + "▌")
                    res_box.markdown(full_res)
                    st.session_state.messages.append({"role": "assistant", "content": full_res})

        with tab2:
            st.subheader("Automated Insights")
            c1, c2 = st.columns(2)
            if c1.button("🚀 Instant Study Plan"):
                with st.spinner("Analyzing..."):
                    # Using the list addition [file] + [prompt] instead of a nested list
                    res = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=shared_content + ["Based on this file, create a 10-minute study plan."]
                    )
                    st.markdown(res.text)
            
            if c2.button("🔥 Smart Flashcards"):
                with st.spinner("Extracting..."):
                    res = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=shared_content + ["Create 5 practice flashcards from this content."]
                    )
                    st.markdown(res.text)

        with tab3:
            if st.button("✨ Compile PDF Report"):
                with st.spinner("Writing..."):
                    res = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=shared_content + ["Generate a deep-dive study report based on this file."]
                    )
                    st.session_state.last_report = res.text
                    st.markdown(st.session_state.last_report)
            
            if "last_report" in st.session_state:
                st.download_button("📥 Download PDF", create_pdf_bytes(st.session_state.last_report), "Report.pdf")
else:
    st.header("Welcome to the Lab")
    st.info("Upload a file in the sidebar to begin.")





