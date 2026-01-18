import streamlit as st
from google import genai
from google.genai import types
import json, os

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="ScholarAI Pro", layout="wide", page_icon="🎓")

# Fixed the 'unsafe_allow_html' typo here
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 15px; margin-bottom: 10px; border: 1px solid #e0e0e0; }
    .stChatInputContainer { padding-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
@st.cache_resource
def init_scholar():
    project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT")
    sa_json = st.secrets.get("SERVICE_ACCOUNT_JSON")
    
    if not sa_json or not project_id:
        st.error("❌ Credentials missing in Streamlit Secrets!")
        return None
    try:
        # Vertex AI setup for Kenya-based stability
        os.environ["GOOGLE_APPLICATION_CREDENTIALS_DICT"] = sa_json.strip()
        return genai.Client(vertexai=True, project=project_id, location="us-central1")
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return None

client = init_scholar()

# --- 3. THE CHAT ENGINE ---
def scholar_chat(prompt, file_bytes, mime, history_msgs):
    try:
        # Convert bytes to a file part
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        
        # Build the conversation context
        contents = [file_part]
        for m in history_msgs:
            role = "user" if m["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
        
        # Add the current prompt
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an expert research professor. Provide deep academic analysis.",
                temperature=0.2
            )
        )
        return response.text
    except Exception as e:
        return f"⚠️ Scholar Connection Error: {str(e)[:150]}"

# --- 4. MAIN INTERFACE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("🎓 Scholar Research Lab")
st.sidebar.header("📁 Material Upload")

with st.sidebar:
    uploaded_file = st.file_uploader("Upload PDF or Research Video", type=['pdf', 'mp4'])
    if st.button("🗑️ Reset Session"):
        st.session_state.messages = []
        st.rerun()

if uploaded_file and client:
    # Handle file reading safely
    file_bytes = uploaded_file.getvalue()
    
    # UI Layout: File on left, Chat on right
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("Reference Material")
        if "video" in uploaded_file.type:
            st.video(file_bytes)
        else:
            st.info(f"📄 Analyzing: {uploaded_file.name}")
            st.caption("Document is loaded into the Professor's memory.")

    with col2:
        st.subheader("Analysis Chat")
        # Display existing messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # New Input
        if prompt := st.chat_input("Ask the Scholar..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Professor is thinking..."):
                    response = scholar_chat(prompt, file_bytes, uploaded_file.type, st.session_state.messages)
                    st.markdown(response)
            
            # Save to history
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.messages.append({"role": "assistant", "content": response})
else:
    st.info("👋 To begin, please upload a research document or video in the sidebar.")































