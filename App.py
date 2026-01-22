import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from gtts import gTTS
import io
import time

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Scholar AI Pro", 
    page_icon="🎓", 
    layout="wide"
)

# --- 2. AUTH & STABLE MODEL ---
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

# --- 3. UTILITIES ---
def handle_rate_limit():
    """Display a 60-second countdown when a rate limit is hit."""
    st.warning("🛑 Professor is out of breath (Rate Limit Hit). Recharging in 60s...")
    progress_bar = st.progress(0)
    for i in range(60):
        time.sleep(1)
        progress_bar.progress((i + 1) / 60)
    st.success("✅ Ready to continue! Please try your question again.")

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

# --- 4. SESSION INITIALIZATION ---
if "model_name" not in st.session_state: st.session_state.model_name = init_scholar()
if "history" not in st.session_state: st.session_state.history = []
if "summary" not in st.session_state: st.session_state.summary = ""
if "faqs" not in st.session_state: st.session_state.faqs = ""

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🎓 Scholar Tools")
    uploaded_file = st.file_uploader("Upload (Optional)", type=['pdf', 'mp4', 'png', 'jpg', 'jpeg'])
    
    if uploaded_file:
        st.success(f"Context: {uploaded_file.name}")
        if not st.session_state.summary:
            if st.button("✨ Analyze Document"):
                with st.spinner("Analyzing..."):
                    try:
                        model = genai.GenerativeModel(st.session_state.model_name)
                        blob = {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}
                        st.session_state.summary = model.generate_content([blob, "Summarize in 3 paragraphs."]).text
                        st.session_state.faqs = model.generate_content([blob, "Generate 4 research FAQs."]).text
                        st.rerun()
                    except Exception as e:
                        if "429" in str(e): handle_rate_limit()
                        else: st.error(f"Error: {e}")

    st.divider()
    if st.session_state.history:
        pdf_data = create_pdf(st.session_state.history)
        st.download_button("📥 Save Memo", data=pdf_data, file_name="memo.pdf", use_container_width=True)
        if st.button("🗑️ Clear Lab", use_container_width=True):
            st.session_state.history = []; st.session_state.summary = ""; st.session_state.faqs = ""
            st.rerun()
    
    st.divider()
    st.caption("🚀 **Scholar Pro v1.3**")
    st.caption("Auto-Recovery Enabled")

# --- 6. MAIN CHAT ---
st.title("🎓 Scholar Pro Lab")

if not uploaded_file:
    st.markdown("🌐 **General Knowledge Mode**")
    if not st.session_state.history:
        st.subheader("💡 Need Inspiration?")
        s_col1, s_col2, s_col3 = st.columns(3)
        topics = {"🧬 Quantum Bio": "Quantum Biology basics.", "🏛️ History": "Bronze Age collapse.", "🌌 Space": "Black holes."}
        cols = [s_col1, s_col2, s_col3]
        for i, (label, p) in enumerate(topics.items()):
            if cols[i].button(label): st.session_state.active_prompt = p

tab_chat, tab_insights = st.tabs(["💬 Chat", "📄 Insights"])

with tab_insights:
    if uploaded_file and st.session_state.summary:
        st.info(st.session_state.summary); st.write(st.session_state.faqs)
    else: st.write("Upload a file for deep insights.")

with tab_chat:
    for i, msg in enumerate(st.session_state.history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant" and st.button("🔊 Read", key=f"v_{i}"):
                fp = io.BytesIO()
                gTTS(text=msg["content"], lang='en').write_to_fp(fp)
                st.audio(fp, format='audio/mp3', autoplay=True)

    query = st.chat_input("Enter your question...")
    if "active_prompt" in st.session_state:
        query = st.session_state.active_prompt
        del st.session_state.active_prompt

    if query:
        st.session_state.history.append({"role": "user", "content": query})
        with st.chat_message("user"): st.write(query)
        with st.chat_message("assistant"):
            res_box = st.empty()
            full_text = ""
            try:
                model = genai.GenerativeModel(st.session_state.model_name)
                prompt_parts = [query]
                if uploaded_file:
                    prompt_parts.insert(0, {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()})
                
                stream = model.generate_content(prompt_parts, stream=True)
                for chunk in stream:
                    full_text += chunk.text
                    res_box.markdown(full_text + "▌")
                res_box.markdown(full_text)
                st.session_state.history.append({"role": "assistant", "content": full_text})
                st.rerun()
            except Exception as e:
                if "429" in str(e): handle_rate_limit()
                else: st.error(f"Error: {e}")
   








































































