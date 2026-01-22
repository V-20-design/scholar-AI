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

# --- 2. AUTH & DYNAMIC MODEL DISCOVERY (FIXES 404) ---
def get_best_model():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ API Key missing!")
        return None
    
    genai.configure(api_key=api_key)
    
    try:
        # Get all models that support generating content
        available_models = [
            m.name for m in genai.list_models() 
            if 'generateContent' in m.supported_generation_methods
        ]
        
        # Priority list: Flash 1.5 is the "Quota King"
        priority_list = [
            "models/gemini-1.5-flash-latest",
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro-latest",
            "models/gemini-pro"
        ]
        
        for target in priority_list:
            if target in available_models:
                return target
        
        return available_models[0] # Fallback to first available
    except Exception:
        return "models/gemini-1.5-flash" # Hard fallback

# --- 3. SESSION INITIALIZATION ---
if "model_name" not in st.session_state:
    st.session_state.model_name = get_best_model()
if "history" not in st.session_state:
    st.session_state.history = []
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "faqs" not in st.session_state:
    st.session_state.faqs = ""

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
    
    uploaded_file = st.file_uploader("Upload Material", type=['pdf', 'mp4', 'png', 'jpg', 'jpeg'], key="main_uploader")
    
    if uploaded_file and not st.session_state.summary:
        if st.button("✨ Auto-Analyze & FAQs"):
            with st.spinner("Analyzing..."):
                try:
                    model = genai.GenerativeModel(st.session_state.model_name)
                    blob = {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}
                    # Combined prompt to minimize API calls (Rate Limit protection)
                    res = model.generate_content([blob, "Summarize this in 2 paragraphs, then list 3 research FAQs."])
                    st.session_state.summary = res.text
                    st.rerun()
                except Exception as e:
                    st.error(f"Rate Limit: Please wait 60s.")

    st.divider()
    st.header("⏱️ Focus Timer")
    t1, t2 = st.columns(2)
    if t1.button("▶️ 25m Focus"): st.toast("Timer Started!")
    if t2.button("⏹️ Reset"): st.toast("Timer Reset.")

    st.divider()
    if st.session_state.history:
        pdf_data = create_pdf(st.session_state.history)
        st.download_button("📥 Save Memo", data=pdf_data, file_name="scholar_memo.pdf", use_container_width=True)
        if st.button("🗑️ Clear Lab", use_container_width=True):
            st.session_state.history = []; st.session_state.summary = ""; st.session_state.faqs = ""
            st.rerun()

# --- 6. MAIN CHAT INTERFACE ---
st.title("🎓 Scholar Pro Research Lab")

# INSPIRATION SECTION
if not st.session_state.history:
    st.subheader("💡 Need Inspiration?")
    i_col1, i_col2, i_col3 = st.columns(3)
    if i_col1.button("🧬 Quantum Bio"): st.session_state.active_prompt = "Explain Quantum Biology basics."
    if i_col2.button("🏛️ History"): st.session_state.active_prompt = "What caused the Bronze Age collapse?"
    if i_col3.button("🌌 Astrophysics"): st.session_state.active_prompt = "How do black holes affect time?"

tab_chat, tab_insights = st.tabs(["💬 Chat", "📄 Insights & FAQs"])

with tab_insights:
    if st.session_state.summary:
        st.info(st.session_state.summary)
    else:
        st.write("Upload a file to see independent insights.")

with tab_chat:
    for i, msg in enumerate(st.session_state.history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant":
                if st.button("🔊 Read Aloud", key=f"v_{i}"):
                    fp = io.BytesIO()
                    gTTS(text=msg["content"], lang='en').write_to_fp(fp)
                    st.audio(fp, format='audio/mp3', autoplay=True)

    query = st.chat_input("Ask the Professor...")
    
    # Trigger from Inspiration buttons
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
                # QUOTA PROTECTION: Sending only query + file (no bulky history)
                payload = [query]
                if uploaded_file:
                    payload.insert(0, {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()})
                
                stream = model.generate_content(payload, stream=True)
                for chunk in stream:
                    full_text += chunk.text
                    res_box.markdown(full_text + "▌")
                res_box.markdown(full_text)
                st.session_state.history.append({"role": "assistant", "content": full_text})
                st.rerun()
            except Exception as e:
                if "429" in str(e):
                    st.error("🚨 Rate Limit! Recharging tokens (60s)...")
                    wait_bar = st.progress(0)
                    for p in range(60):
                        time.sleep(1)
                        wait_bar.progress((p+1)/60)
                    st.success("Recharged! Please try again.")
                else:
                    st.error(f"Error: {e}")
   



















































































