import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from gtts import gTTS
import io

# --- 1. AUTHENTICATION ---
def init_scholar():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ GOOGLE_API_KEY missing!")
        return False
    genai.configure(api_key=api_key)
    return True

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
        # Clean text
        clean_text = entry["content"].encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(w=0, h=8, txt=clean_text, align='L')
        pdf.ln(5)
    
    return bytes(pdf.output())

def get_ai_analysis(file_bytes, mime, prompt):
    try:
        # UPDATED: Using Gemini 2.0 Flash
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        content = [{"mime_type": mime, "data": file_bytes}, prompt]
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        return f"Analysis unavailable: {e}"

# --- 3. MAIN INTERFACE ---
st.title("🎓 Scholar Research Lab Pro")
auth_ready = init_scholar()

# Initialize session states
if "history" not in st.session_state: st.session_state.history = []
if "summary" not in st.session_state: st.session_state.summary = ""
if "faqs" not in st.session_state: st.session_state.faqs = ""

with st.sidebar:
    st.header("📂 Research Material")
    uploaded_file = st.file_uploader("Upload PDF or Video", type=['pdf', 'mp4'])
    
    if st.session_state.history:
        st.divider()
        try:
            pdf_data = create_pdf(st.session_state.history)
            st.download_button(
                label="📥 Download Research Memo",
                data=pdf_data,
                file_name="research_memo.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF Error: {e}")
        
        if st.button("🗑️ Clear Session"):
            st.session_state.history = []; st.session_state.summary = ""; st.session_state.faqs = ""
            st.rerun()

# --- 4. DASHBOARD LOGIC ---
if uploaded_file and auth_ready:
    f_bytes = uploaded_file.getvalue()
    
    # Run Auto-Analysis if empty
    if not st.session_state.summary:
        with st.spinner("The Scholar is analyzing your document..."):
            # UPDATED: Using Gemini 2.0 Flash
            st.session_state.summary = get_ai_analysis(f_bytes, uploaded_file.type, 
                "Summarize this in 3 professional paragraphs for a researcher.")
            st.session_state.faqs = get_ai_analysis(f_bytes, uploaded_file.type, 
                "Generate 4 FAQs a student might ask about this material.")

    tab_chat, tab_summary = st.tabs(["💬 Academic Discourse", "📄 Summary & FAQs"])

    with tab_summary:
        st.subheader("📝 Executive Summary")
        st.info(st.session_state.summary)
        st.divider()
        st.subheader("❓ Suggested Research FAQs")
        st.markdown(st.session_state.faqs)

    with tab_chat:
        col_mat, col_chat = st.columns([1, 1.5], gap="large")
        with col_mat:
            if "video" in uploaded_file.type: st.video(f_bytes)
            else: st.success(f"📄 {uploaded_file.name} is analyzed.")
        
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
                    # UPDATED: Using Gemini 2.0 Flash
                    model = genai.GenerativeModel("gemini-2.0-flash")
                    stream = model.generate_content([{"mime_type": uploaded_file.type, "data": f_bytes}, query], stream=True)
                    for chunk in stream:
                        full_text += chunk.text
                        res_box.markdown(full_text + "▌")
                    res_box.markdown(full_text)
                st.session_state.history.append({"role": "user", "content": query})
                st.session_state.history.append({"role": "assistant", "content": full_text})
                st.rerun()
else:
    st.info("👋 Welcome. Please upload a Research PDF or Video to begin.")


















































