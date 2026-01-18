import streamlit as st
from google import genai
from google.genai import types
import json, os

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="ScholarAI Pro", layout="wide", page_icon="🎓")

# Custom CSS for a "Cooler" Look
st.markdown("""
    <style>
    .stChatMessage { background-color: #f0f2f6; border-radius: 10px; padding: 10px; margin-bottom: 10px; }
    .stActionButton { background-color: #4CAF50; color: white; }
    </style>
""", unsafe_allow_value=True)

# --- 2. AUTHENTICATION (The "Neighborhood" Fix) ---
@st.cache_resource
def init_scholar():
    project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT")
    sa_json = st.secrets.get("SERVICE_ACCOUNT_JSON")
    
    if not sa_json or not project_id:
        st.error("❌ Credentials missing! Please check Streamlit Secrets.")
        return None
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS_DICT"] = sa_json.strip()
        return genai.Client(vertexai=True, project=project_id, location="us-central1")
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return None

client = init_scholar()

# --- 3. THE ENGINE ---
def scholar_chat(prompt, file_bytes, mime, history):
    try:
        file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        # Combine history for context
        full_contents = [file_part] + history + [prompt]
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=full_contents,
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an elite research assistant. Be insightful, academic, and helpful.",
                temperature=0.3
            )
        )
        return response.text
    except Exception as e:
        return f"⚠️ Error: {str(e)[:100]}"

# --- 4. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab")
st.caption("Advanced Material Analysis via Vertex AI")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for Uploads
with st.sidebar:
    st.header("📂 Research Material")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

if uploaded_file:
    # Preview the file
    file_bytes = uploaded_file.read()
    if "video" in uploaded_file.type:
        st.video(file_bytes)
    else:
        st.info(f"📄 Analyzing: {uploaded_file.name}")

    # Display Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Ask the Scholar..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing material..."):
                # Pass previous messages for context
                history = [types.Content(role=m["role"], parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages[:-1]]
                response = scholar_chat(prompt, file_bytes, uploaded_file.type, history)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
else:
    st.info("👋 Upload a document or video in the sidebar to begin your research.")






























