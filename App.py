import streamlit as st
from google import genai
from google.genai import types
import os
import base64
from fpdf import FPDF

# --- 1. CONFIG & CSS ---
st.set_page_config(page_title="ScholarAI", page_icon="🎓", layout="wide")

def inject_ui():
    st.markdown("""
        <style>
        .stApp { background-color: #0e1117; }
        .main .block-container { background: rgba(255, 255, 255, 0.05); border-radius: 20px; padding: 3rem; border: 1px solid rgba(255, 255, 255, 0.1); }
        h1, h2 { color: #ffffff !important; }
        .stButton>button { background-color: #1c1f26; border: 1px solid #4dabf7; width: 100%; color: white; }
        </style>
    """, unsafe_allow_html=True)

inject_ui()

# --- 2. THE STABLE FILE HANDLER ---
@st.cache_data(show_spinner=False)
def process_file_to_bytes(uploaded_file):
    """Safely reads file and returns bytes + forced mime_type"""
    bytes_data = uploaded_file.getvalue() # Use getvalue() for better stability in Streamlit
    size_mb = len(bytes_data) / (1024 * 1024)
    
    # Check 20MB limit for Inline Data
    if size_mb > 20:
        return None, f"File too large ({size_mb:.1f}MB). Limit is 20MB."
    
    # Standardize Mime-Type
    m_type = uploaded_file.type
    if not m_type or m_type == "application/octet-stream":
        m_type = "application/pdf" if uploaded_file.name.endswith(".pdf") else "video/mp4"
        
    return bytes_data, m_type

# --- 3. AUTH ---
def get_api_key():
    return st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

api_key = get_api_key()
client = genai.Client(api_key=api_key) if api_key else None

# --- 4. SIDEBAR & LOGIC ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    if not api_key:
        st.error("Missing API Key in Secrets.")
        st.stop()
        
    MODEL_ID = st.radio("Model", ["gemini-2.0-flash", "gemini-1.5-pro"])
    uploaded_file = st.file_uploader("Upload (Max 20MB)", type=['pdf', 'mp4'])

if uploaded_file:
    file_bytes, error_or_mime = process_file_to_bytes(uploaded_file)
    
    if file_bytes is None:
        st.error(error_or_mime)
        st.stop()
    
    # Create the part once
    shared_file_part = types.Part.from_bytes(data=file_bytes, mime_type=error_or_mime)
    
    PROFESSOR_ROLE = "You are a Senior Research Professor. Be academic, cited, and sophisticated."

    st.title("🎓 Scholar Research Lab")
    
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.subheader("📁 Reference")
        if "video" in error_or_mime: st.video(uploaded_file)
        else: st.info(f"Context: {uploaded_file.name}")

    with col2:
        tab1, tab2 = st.tabs(["💬 Chat", "🧠 Tools"])
        
        with tab1:
            if "messages" not in st.session_state: st.session_state.messages = []
            for m in st.session_state.messages: st.chat_message(m["role"]).write(m["content"])
            
            if prompt := st.chat_input("Ask Professor..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.chat_message("user").write(prompt)
                
                try:
                    res = client.models.generate_content(
                        model=MODEL_ID,
                        contents=[shared_file_part, prompt],
                        config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)
                    )
                    st.chat_message("assistant").write(res.text)
                    st.session_state.messages.append({"role": "assistant", "content": res.text})
                except Exception as e:
                    st.error(f"Professor is busy. (Technical: {str(e)})")

        with tab2:
            if st.button("🚀 Generate Study Plan"):
                with st.spinner("Drafting..."):
                    # We wrap this in a TRY block to catch the ClientError specifically
                    try:
                        res = client.models.generate_content(
                            model=MODEL_ID,
                            contents=[shared_file_part, "Create a structured study plan for this."],
                            config=types.GenerateContentConfig(system_instruction=PROFESSOR_ROLE)
                        )
                        st.markdown(res.text)
                    except Exception as e:
                        st.error("Request failed. Try a smaller file or wait 60 seconds.")
    






