import streamlit as st
from google import genai
from google.genai import types
from google.oauth2 import service_account
import re

# --- 1. AUTHENTICATION (The Ultra-Sanitized Version) ---
@st.cache_resource
def init_scholar():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ 'gcp_service_account' missing in Secrets!")
            return None
        
        sa_info = dict(st.secrets["gcp_service_account"])
        
        # SANITIZATION: This removes the ('Unused bytes', b'\xb8') error
        raw_key = sa_info["private_key"]
        
        # Extract only the data between the markers
        key_body = re.search(r"-----BEGIN PRIVATE KEY-----(.*)-----END PRIVATE KEY-----", raw_key, re.DOTALL)
        
        if key_body:
            # Join all parts and strip EVERY non-base64 character (spaces, tabs, special bytes)
            clean_content = "".join(key_body.group(1).split())
            # Reconstruct with clean newlines
            sa_info["private_key"] = f"-----BEGIN PRIVATE KEY-----\n{clean_content}\n-----END PRIVATE KEY-----\n"
        
        # Initialize credentials
        creds = service_account.Credentials.from_service_account_info(sa_info)
        
        # Initialize the Client for Vertex AI
        return genai.Client(
            vertexai=True,
            project=st.secrets["GOOGLE_CLOUD_PROJECT"],
            location="us-central1",
            credentials=creds
        )
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}")
        return None

# --- UI CONFIG ---
st.set_page_config(page_title="ScholarAI Pro", layout="wide", page_icon="🎓")
client = init_scholar()

# --- 2. THE CHAT ENGINE ---
def scholar_stream(prompt, file_bytes, mime):
    try:
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        return client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an elite research professor.",
                temperature=0.1
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
    uploaded_file = st.file_uploader("Upload PDF or Research Video", type=['pdf', 'mp4'])
    if st.button("🗑️ Clear Session"):
        st.session_state.history = []
        st.rerun()

if uploaded_file and client:
    f_bytes = uploaded_file.getvalue()
    
    col1, col2 = st.columns([1, 1.4])
    with col1:
        if "video" in uploaded_file.type:
            st.video(f_bytes)
        else:
            st.success(f"📄 {uploaded_file.name} is ready.")

    with col2:
        for msg in st.session_state.history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

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
    st.info("👋 Upload a file to start.")




































