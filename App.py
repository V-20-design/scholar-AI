import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from gtts import gTTS
import io
import time

# --- 1. AUTH & STABLE MODEL DISCOVERY ---
def init_scholar():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ GOOGLE_API_KEY missing!")
        return None
    genai.configure(api_key=api_key)
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest"]
        for target in priority:
            if target in available: return target
        return available[0]
    except: return "models/gemini-1.5-flash"

# --- 2. THE ICON FIX ---
# This line sets the icon for the browser tab and the installed PWA
st.set_page_config(
    page_title="Scholar AI Pro", 
    layout="wide", 
    page_icon="🎓"  # This is the graduation cap icon
)

# --- 3. UTILITIES ---
def create_pdf(history):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, txt="Scholar AI - Research Memo", ln=True, align='C')
    pdf.ln(10)
    for entry in history:
        role = "Professor" if entry["role"] == "assistant" else "Scholar"
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 10, txt=f"{role}:", ln=True)
        pdf.set_font("Helvetica", size=11)
        clean_text = entry["content"].encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(w=0, h=8, txt=clean_text, align='L')
        pdf.ln(5)
    return bytes(pdf.output())

# --- 4. INTERFACE ---
if "model_name" not in st.session_state: st.session_state.model_name = init_scholar()
if "history" not in st.session_state: st.session_state.history = []
if "summary" not in st.session_state: st.session_state.summary = ""
if "faqs" not in st.session_state: st.session_state.faqs = ""

st.title("🎓 Scholar Pro: Research Lab")

with st.sidebar:
    st.header("📂 Research Input")
    uploaded_file = st.file_uploader("Upload PDF, Video, or Image", type=['pdf', 'mp4', 'png', 'jpg', 'jpeg'])
    
    if uploaded_file:
        st.success(f"Loaded: {uploaded_file.name}")
        if not st.session_state.summary:
            if st.button("✨ Auto-Summarize"):
                with st.spinner("Scholar is thinking..."):
                    try:
                        model = genai.GenerativeModel(st.session_state.model_name)
                        blob = {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}
                        st.session_state.summary = model.generate_content([blob, "Summarize this in 3 paragraphs."]).text
                        st.session_state.faqs = model.generate_content([blob, "Generate 4 Research FAQs."]).text
                        st.rerun()
                    except Exception as e: st.error(f"Quota Error: {e}")

    st.divider()
    
    # NEW FEATURE: STUDY TIMER (POMODORO)
    st.header("⏱️ Focus Timer")
    if "timer_active" not in st.session_state: st.session_state.timer_active = False
    
    timer_col1, timer_col2 = st.columns(2)
    with timer_col1:
        if st.button("▶️ 25m Focus"):
            st.session_state.timer_active = True
            # In a real Streamlit app, we'd use a background thread, 
            # but for now, we'll show a simple notification.
            st.toast("Focus timer started! 25 minutes.")
    with timer_col2:
        if st.button("⏹️ Reset"):
            st.session_state.timer_active = False
            st.toast("Timer reset.")

    st.divider()
    if st.session_state.history:
        pdf_data = create_pdf(st.session_state.history)
        st.download_button("📥 Save Memo", data=pdf_data, file_name="scholar_memo.pdf", use_container_width=True)
        if st.button("🗑️ Clear Lab", use_container_width=True):
            st.session_state.history = []; st.session_state.summary = ""; st.session_state.faqs = ""
            st.rerun()

# --- 5. MAIN DASHBOARD ---
if uploaded_file and st.session_state.model_name:
    tab1, tab2 = st.tabs(["💬 Professor Chat", "📄 Insights"])

    with tab2:
        if st.session_state.summary:
            st.subheader("📝 Executive Summary")
            st.info(st.session_state.summary)
            st.subheader("❓ Suggested Deep-Dives")
            st.write(st.session_state.faqs)
        else:
            st.info("Tap 'Auto-Summarize' in the sidebar.")

    with tab1:
        for i, msg in enumerate(st.session_state.history):
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg["role"] == "assistant":
                    if st.button(f"🔊 Read Aloud", key=f"v_{i}"):
                        fp = io.BytesIO()
                        gTTS(text=msg["content"], lang='en').write_to_fp(fp)
                        st.audio(fp, format='audio/mp3', autoplay=True)

        if query := st.chat_input("Ask about this material..."):
            st.session_state.history.append({"role": "user", "content": query})
            with st.chat_message("user"): st.write(query)
            
            with st.chat_message("assistant"):
                res_box = st.empty()
                full_text = ""
                try:
                    model = genai.GenerativeModel(st.session_state.model_name)
                    blob = {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}
                    stream = model.generate_content([blob, query], stream=True)
                    for chunk in stream:
                        full_text += chunk.text
                        res_box.markdown(full_text + "▌")
                    res_box.markdown(full_text)
                    st.session_state.history.append({"role": "assistant", "content": full_text})
                    st.rerun()
                except Exception as e: st.error(f"Professor is busy. Wait 60s. Error: {e}")
else:
    st.info("👋 Upload a file to begin.")
   



































































