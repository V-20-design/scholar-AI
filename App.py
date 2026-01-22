import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from gtts import gTTS
import io
import time

# --- 1. PAGE CONFIG (ICON FIX) ---
st.set_page_config(
    page_title="Scholar AI Pro", 
    page_icon="🎓", 
    layout="wide"
)

# --- 2. AUTH & MODEL DISCOVERY ---
def init_scholar():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ API Key missing in Secrets!")
        return None
    genai.configure(api_key=api_key)
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Priority on 1.5-Flash for highest free-tier limits
        return "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in models else models[0]
    except:
        return "models/gemini-1.5-flash"

# --- 3. SESSION INITIALIZATION ---
if "history" not in st.session_state: st.session_state.history = []
if "summary" not in st.session_state: st.session_state.summary = ""
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
    
    uploaded_file = st.file_uploader("Upload Material", type=['pdf', 'mp4', 'png', 'jpg', 'jpeg'], key="user_upload")
    
    if uploaded_file:
        st.success(f"Context: {uploaded_file.name}")
        if not st.session_state.summary:
            if st.button("✨ Analyze Document"):
                with st.spinner("Analyzing..."):
                    try:
                        model = genai.GenerativeModel(st.session_state.model_name)
                        blob = {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}
                        res = model.generate_content([blob, "Brief 2-sentence summary."])
                        st.session_state.summary = res.text
                        st.rerun()
                    except Exception as e:
                        st.error("Rate limit hit. Please wait a moment.")

    st.divider()
    st.header("⏱️ Focus Timer")
    t1, t2 = st.columns(2)
    if t1.button("▶️ 25m"): st.toast("Timer started!")
    if t2.button("⏹️ Reset"): st.toast("Timer reset.")

    st.divider()
    if st.session_state.history:
        pdf_data = create_pdf(st.session_state.history)
        st.download_button("📥 Save Memo", data=pdf_data, file_name="memo.pdf", use_container_width=True)
        if st.button("🗑️ Clear & Reset Quota", use_container_width=True):
            st.session_state.history = []; st.session_state.summary = ""
            st.rerun()

# --- 6. MAIN CHAT ---
st.title("🎓 Scholar Pro Lab")

tab_chat, tab_insights = st.tabs(["💬 Chat", "📄 Insights"])

with tab_insights:
    if st.session_state.summary:
        st.info(st.session_state.summary)
    else:
        st.write("Upload a file for independent insights.")

with tab_chat:
    # Display History
    for i, msg in enumerate(st.session_state.history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant":
                if st.button("🔊 Read", key=f"v_{i}"):
                    fp = io.BytesIO()
                    gTTS(text=msg["content"], lang='en').write_to_fp(fp)
                    st.audio(fp, format='audio/mp3', autoplay=True)

    query = st.chat_input("Ask a question...")
    
    if query:
        st.session_state.history.append({"role": "user", "content": query})
        with st.chat_message("user"): st.write(query)
        
        with st.chat_message("assistant"):
            res_box = st.empty()
            full_text = ""
            try:
                model = genai.GenerativeModel(st.session_state.model_name)
                
                # Payload optimization
                payload = [query]
                if uploaded_file:
                    payload.insert(0, {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()})
                
                # Streaming response
                stream = model.generate_content(payload, stream=True)
                for chunk in stream:
                    full_text += chunk.text
                    res_box.markdown(full_text + "▌")
                res_box.markdown(full_text)
                st.session_state.history.append({"role": "assistant", "content": full_text})
            
            except Exception as e:
                if "429" in str(e):
                    st.error("🚨 Limit Hit! This device is pausing for 60s to recharge.")
                    # Progress bar for visual feedback
                    wait_bar = st.progress(0)
                    for i in range(100):
                        time.sleep(0.6) 
                        wait_bar.progress(i + 1)
                    st.success("Recharged! Try resending your question.")
                else:
                    st.error(f"Error: {e}")
   
















































































