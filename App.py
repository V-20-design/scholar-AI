import streamlit as st
import google.generativeai as genai

# --- 1. AUTHENTICATION ---
def init_scholar():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ GOOGLE_API_KEY not found in Secrets!")
        return False
    genai.configure(api_key=api_key)
    return True

# --- UI CONFIG ---
st.set_page_config(page_title="ScholarAI Pro", layout="wide", page_icon="🎓")

# --- 2. THE CHAT ENGINE ---
def scholar_stream(prompt, file_bytes, mime):
    try:
        # FIX: Changed model to 'gemini-flash-latest' to avoid 404 errors
        model = genai.GenerativeModel(
            model_name="gemini-flash-latest", 
            system_instruction=(
                "You are 'The Scholar,' an elite research professor. "
                "Provide deep academic insights and maintain a professional tone."
            )
        )
        
        content = [
            {"mime_type": mime, "data": file_bytes},
            prompt
        ]
        
        return model.generate_content(content, stream=True)
    except Exception as e:
        # Better error reporting for debugging
        if "404" in str(e):
            st.error("⚠️ Model Error: The requested model ID was not found. Try 'gemini-2.0-flash'.")
        else:
            st.error(f"⚠️ Professor's Note: {e}")
        return None

# --- 3. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab")
st.caption("Powered by Gemini 1.5 Flash • Free Tier")

if "history" not in st.session_state:
    st.session_state.history = []

auth_ready = init_scholar()

with st.sidebar:
    st.header("📂 Research Material")
    uploaded_file = st.file_uploader("Upload PDF or Research Video", type=['pdf', 'mp4'])
    
    st.divider()
    if st.button("🗑️ Clear Session"):
        st.session_state.history = []
        st.rerun()

if uploaded_file and auth_ready:
    file_bytes = uploaded_file.getvalue()
    
    col1, col2 = st.columns([1, 1.4], gap="large")
    
    with col1:
        st.subheader("Reference Material")
        if "video" in uploaded_file.type:
            st.video(file_bytes)
        else:
            st.success(f"📄 {uploaded_file.name} is ready.")

    with col2:
        st.subheader("Academic Discourse")
        
        for msg in st.session_state.history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if user_query := st.chat_input("Ask the Professor..."):
            with st.chat_message("user"):
                st.write(user_query)
            
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                
                with st.spinner("Analyzing..."):
                    stream = scholar_stream(user_query, file_bytes, uploaded_file.type)
                    
                    if stream:
                        for chunk in stream:
                            if chunk.text:
                                full_response += chunk.text
                                response_placeholder.markdown(full_response + "▌")
                        response_placeholder.markdown(full_response)
                
            st.session_state.history.append({"role": "user", "content": user_query})
            st.session_state.history.append({"role": "assistant", "content": full_response})
else:
    st.info("👋 Upload a file in the sidebar to begin.")














































