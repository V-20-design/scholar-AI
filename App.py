import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from gtts import gTTS
import io
import time

# --- 1. PAGE CONFIG (THE ICON FIX) ---
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
        # Using 1.5 Flash (Highest Free Quota)
        return "models/gemini-1.5-flash"
    except: return "models/gemini-1.5-flash"

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

# --- 4. SESSION INITIALIZATION ---
if "model_name" not in st.session_state: st.session_state.model_name = init_scholar()
if "history" not in st.session_state: st.session_state.history = []
if "summary" not in st.session_state: st.session_state.summary = ""
if "faqs" not in st.session_state: st.session_state.faqs = ""

# --- 5. SIDEBAR TOOLS ---
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
                        # Optimized prompt for speed
                        res = model.generate_content([blob, "Summarize in 2 paragraphs and give 3 FAQs."])
                        st.session_state.summary = res.text
                        st.rerun()
                    except Exception as e: st.error(f"Quota Hit: {e}")

    st.divider()
    st.header("⏱️ Focus Timer")
    t1, t2 = st.columns(2)
    with t1:
        if st.button("▶️ 25m"): st.toast("Timer started!")
    with t2:
        if st.button("⏹️ Reset"): st.toast("Timer reset.")

    st.divider()
    if st.session_state.history:
        pdf_data = create_pdf(st.session_state.history)
        st.download_button("📥 Save Memo", data=pdf_data, file_name="memo.pdf", use_container_width=True)
        if st.button("🗑️ Clear & Reset Quota", use_container_width=True):
            st.session_state.history = []; st.session_state.summary = ""; st.session_state.faqs = ""
            st.rerun()

# --- 6. MAIN INTERFACE ---
st.title("🎓 Scholar Pro Research Lab")

if not uploaded_file:
    st.markdown("🌐 **General Mode**")
    if not st.session_state.history:
        st.subheader("💡 Suggestions")
        if st.button("🧬 Explain Quantum Biology"): st.session_state.active_prompt = "Explain Quantum Biology."
        if st.button("🏛️ Ancient History"): st.session_state.active_prompt = "Tell me about the Bronze Age."

tab_chat, tab_insights = st.tabs(["💬 Chat", "📄 Insights"])

with tab_insights:
    if uploaded_file and st.session_state.summary:
        st.info(st.session_state.summary)
    else: st.write("Upload a file for insights.")

with tab_chat:
    # Render Chat (Restoring Read Aloud)
    for i, msg in enumerate(st.session_state.history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant":
                if st.button("🔊 Read", key=f"read_{i}"):
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
                # QUOTA FIX: Send file + current query ONLY (ignoring history)
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
                st.error("🛑 Rate limit hit. Please wait 60s.")
   










































































