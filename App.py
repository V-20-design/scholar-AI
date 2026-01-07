import streamlit as st
from google import genai
from google.genai import types
import os
import time
from dotenv import load_dotenv, set_key
from fpdf import FPDF

# --- 1. CONFIG ---
st.set_page_config(
    page_title="ScholarAI", 
    page_icon="🎓", 
    layout="wide"
)

# --- 2. UI STYLING ---
def inject_dark_academy_css():
    st.markdown("""
        <style>
        .stApp { background-color: #0e1117; }
        .main .block-container {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .stButton>button { width: 100%; border-radius: 10px; height: 3em; }
        section[data-testid="stSidebar"] { background-color: #16191f !important; }
        </style>
        """, unsafe_allow_html=True)

inject_dark_academy_css()

# --- 3. AUTH ---
env_path = ".env"
if os.path.exists(env_path): load_dotenv(env_path, override=True)

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

# --- 4. SIDEBAR ---
api_key = get_api_key()
with st.sidebar:
    st.title("🛡️ Admin")
    if not api_key:
        new_key = st.text_input("Enter API Key", type="password")
        if st.button("Unlock"):
            if new_key:
                set_key(env_path, "GOOGLE_API_KEY", new_key.strip())
                st.rerun()
        st.stop()
    
    # Using the NEWEST specific model IDs for 2026
    model_choice = st.radio("Model", ["Gemini 2.0 Flash", "Gemini 1.5 Pro"])
    MODEL_ID = "gemini-2.0-flash-exp" if "2.0" in model_choice else "gemini-1.5-pro"
    
    uploaded_file = st.file_uploader("Upload PDF/Video", type=['pdf', 'mp4'])

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

client = genai.Client(api_key=api_key)

# --- 5. SHARED CONFIG ---
# This disables safety filters that often trigger 400 ClientErrors
safety_config = [
    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
]

# --- 6. MAIN LOGIC ---
if uploaded_file:
    if "file_uri" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.status("Processing...") as status:
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
            status.update(label="Ready!", state="complete")

    # The most stable way to reference the file part
    file_part = types.Part.from_uri(file_uri=st.session_state.file_uri, mime_type=st.session_state.mime_type)

    st.title("🎓 Scholar Lab")
    col_viewer, col_tools = st.columns([1, 1], gap="large")

    with col_viewer:
        if "mp4" in st.session_state.mime_type:
            st.video(uploaded_file)
        else:
            st.info(f"Active File: {st.session_state.file_name}")

    with col_tools:
        tab1, tab2 = st.tabs(["💬 Chat", "🧠 Tools"])

        with tab1:
            if "messages" not in st.session_state: st.session_state.messages = []
            for msg in st.session_state.messages:
                st.chat_message(msg["role"]).write(msg["content"])

            if prompt := st.chat_input("Ask something..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.chat_message("user").write(prompt)
                with st.chat_message("assistant"):
                    res_box = st.empty()
                    full_res = ""
                    # Passing safety settings to prevent ClientError
                    for chunk in client.models.generate_content_stream(
                        model=MODEL_ID,
                        contents=[file_part, prompt],
                        config=types.GenerateContentConfig(safety_settings=safety_config)
                    ):
                        full_res += chunk.text
                        res_box.markdown(full_res + "▌")
                    res_box.markdown(full_res)
                    st.session_state.messages.append({"role": "assistant", "content": full_res})

        with tab2:
            if st.button("🚀 Generate Study Plan"):
                with st.spinner("Thinking..."):
                    res = client.models.generate_content(
                        model=MODEL_ID,
                        contents=[file_part, "Create a study plan for this file."],
                        config=types.GenerateContentConfig(safety_settings=safety_config)
                    )
                    st.markdown(res.text)
                    st.session_state.last_report = res.text
            
            if "last_report" in st.session_state:
                st.download_button("📥 Download PDF", create_pdf_bytes(st.session_state.last_report), "Report.pdf")
else:
    st.info("Upload a file to begin.")
