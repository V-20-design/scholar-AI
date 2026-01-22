import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from gtts import gTTS
import io
import time

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Scholar AI Pro", page_icon="🎓", layout="wide")

# --- 2. AUTH & STABLE MODEL ---
def init_scholar():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ GOOGLE_API_KEY missing!")
        return None
    genai.configure(api_key=api_key)
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prefer 1.5-Flash as it has the most generous free-tier quota
        for target in ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest"]:
            if target in available: return target
        return available[0]
    except: return "models/gemini-1.5-flash"

# --- 3. QUOTA RECOVERY UTILITY ---
def handle_rate_limit():
    st.error("🛑 Daily or Minute Quota Exhausted.")
    st.info("💡 **Tips to fix this:** \n1. Wait 1-2 minutes. \n2. Try a smaller file. \n3. Use 'Clear Lab' to reset the token count.")
    if st.button("Attempt Manual Reconnect"):
        st.rerun()

# --- 4. SESSION INITIALIZATION ---
if "model_name" not in st.session_state: st.session_state.model_name = init_scholar()
if "history" not in st.session_state: st.session_state.history = []
if "summary" not in st.session_state: st.session_state.summary = ""
if "faqs" not in st.session_state: st.session_state.faqs = ""

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🎓 Scholar Tools")
    uploaded_file = st.file_uploader("Upload (Small files work best)", type=['pdf', 'mp4', 'png', 'jpg', 'jpeg'])
    
    if uploaded_file:
        st.success(f"Context: {uploaded_file.name}")
        if not st.session_state.summary:
            if st.button("✨ Quick Analyze"):
                with st.spinner("Processing..."):
                    try:
                        model = genai.GenerativeModel(st.session_state.model_name)
                        blob = {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}
                        # Requesting shorter responses to save tokens
                        st.session_state.summary = model.generate_content([blob, "Brief summary in 2 paragraphs."]).text
                        st.session_state.faqs = model.generate_content([blob, "3 short FAQs."]).text
                        st.rerun()
                    except Exception as e:
                        if "429" in str(e): handle_rate_limit()
                        else: st.error(f"Error: {e}")

    st.divider()
    if st.session_state.history:
        if st.button("🗑️ Clear Lab & Reset Quota", use_container_width=True):
            st.session_state.history = []; st.session_state.summary = ""; st.session_state.faqs = ""
            st.rerun()

# --- 6. MAIN CHAT ---
st.title("🎓 Scholar Pro Lab")

tab_chat, tab_insights = st.tabs(["💬 Chat", "📄 Insights"])

with tab_insights:
    if uploaded_file and st.session_state.summary:
        st.info(st.session_state.summary)
        st.write(st.session_state.faqs)
    else: st.write("Upload a file (under 5MB) for faster processing.")

with tab_chat:
    # Display only the last 4 messages to save tokens
    recent_history = st.session_state.history[-4:]
    for i, msg in enumerate(recent_history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    query = st.chat_input("Enter your question...")

    if query:
        st.session_state.history.append({"role": "user", "content": query})
        with st.chat_message("user"): st.write(query)
        
        with st.chat_message("assistant"):
            res_box = st.empty()
            full_text = ""
            try:
                model = genai.GenerativeModel(st.session_state.model_name)
                # Optimization: Send file context + ONLY the current query (skipping history) to save tokens
                prompt_parts = [query]
                if uploaded_file:
                    prompt_parts.insert(0, {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()})
                
                stream = model.generate_content(prompt_parts, stream=True)
                for chunk in stream:
                    full_text += chunk.text
                    res_box.markdown(full_text + "▌")
                res_box.markdown(full_text)
                st.session_state.history.append({"role": "assistant", "content": full_text})
            except Exception as e:
                if "429" in str(e): handle_rate_limit()
                else: st.error(f"Error: {e}")
   









































































