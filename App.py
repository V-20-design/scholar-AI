import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from gtts import gTTS
import io
import time

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="Scholar AI Pro", 
    page_icon="🎓", 
    layout="wide"
)

# --- 2. DYNAMIC MODEL DISCOVERY (FIXES 404) ---
def init_scholar():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ API Key missing in Secrets!")
        return None
    genai.configure(api_key=api_key)
    try:
        # Discover models to avoid 404 errors
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Flash 1.5 is the most resilient to rate limits
        for target in ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest"]:
            if target in models: return target
        return models[0] if models else "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash"

# --- 3. SESSION INITIALIZATION ---
if "history" not in st.session_state: st.session_state.history = []
if "summary" not in st.session_state: st.session_state.summary = ""
if "faqs" not in st.session_state: st.session_state.faqs = ""
if "model_name" not in st.session_state: st.session_state.model_name = init_scholar()

# --- 4. UTILITIES ---
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

# --- 5. SIDEBAR TOOLS ---
with st.sidebar:
    st.title("🎓 Scholar Tools")
    st.caption(f"Connected to: {st.session_state.model_name}")
    
    uploaded_file = st.file_uploader("Upload Material", type=['pdf', 'mp4', 'png', 'jpg', 'jpeg'], key="main_upload")
    
    if uploaded_file and not st.session_state.summary:
        if st.button("✨ Analyze & Generate FAQs"):
            with st.spinner("Analyzing..."):
                try:
                    model = genai.GenerativeModel(st.session_state.model_name)
                    blob = {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}
                    # Combined request to save tokens
                    res = model.generate_content([blob, "Summarize in 2 paragraphs and provide 3 research FAQs."])
                    st.session_state.summary = res.text
                    st.rerun()
                except Exception as e:
                    st.error("Rate limit hit. Wait 60s.")

    st.divider()
    st.header("⏱️ Focus Timer")
    t1, t2 = st.columns(2)
    if t1.button("▶️ 25m Focus"): st.toast("Timer active!")
    if t2.button("⏹️ Reset"): st.toast("Timer reset.")

    st.divider()
    if st.session_state.history:
        pdf_data = create_pdf(st.session_state.history)
        st.download_button("📥 Save Memo", data=pdf_data, file_name="memo.pdf", use_container_width=True)
        if st.button("🗑️ Clear & Reset Quota", use_container_width=True):
            st.session_state.history = []; st.session_state.summary = ""; st.session_state.faqs = ""
            st.rerun()

# --- 6. MAIN CHAT INTERFACE ---
st.title("🎓 Scholar Pro Lab")

# INSPIRATION BUTTONS
if not st.session_state.history:
    st.subheader("💡 Inspiration")
    cols = st.columns(3)
    if cols[0].button("🧬 Quantum Bio"): st.session_state.active_prompt = "Explain Quantum Biology basics."
    if cols[1].button("🏛️ History"): st.session_state.active_prompt = "Explain the Bronze Age collapse."
    if cols[2].button("🌌 Space"): st.session_state.active_prompt = "How do black holes work?"

tab_chat, tab_insights = st.tabs(["💬 Chat", "📄 Insights & FAQs"])

with tab_insights:
    if st.session_state.summary:
        st.info(st.session_state.summary)
    else:
        st.write("Upload a file for independent insights.")

with tab_chat:
    for i, msg in enumerate(st.session_state.history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant":
                if st.button("🔊 Read Aloud", key=f"v_{i}"):
                    fp = io.BytesIO()
                    gTTS(text=msg["content"], lang='en').write_to_fp(fp)
                    st.audio(fp, format='audio/mp3', autoplay=True)

    query = st.chat_input("Ask a question...")
    
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
                # QUOTA SAVER: We send the current query + the lightweight summary.
                # We DO NOT resend the heavy original file or long history.
                context_prompt = f"Based on this summary: {st.session_state.summary}\n\nUser Question: {query}"
                
                stream = model.generate_content(context_prompt, stream=True)
                for chunk in stream:
                    full_text += chunk.text
                    res_box.markdown(full_text + "▌")
                res_box.markdown(full_text)
                st.session_state.history.append({"role": "assistant", "content": full_text})
                st.rerun()
            except Exception as e:
                if "429" in str(e):
                    st.error("🚨 Rate Limit Hit! Recharging for 60s...")
                    wait_bar = st.progress(0)
                    for p in range(60):
                        time.sleep(1)
                        wait_bar.progress((p+1)/60)
                    st.success("Recharged! Try again.")
                else:
                    st.error(f"Error: {e}")
   





















































































