import streamlit as st
from google import genai
from google.genai import types
from google.oauth2 import service_account
import time

# --- 1. SETTINGS & STYLE ---
st.set_page_config(page_title="ScholarAI Pro", layout="wide", page_icon="🎓")

st.markdown("""
    <style>
    .stChatMessage { border-radius: 12px; padding: 15px; margin-bottom: 10px; border: 1px solid #ddd; }
    .stChatInputContainer { padding-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. AUTHENTICATION (The Handshake Fix) ---
@st.cache_resource
def init_scholar():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ 'gcp_service_account' table not found in Secrets!")
            return None
        
        # Convert TOML secrets to Python dictionary
        sa_info = dict(st.secrets["gcp_service_account"])
        
        # Repair any hidden newline issues in the key
        sa_info["private_key"] = sa_info["private_key"].replace("\\n", "\n")
        
        # Create the formal Credentials object
        creds = service_account.Credentials.from_service_account_info(sa_info)
        
        # Initialize the Google GenAI Client
        return genai.Client(
            vertexai=True,
            project=st.secrets["GOOGLE_CLOUD_PROJECT"],
            location="us-central1",
            credentials=creds
        )
    except Exception as e:
        st.error(f"❌ Handshake Failed: {e}")
        return None

client = init_scholar()

# --- 3. THE RESEARCH ENGINE ---
def scholar_stream_ask(prompt, file_bytes, mime):
    try:
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        
        # Using stream=True prevents the "infinite thinking" freeze
        return client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' a world-class research professor. Provide high-level academic analysis.",
                temperature=0.2
            )
        )
    except Exception as e:
        st.error(f"⚠️ Professor Error: {str(e)[:200]}")
        return None

# --- 4. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab")

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.header("📂 Research Material")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    if st.button("🗑️ Clear All Sessions"):
        st.session_state.history = []
        st.rerun()

if uploaded_file and client:
    file_bytes = uploaded_file.getvalue()
    
    col1, col2 = st.columns([1, 1.3])
    with col1:
        st.subheader("Reference View")
        if "video" in uploaded_file.type:
            st.video(file_bytes)
        else:
            st.success(f"📄 {uploaded_file.name} loaded successfully.")
            st.info("The Professor has memorized this document.")

    with col2:
        st.subheader("Academic Chat")
        # Display Conversation
        for msg in st.session_state.history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # New Query
        if user_query := st.chat_input("Ask the Scholar..."):
            with st.chat_message("user"):
                st.write(user_query)
            
            with st.chat_message("assistant"):
                response_box = st.empty()
                full_text = ""
                
                with st.status("The Scholar is analyzing...", expanded=True) as status:
                    stream = scholar_stream_ask(user_query, file_bytes, uploaded_file.type)
                    if stream:
                        for chunk in stream:
                            if chunk.text:
                                full_text += chunk.text
                                response_box.markdown(full_text + "▌")
                        
                        response_box.markdown(full_text)
                        status.update(label="Analysis Complete!", state="complete")
                    else:
                        status.update(label="Analysis Failed", state="error")

            # Save to history
            st.session_state.history.append({"role": "user", "content": user_query})
            st.session_state.history.append({"role": "assistant", "content": full_text})
else:
    st.info("👋 Welcome. Please upload a document or video in the sidebar to begin.")


































