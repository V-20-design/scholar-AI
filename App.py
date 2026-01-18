import streamlit as st
from google import genai
from google.genai import types
from google.oauth2 import service_account
import re

# --- 1. AUTHENTICATION & HANDSHAKE ---
@st.cache_resource
def init_scholar():
    try:
        # Check if secrets exist
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Secrets not found! Please check your Streamlit Dashboard.")
            return None
        
        # Load the dictionary from secrets
        sa_info = dict(st.secrets["gcp_service_account"])
        
        # KEY CLEANING: Ensure no hidden spaces or bad characters break the padding
        raw_key = sa_info["private_key"]
        key_match = re.search(r"-----BEGIN PRIVATE KEY-----(.*)-----END PRIVATE KEY-----", raw_key, re.DOTALL)
        
        if key_match:
            # Rebuild key with zero whitespace in the middle
            middle = "".join(key_match.group(1).split())
            sa_info["private_key"] = f"-----BEGIN PRIVATE KEY-----\n{middle}\n-----END PRIVATE KEY-----\n"
        
        # Create Google Credentials
        creds = service_account.Credentials.from_service_account_info(sa_info)
        
        # Initialize the Client for Vertex AI (Kenya Stability)
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

# Custom Styling for the "Cool" Interface
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 15px; margin-bottom: 10px; border: 1px solid #ddd; background-color: #fcfcfc; }
    .stChatInputContainer { padding-bottom: 30px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. THE CHAT ENGINE ---
def scholar_stream(prompt, file_bytes, mime):
    try:
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        return client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an elite professor. Provide brilliant academic analysis.",
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
    st.header("📂 Research Material")
    uploaded_file = st.file_uploader("Upload PDF or Research Video", type=['pdf', 'mp4'])
    if st.button("🗑️ Reset Scholar"):
        st.session_state.history = []
        st.rerun()

if uploaded_file and client:
    f_bytes = uploaded_file.getvalue()
    
    col1, col2 = st.columns([1, 1.4])
    with col1:
        st.subheader("Reference Material")
        if "video" in uploaded_file.type:
            st.video(f_bytes)
        else:
            st.success(f"📄 {uploaded_file.name} is Loaded")
            st.info("The Scholar has analyzed the document content.")

    with col2:
        st.subheader("Academic Discourse")
        # Display Conversation
        for msg in st.session_state.history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # Input
        if user_query := st.chat_input("Ask the Professor..."):
            with st.chat_message("user"):
                st.write(user_query)
            
            with st.chat_message("assistant"):
                res_box = st.empty()
                full_text = ""
                with st.status("The Scholar is analyzing...", expanded=True) as status:
                    stream = scholar_stream(user_query, f_bytes, uploaded_file.type)
                    if stream:
                        for chunk in stream:
                            if chunk.text:
                                full_text += chunk.text
                                res_box.markdown(full_text + "▌")
                        res_box.markdown(full_text)
                        status.update(label="Complete!", state="complete")
                    
            st.session_state.history.append({"role": "user", "content": user_query})
            st.session_state.history.append({"role": "assistant", "content": full_text})
else:
    st.info("👋 Welcome! Please upload your material in the sidebar to start the lab.")



































