import streamlit as st
import google.generativeai as genai
import os
from io import BytesIO
from gtts import gTTS
from fpdf import FPDF

# --- 1. SECURE API CONFIGURATION ---
# This uses the google-generativeai library from your requirements
try:
    # On Streamlit Cloud, it looks in Secrets. Locally, it looks for GEMINI_API_KEY
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("API Key not found or invalid. Please add GEMINI_API_KEY to your Secrets.")
    st.stop()

# --- 2. PAGE UI SETUP ---
st.set_page_config(page_title="Student Study Hub", page_icon="🎓")
st.title("🎓 Smart Student Assistant")
st.markdown("Interact with documents or ask general questions.")

# Initialize Session State
if "doc_text" not in st.session_state:
    st.session_state.doc_text = ""
if "current_filename" not in st.session_state:
    st.session_state.current_filename = None

# --- 3. THE TWO MODES (TABS) ---
tab_doc, tab_random = st.tabs(["📄 Document Mode", "💡 Random Question"])

# --- TAB: DOCUMENT MODE ---
with tab_doc:
    st.subheader("Context-Based Learning")
    uploaded_file = st.file_uploader("Upload your notes (Text file)", type=['txt'])

    if uploaded_file:
        # Process Text File
        if uploaded_file.name != st.session_state.current_filename:
            st.session_state.doc_text = uploaded_file.read().decode("utf-8")
            st.session_state.current_filename = uploaded_file.name
        
        st.success(f"File loaded: {st.session_state.current_filename}")
        
        doc_query = st.text_input("Ask a question about this file:")
        
        if doc_query:
            with st.spinner("Analyzing document..."):
                prompt = f"Use this text to answer: {st.session_state.doc_text}\n\nQuestion: {doc_query}"
                response = model.generate_content(prompt)
                st.info(response.text)
                
                # Feature: Convert answer to Audio (using gtts)
                if st.button("Listen to Answer"):
                    tts = gTTS(text=response.text, lang='en')
                    audio_fp = BytesIO()
                    tts.write_to_fp(audio_fp)
                    st.audio(audio_fp)

# --- TAB: RANDOM QUESTION ---
with tab_random:
    st.subheader("General Knowledge")
    random_q = st.text_area("What's on your mind?", placeholder="Explain a concept...", height=150)
    
    if st.button("Ask Gemini"):
        if random_q.strip():
            with st.spinner("Generating answer..."):
                response = model.generate_content(random_q)
                st.markdown("### 🤖 AI Response:")
                st.write(response.text)
                
                # Feature: Export Answer to PDF (using fpdf2)
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.multi_cell(0, 10, txt=response.text)
                pdf_output = pdf.output(dest='S').encode('latin-1', 'ignore')
                
                st.download_button(
                    label="📥 Download Answer as PDF",
                    data=pdf_output,
                    file_name="ai_answer.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("Please enter a question.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    if st.button("Clear App Data"):
        st.session_state.doc_text = ""
        st.session_state.current_filename = None
        st.rerun()
    st.markdown("---")
    st.write("Using: `google-generativeai`, `gTTS`, and `fpdf2`.")
   




































































