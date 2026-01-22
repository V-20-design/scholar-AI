import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from gtts import gTTS
import io

# --- 1. AUTHENTICATION & CONFIG ---
def init_scholar():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ GOOGLE_API_KEY missing!")
        return False
    genai.configure(api_key=api_key)
    return True

st.set_page_config(page_title="Scholar AI Pro", layout="wide", page_icon="🎓")

# --- 2. UTILITY: PDF GENERATOR ---
def create_pdf(history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Scholar AI - Research Memo", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    
    for entry in history:
        role = "Professor" if entry["role"] == "assistant" else "Scholar"
        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 10, txt=f"{role}:")
        pdf.set_font("Arial", size=11)
        # Replacing characters that Arial doesn't like
        clean_text = entry["content"].encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, txt=clean_text)
        pdf.ln(5)
        
    return pdf.output(dest='S').encode('latin-1')

# --- 3. THE RESEARCH ENGINE ---
def scholar_stream(prompt, file_bytes, mime):
    try:
        model = genai.GenerativeModel(
            model_name="gemini-flash-latest", # Switch to "gemini-2.0-flash" if 404 occurs
            system_instruction="You are 'The Scholar,' an elite professor. Be concise but rigorous."
        )
        content = [{"mime_type": mime, "data": file_bytes}, prompt]
        return model.generate_content(content, stream=True)
    except Exception as e:
        st.error(f"⚠️ API Error: {e}")
        return None

# --- 4. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab Pro")
auth_ready = init_scholar()

if "history" not in st.session_state:
    st.session_state.history = []

# SIDEBAR: Tools and Stats
with st.sidebar:
    st.header("📂 Research Tools")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    
    if st.session_state.history:
        st.divider()
        st.subheader("📝 Export Lab Notes")
        pdf_data = create_pdf(st.session_state.history)
        st.download_button(
            label="Download Research Memo (PDF)",
            data=pdf_data,
            file_name="research_memo.pdf",
            mime="application/pdf"
        )
        
        if st.button("🗑️ Clear Lab Notes"):
            st.session_state.history = []
            st.rerun()

    # Stats Dashboard
    st.divider()
    st.metric(label="Queries This Session", value=len([m for m in st.session_state.history if m["role"]=="user"]))

# MAIN PANEL
if uploaded_file and auth_ready:
    file_bytes = uploaded_file.getvalue()
    col1, col2 = st.columns([1, 1.4], gap="large")
    
    with col1:
        st.subheader("Reference Material")
        if "video" in uploaded_file.type:
            st.video(file_bytes)
        else:
            st.success(f"📄 {uploaded_file.name} Analyzed")

    with col2:
        st.subheader("Academic Discourse")
        
        # Display Chat
        for i, msg in enumerate(st.session_state.history):
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                # Feature: Play Voice for last assistant message
                if msg["role"] == "assistant" and i == len(st.session_state.history) - 1:
                    if st.button("🔊 Read Aloud"):
                        tts = gTTS(text=msg["content"], lang='en')
                        audio_fp = io.BytesIO()
                        tts.write_to_fp(audio_fp)
                        st.audio(audio_fp, format='audio/mp3')

        # Chat Input
        if user_query := st.chat_input("Ask the Professor..."):
            with st.chat_message("user"):
                st.write(user_query)
            
            with st.chat_message("assistant"):
                res_box = st.empty()
                full_text = ""
                with st.spinner("Analyzing..."):
                    stream = scholar_stream(user_query, file_bytes, uploaded_file.type)
                    if stream:
                        for chunk in stream:
                            full_text += chunk.text
                            res_box.markdown(full_text + "▌")
                        res_box.markdown(full_text)
                
            st.session_state.history.append({"role": "user", "content": user_query})
            st.session_state.history.append({"role": "assistant", "content": full_text})
            st.rerun() # Refresh to show the "Read Aloud" button
else:
    st.info("👋 Upload research material to begin your session.")















































