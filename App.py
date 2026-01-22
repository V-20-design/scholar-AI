import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from gtts import gTTS
import io

# --- 1. AUTHENTICATION & CONFIG ---
def init_scholar():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ GOOGLE_API_KEY missing from Secrets!")
        return False
    genai.configure(api_key=api_key)
    return True

st.set_page_config(page_title="Scholar AI Pro", layout="wide", page_icon="🎓")

# --- 2. FIXED PDF GENERATOR ---
def create_pdf(history):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, txt="Scholar AI - Research Memo", ln=True, align='C')
    pdf.ln(10)
    
    for entry in history:
        role = "Professor" if entry["role"] == "assistant" else "Scholar"
        
        # Header for the speaker
        pdf.set_font("Helvetica", 'B', 12)
        pdf.set_text_color(100, 100, 100) if role == "Scholar" else pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, txt=f"{role}:", ln=True)
        
        # Reset color and set font for body
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", size=11)
        
        # FIX: Clean text of non-Latin1 characters and use Effective Page Width (epw)
        clean_text = entry["content"].encode('latin-1', 'replace').decode('latin-1')
        
        # Use multicell with 'pdf.epw' to ensure it never exceeds page width
        pdf.multi_cell(w=0, h=8, txt=clean_text, align='L')
        pdf.ln(5)
        
    # Return as bytes
    return pdf.output()

# --- 3. THE RESEARCH ENGINE ---
def scholar_stream(prompt, file_bytes, mime):
    try:
        # Using 1.5 Flash for the free tier
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction="You are 'The Scholar,' an elite research professor. Use academic language."
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

# SIDEBAR: Tools
with st.sidebar:
    st.header("📂 Research Tools")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    
    if st.session_state.history:
        st.divider()
        st.subheader("📝 Export Lab Notes")
        try:
            pdf_bytes = create_pdf(st.session_state.history)
            st.download_button(
                label="Download Research Memo (PDF)",
                data=pdf_bytes,
                file_name="research_memo.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.warning("Could not generate PDF yet. Continue chatting...")
        
        if st.button("🗑️ Clear Lab Notes"):
            st.session_state.history = []
            st.rerun()

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
            st.success(f"📄 {uploaded_file.name} Loaded")

    with col2:
        st.subheader("Academic Discourse")
        
        for i, msg in enumerate(st.session_state.history):
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg["role"] == "assistant" and i == len(st.session_state.history) - 1:
                    if st.button("🔊 Read Aloud"):
                        tts = gTTS(text=msg["content"], lang='en')
                        audio_fp = io.BytesIO()
                        tts.write_to_fp(audio_fp)
                        st.audio(audio_fp, format='audio/mp3')

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
            st.rerun() 
else:
    st.info("👋 Upload research material to begin.")















































