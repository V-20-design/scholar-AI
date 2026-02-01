import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from gtts import gTTS
import io
import time
import collections

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="Scholar AI Pro", 
    page_icon="🎓", 
    layout="wide"
)

# --- 2. DYNAMIC MODEL DISCOVERY ---
def init_scholar():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ API Key missing in Secrets!")
        return None
    genai.configure(api_key=api_key)
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
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
# NEW: Track interests for personalized inspirations
if "interests" not in st.session_state: st.session_state.interests = collections.Counter()

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

def update_interests(text):
    # Simple keyword tracking for personalization
    keywords = ["science", "history", "math", "art", "space", "bio", "tech", "physics", "coding"]
    for word in keywords:
        if word in text.lower():
            st.session_state.interests[word] += 1

# --- 5. SIDEBAR TOOLS ---
with st.sidebar:
    st.title("🎓 Scholar Tools")
    st.caption(f"Connected to: {st.session_state.model_name}")
    
    uploaded_file = st.file_uploader("Upload Material (Optional)", type=['pdf', 'mp4', 'png', 'jpg', 'jpeg'], key="main_upload")
    
    if uploaded_file and not st.session_state.summary:
        if st.button("✨ Analyze & Generate FAQs"):
            with st.spinner("Analyzing..."):
                try:
                    model = genai.GenerativeModel(st.session_state.model_name)
                    blob = {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}
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
            st.session_state.history = []; st.session_state.summary = ""; st.session_state.faqs = ""; st.session_state.interests = collections.Counter()
            st.rerun()

# --- 6. MAIN CHAT INTERFACE ---
st.title("🎓 Scholar Pro Lab")

# DYNAMIC PERSONALIZED INSPIRATION
st.subheader("💡 Inspiration")
# Default inspirations
suggestions = [("🧬 Quantum Bio", "Quantum Biology basics"), ("🏛️ History", "Bronze Age collapse"), ("🌌 Space", "Black holes")]

# If user has specific interests, swap top suggestion
top_interest = st.session_state.interests.most_common(1)
if top_interest:
    interest_word = top_interest[0][0].capitalize()
    suggestions[0] = (f"🌟 For You: {interest_word}", f"Tell me something advanced about {interest_word}")

cols = st.columns(3)
for idx, (label, prompt) in enumerate(suggestions):
    if cols[idx].button(label):
        st.session_state.active_prompt = prompt

tab_chat, tab_insights = st.tabs(["💬 Chat", "📄 Insights & FAQs"])

with tab_insights:
    if st.session_state.summary:
        st.info(st.session_state.summary)
    else:
        st.write("Upload a file for document-specific insights. Otherwise, use the chat for any topic!")

with tab_chat:
    for i, msg in enumerate(st.session_state.history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant":
                if st.button("🔊 Read Aloud", key=f"v_{i}"):
                    fp = io.BytesIO()
                    gTTS(text=msg["content"], lang='en').write_to_fp(fp)
                    st.audio(fp, format='audio/mp3', autoplay=True)

    query = st.chat_input("Ask anything (with or without a file)...")
    
    if "active_prompt" in st.session_state:
        query = st.session_state.active_prompt
        del st.session_state.active_prompt

    if query:
        update_interests(query)
        st.session_state.history.append({"role": "user", "content": query})
        with st.chat_message("user"): st.write(query)
        
        with st.chat_message("assistant"):
            res_box = st.empty()
            full_text = ""
            try:
                model = genai.GenerativeModel(st.session_state.model_name)
                
                # REVISED LOGIC: Universal Answering
                if st.session_state.summary:
                    context_prompt = f"Context: {st.session_state.summary}\n\nUser Question: {query}"
                else:
                    context_prompt = query # Standard AI answering
                
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
   






















































































