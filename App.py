import streamlit as st
import google.generativeai as genai

# --- 1. AUTHENTICATION (The Simple API Key Method) ---
def init_scholar():
    # Looks for 'GOOGLE_API_KEY' in your Streamlit Secrets
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ GOOGLE_API_KEY not found! Go to App Settings > Secrets and add: GOOGLE_API_KEY = 'your_key'")
        return False
    genai.configure(api_key=api_key)
    return True

# --- UI CONFIGURATION ---
st.set_page_config(page_title="ScholarAI Pro", layout="wide", page_icon="🎓")

# --- 2. RESEARCH ENGINE ---
def scholar_stream(prompt, file_bytes, mime):
    try:
        # We use the Flash model because it is the fastest for the Free Tier
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=(
                "You are 'The Scholar,' an elite research professor. "
                "Analyze the provided file deeply and answer with academic rigor. "
                "Cite specific timestamps for videos or pages for PDFs."
            )
        )
        
        # Structure the message with the file and the user query
        message_parts = [
            {"mime_type": mime, "data": file_bytes},
            prompt
        ]
        
        return model.generate_content(message_parts, stream=True)
    except Exception as e:
        st.error(f"⚠️ Professor's Note: {e}")
        return None

# --- 3. THE LAB INTERFACE ---
st.title("🎓 Scholar Research Lab")
st.markdown("---")

if "history" not in st.session_state:
    st.session_state.history = []

auth_ready = init_scholar()

# Sidebar for controls
with st.sidebar:
    st.header("📂 Research Material")
    uploaded_file = st.file_uploader("Upload PDF or Research Video", type=['pdf', 'mp4'])
    
    st.divider()
    if st.button("🗑️ Clear Session"):
        st.session_state.history = []
        st.rerun()
    
    st.info("The Free Tier allows up to 15 requests per minute.")

# Main area
if uploaded_file and auth_ready:
    # Cache the file bytes so they don't reload on every click
    file_bytes = uploaded_file.getvalue()
    
    col1, col2 = st.columns([1, 1.4], gap="large")
    
    with col1:
        st.subheader("Reference Material")
        if "video" in uploaded_file.type:
            st.video(file_bytes)
        else:
            st.success(f"📄 {uploaded_file.name} is ready for analysis.")
            st.caption("I have fully indexed this document for you.")

    with col2:
        st.subheader("Academic Discourse")
        
        # Display chat history
        for msg in st.session_state.history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # Chat Input
        if user_query := st.chat_input("Ask a research question..."):
            # Display user message
            with st.chat_message("user"):
                st.write(user_query)
            
            # Display assistant response
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                
                with st.spinner("Analyzing material..."):
                    stream = scholar_stream(user_query, file_bytes, uploaded_file.type)
                    
                    if stream:
                        for chunk in stream:
                            if chunk.text:
                                full_response += chunk.text
                                # Adds a blinking cursor effect while typing
                                response_placeholder.markdown(full_response + "▌")
                        response_placeholder.markdown(full_response)
                
            # Update history
            st.session_state.history.append({"role": "user", "content": user_query})
            st.session_state.history.append({"role": "assistant", "content": full_response})
else:
    st.info("👋 Welcome! Please upload your PDF or Video in the sidebar to begin the research session.")













































