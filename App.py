import streamlit as st
from google import genai
from google.genai import types
from google.oauth2 import service_account

# --------------------------------------------------
# 1. AUTHENTICATION (CLEAN & SAFE)
# --------------------------------------------------

@st.cache_resource
def init_scholar():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Missing 'gcp_service_account' in Streamlit Secrets")
            return None

        creds = service_account.Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"])
        )

        client = genai.Client(
            vertexai=True,
            project=st.secrets["GOOGLE_CLOUD_PROJECT"],
            location="us-central1",
            credentials=creds
        )
        return client

    except Exception as e:
        st.error(f"❌ Authentication Failed: {e}")
        return None


# --------------------------------------------------
# 2. GEMINI CALL (NON-STREAMING — FIXED)
# --------------------------------------------------

def scholar_generate(prompt, file_bytes, mime):
    try:
        file_part = types.Part.from_bytes(
            data=file_bytes,
            mime_type=mime
        )

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are 'The Scholar', a world-class professor. "
                    "Provide deep, structured academic analysis with clarity."
                ),
                temperature=0.1
            )
        )

        return response

    except Exception as e:
        st.error(f"⚠️ Professor Error: {str(e)[:150]}")
        return None


# --------------------------------------------------
# 3. STREAMLIT UI SETUP
# --------------------------------------------------

st.set_page_config(
    page_title="🎓 Scholar Research Lab",
    page_icon="🎓",
    layout="wide"
)

client = init_scholar()

st.markdown("""
<style>
.stChatMessage {
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 10px;
    border: 1px solid #ddd;
    background-color: #f9f9f9;
}
</style>
""", unsafe_allow_html=True)

st.title("🎓 Scholar Research Lab")

# --------------------------------------------------
# 4. SESSION STATE
# --------------------------------------------------

if "history" not in st.session_state:
    st.session_state.history = []


# --------------------------------------------------
# 5. SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.header("📂 Data Source")
    uploaded_file = st.file_uploader(
        "Upload PDF or Research Video",
        type=["pdf", "mp4"]
    )

    if st.button("🗑️ Clear Session"):
        st.session_state.history.clear()
        st.rerun()


# --------------------------------------------------
# 6. MAIN INTERFACE
# --------------------------------------------------

if uploaded_file and client:
    file_bytes = uploaded_file.getvalue()
    mime_type = uploaded_file.type

    col1, col2 = st.columns([1, 1.4])

    # Reference Panel
    with col1:
        st.subheader("Reference Material")
        if "video" in mime_type:
            st.video(file_bytes)
        else:
            st.success(f"📄 {uploaded_file.name} loaded successfully")

    # Chat Panel
    with col2:
        st.subheader("Academic Discourse")

        for msg in st.session_state.history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if user_query := st.chat_input("Ask the Professor..."):
            # User message
            with st.chat_message("user"):
                st.write(user_query)

            # Assistant message
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    response = scholar_generate(
                        user_query,
                        file_bytes,
                        mime_type
                    )

                    if response and response.text:
                        answer = response.text
                        st.markdown(answer)
                    else:
                        answer = "⚠️ No response generated."

            # Save history
            st.session_state.history.append(
                {"role": "user", "content": user_query}
            )
            st.session_state.history.append(
                {"role": "assistant", "content": answer}
            )

else:
    st.info("👋 Upload a PDF or video from the sidebar to begin.")








































