import streamlit as st
from google import genai
from google.genai import types
from google.oauth2 import service_account
import json

# --- 1. AUTHENTICATION (The Clean Way) ---
@st.cache_resource
def init_scholar():
    try:
        # 1. Grab the table from secrets
        if "gcp_service_account" not in st.secrets:
            st.error("❌ 'gcp_service_account' table not found in Secrets!")
            return None
        
        # 2. Convert to a standard Python dictionary
        sa_info = dict(st.secrets["gcp_service_account"])
        
        # 3. Create credentials object
        creds = service_account.Credentials.from_service_account_info(sa_info)
        
        # 4. Initialize the Client using the Project ID from the main secrets level
        return genai.Client(
            vertexai=True,
            project=st.secrets["GOOGLE_CLOUD_PROJECT"],
            location="us-central1",
            credentials=creds
        )
    except Exception as e:
        st.error(f"❌ Handshake Failed: {e}")
        return None

# --- UI CONFIG ---
st.set_page_config(page_title="ScholarAI Pro", layout="wide", page_icon="🎓")
client = init_scholar()

# --- 2. ENGINE ---
def scholar_stream(prompt, file_bytes, mime):
    try:
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        return client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' a research assistant. Be brilliant and concise.",
                temperature=0.0
            )
        )
    except Exception as e:
        st.error(f"⚠️ Professor Error: {str(e)[:150]}")
        return None

# --- 3. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab")

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.header("📂 Data Source")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    if st.button("🗑️ Clear Session"):
        st.session_state.history = []
        st.rerun()

if uploaded_file and client:
    f_bytes = uploaded_file.getvalue()
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        if "video" in uploaded_file.type:
            st.video(f_bytes)
        else:
            st.success(f"📄 {uploaded_file.name} is ready.")

    with col2:
        # Show history
        for msg in st.session_state.history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # Input Query
        if user_query := st.chat_input("Ask the Professor..."):
            with st.chat_message("user"):
                st.write(user_query)
            
            with st.chat_message("assistant"):
                res_box = st.empty()
                full_text = ""
                with st.spinner("Analyzing..."):
                    stream = scholar_stream(user_query, f_bytes, uploaded_file.type)
                    if stream:
                        for chunk in stream:
                            if chunk.text:
                                full_text += chunk.text
                                res_box.markdown(full_text + "▌")
                        res_box.markdown(full_text)
                    
            st.session_state.history.append({"role": "user", "content": user_query})
            st.session_state.history.append({"role": "assistant", "content": full_text})
else:
    st.info("👋 Upload a file in the sidebar to begin.")

































