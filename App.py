import streamlit as st
from google import genai
from google.genai import types
from google.oauth2 import service_account
import re

# --- 1. AUTHENTICATION (The Scope-Corrected Version) ---
@st.cache_resource
def init_scholar():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Secrets not found!")
            return None
        
        sa_info = dict(st.secrets["gcp_service_account"])
        raw_key = sa_info["private_key"]
        
        # 1. Final Sanitization (Ensuring Multi-4 for Base64)
        match = re.search(r"-----BEGIN PRIVATE KEY-----(.*)-----END PRIVATE KEY-----", raw_key, re.DOTALL)
        if match:
            clean_body = "".join(re.findall(r"[A-Za-z0-9+/=]", match.group(1)))
            length = len(clean_body)
            if length % 4 != 0:
                clean_body = clean_body[:(length - (length % 4))]
            sa_info["private_key"] = f"-----BEGIN PRIVATE KEY-----\n{clean_body}\n-----END PRIVATE KEY-----\n"
        
        # 2. FIX: Explicitly define the OAuth Scopes
        # This prevents the 'invalid_scope' error by requesting full platform access
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        
        creds = service_account.Credentials.from_service_account_info(
            sa_info, 
            scopes=scopes
        )
        
        # 3. Initialize Client (Vertex AI Mode)
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

# --- 2. ENGINE ---
def scholar_stream(prompt, file_bytes, mime):
    try:
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        return client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an elite research professor. Use academic language.",
                temperature=0.1
            )
        )
    except Exception as e:
        # Detailed error reporting for the API
        st.error(f"⚠️ Scholar Error: {str(e)}")
        return None

# --- 3. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab")

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.header("📂 Research Material")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    if st.button("🗑️ Reset Scholar"):
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
                with st.spinner("The Scholar is analyzing..."):
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
    st.info("👋 Upload a file in the sidebar to begin your research session.")












































