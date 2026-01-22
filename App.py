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

# --- 3. SESSION INITIALIZATION ---
if "model_name" not in st.session_state: st.session_state.model_name = init_scholar()
if "history" not in st.session_state: st.session_state.history = []
if "summary" not in st.session_state: st.session_state.summary = ""
if "faqs" not in st.session_state: st.session_state.faqs = ""

# --- 4. SIDEBAR & TOOLS ---
with st.sidebar:
    st.title("🎓 Scholar Tools")
    
    # Mode Toggle / File Upload
    st.header("📂 Research Material")
    uploaded_file = st.file_uploader("Upload (Optional)", type=['pdf', 'mp4', 'png', 'jpg', 'jpeg'])
    
    if uploaded_file:
        st.success(f"Context: {uploaded_file.name}")
        if not st.session_state.summary:
            if st.button("✨ Analyze Document"):
                with st.spinner("Processing..."):
                    try:
                        model = genai.GenerativeModel(st.session_state.model_name)
                        blob = {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}
                        st.session_state.summary = model.generate_content([blob, "Summarize this in 3 paragraphs."]).text
                        st.session_state.faqs = model.generate_content([blob, "Generate 4 research questions."]).text
                        st.rerun()
                    except Exception as e: st.error(f"Quota Error: {e}")
    else:
        st.info("💡 No file? I'm in **General Research Mode**.")

    st.divider()
    
    # Focus Timer
    st.header("⏱️ Focus Timer")
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        if st.button("▶️ 25m Focus"): st.toast("Timer started!")
    with t_col2:
        if st.button("⏹️ Reset"): st.toast("Timer reset.")

    st.divider()
    if st.session_state.history:
        pdf_data = create_pdf(st.session_state.history)
        st.download_button("📥 Save Memo", data=pdf_data, file_name="research_memo.pdf", use_container_width=True)
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.history = []; st.session_state.summary = ""; st.session_state.faqs = ""
            st.rerun()

# --- 5. MAIN CHAT INTERFACE ---
st.title("🎓 Scholar Pro Research Lab")

# Mode Badge
if uploaded_file:
    st.markdown("🔍 **Currently Analyzing:** " + uploaded_file.name)
else:
    st.markdown("🌐 **General Knowledge Mode** (Ask me anything!)")

# Dashboard Tabs
tab_chat, tab_insights = st.tabs(["💬 Academic Discourse", "📄 Insights"])

with tab_insights:
    if uploaded_file and st.session_state.summary:
        st.subheader("📝 Document Summary")
        st.info(st.session_state.summary)
        st.subheader("❓ Suggested Deep-Dives")
        st.write(st.session_state.faqs)
    elif uploaded_file:
        st.info("Tap 'Analyze Document' in the sidebar to generate insights.")
    else:
        st.info("Upload a file to unlock automated document insights.")

with tab_chat:
    # Display History
    for i, msg in enumerate(st.session_state.history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant":
                if st.button(f"🔊 Read Aloud", key=f"voice_{i}"):
                    fp = io.BytesIO()
                    gTTS(text=msg["content"], lang='en').write_to_fp(fp)
                    st.audio(fp, format='audio/mp3', autoplay=True)

    # Hybrid Chat Input
    if query := st.chat_input("Enter your question..."):
        st.session_state.history.append({"role": "user", "content": query})
        with st.chat_message("user"): st.write(query)
        
        with st.chat_message("assistant"):
            res_box = st.empty()
            full_text = ""
            try:
                model = genai.GenerativeModel(st.session_state.model_name)
                
                # ROUTING LOGIC: File Context vs General Knowledge
                if uploaded_file:
                    prompt_parts = [{"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}, query]
                else:
                    prompt_parts = [query]
                
                stream = model.generate_content(prompt_parts, stream=True)
                for chunk in stream:
                    full_text += chunk.text
                    res_box.markdown(full_text + "▌")
                res_box.markdown(full_text)
                
                st.session_state.history.append({"role": "assistant", "content": full_text})
                st.rerun()
            except Exception as e: 
                st.error("Professor is busy. Please wait 60s for the free-tier reset.")
   





































































