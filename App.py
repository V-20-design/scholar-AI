import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from gtts import gTTS
import io
import time

# --- 1. AUTHENTICATION & AUTO-MODEL DISCOVERY ---
def init_scholar():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ GOOGLE_API_KEY missing from Secrets!")
        return None
    
    genai.configure(api_key=api_key)
    
    # Logic to find the best available model name for your key
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Look for the best Flash model available
        for target in ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "models/gemini-2.0-flash-exp"]:
            if target in available_models:
                return target
        # If no specific flash, return the first available one
        return available_models[0] if available_models else "gemini-1.5-flash"
    except Exception as e:
        st.error(f"Discovery Error: {e}")
        return "gemini-1.5-flash"

st.set_page_config(page_title="Scholar AI Pro", layout="wide", page_icon="🎓")

# --- 2. UTILITIES ---
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

# --- 3. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab Pro")

# Initialize Session
if "model_name" not in st.session_state:
    st.session_state.model_name = init_scholar()
if "history" not in st.session_state: st.session_state.history = []
if "summary" not in st.session_state: st.session_state.summary = ""
if "faqs" not in st.session_state: st.session_state.faqs = ""

with st.sidebar:
    st.header("📂 Research Material")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    
    if st.session_state.model_name:
        st.caption(f"Connected to: `{st.session_state.model_name}`")
    
    if uploaded_file:
        st.divider()
        if not st.session_state.summary:
            if st.button("✨ Generate Summary & FAQs"):
                with st.spinner("Analyzing..."):
                    try:
                        model = genai.GenerativeModel(st.session_state.model_name)
                        content = [{"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}, "Summarize in 3 paragraphs."]
                        st.session_state.summary = model.generate_content(content).text
                        st.session_state.faqs = model.generate_content([content[0], "Generate 4 FAQs."]).text
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
        
    if st.session_state.history:
        st.divider()
        pdf_data = create_pdf(st.session_state.history)
        st.download_button("📥 Download Memo", data=pdf_data, file_name="memo.pdf")
        if st.button("🗑️ Clear Session"):
            st.session_state.history = []; st.session_state.summary = ""; st.session_state.faqs = ""
            st.rerun()

# UI Layout
if uploaded_file and st.session_state.model_name:
    f_bytes = uploaded_file.getvalue()
    tab_chat, tab_summary = st.tabs(["💬 Academic Discourse", "📄 Summary & FAQs"])

    with tab_summary:
        if st.session_state.summary:
            st.subheader("📝 Executive Summary")
            st.info(st.session_state.summary)
            st.divider()
            st.subheader("❓ Suggested Research FAQs")
            st.markdown(st.session_state.faqs)
        else:
            st.info("Click 'Generate Summary' in sidebar.")

    with tab_chat:
        col_mat, col_chat = st.columns([1, 1.5], gap="large")
        with col_mat:
            if "video" in uploaded_file.type: st.video(f_bytes)
            else: st.success(f"📄 {uploaded_file.name} Loaded")
        
        with col_chat:
            for i, msg in enumerate(st.session_state.history):
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    if msg["role"] == "assistant" and i == len(st.session_state.history)-1:
                        if st.button("🔊 Read Aloud"):
                            audio_fp = io.BytesIO()
                            gTTS(text=msg["content"], lang='en').write_to_fp(audio_fp)
                            st.audio(audio_fp, format='audio/mp3')

            if query := st.chat_input("Ask the Professor..."):
                with st.chat_message("user"): st.write(query)
                with st.chat_message("assistant"):
                    full_text = ""
                    res_box = st.empty()
                    try:
                        model = genai.GenerativeModel(st.session_state.model_name)
                        stream = model.generate_content([{"mime_type": uploaded_file.type, "data": f_bytes}, query], stream=True)
                        for chunk in stream:
                            full_text += chunk.text
                            res_box.markdown(full_text + "▌")
                        res_box.markdown(full_text)
                        st.session_state.history.append({"role": "user", "content": query})
                        st.session_state.history.append({"role": "assistant", "content": full_text})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Professor Error: {e}")
else:
    st.info("👋 Upload a file to begin.")
   





























































