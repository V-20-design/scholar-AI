
import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
from gtts import gTTS
import io
import time
import collections
from duckduckgo_search import DDGS

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="Scholar AI Pro", 
    page_icon="🎓", 
    layout="wide"
)

# --- 2. GLASSMORPHISM UI OVERRIDE ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    }
    .stChatMessage {
        border-radius: 15px;
        backdrop-filter: blur(12px);
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        margin-bottom: 10px;
    }
    .stButton>button {
        border-radius: 20px;
        background: linear-gradient(90deg, #4F8BFF, #3B82F6);
        color: white;
        border: none;
        transition: 0.3s;
        font-weight: bold;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0px 5px 15px rgba(59, 130, 246, 0.5);
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    #splash-screen {
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background-color: #0E1117;
        display: flex; flex-direction: column;
        justify-content: center; align-items: center;
        z-index: 999999;
        animation: fadeout 3s forwards;
    }
    @keyframes fadeout {
        0% { opacity: 1; visibility: visible; }
        80% { opacity: 1; }
        100% { opacity: 0; visibility: hidden; }
    }
    .splash-logo { font-size: 80px; margin-bottom: 20px; }
    .splash-text { color: white; font-family: sans-serif; font-size: 24px; font-weight: bold; }
    </style>
    
    <div id="splash-screen">
        <div class="splash-logo">🎓</div>
        <div class="splash-text">Scholar AI Pro</div>
    </div>
""", unsafe_allow_html=True)

# --- 3. DYNAMIC MODEL DISCOVERY ---
def init_scholar():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ API Key missing in Secrets!")
        return None
    genai.configure(api_key=api_key)
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for target in ["models/gemini-2.0-flash", "models/gemini-1.5-flash-latest", "models/gemini-1.5-flash"]:
            if target in models: return target
        return models[0] if models else "models/gemini-1.5-flash"
    except:
        return "gemini-1.5-flash-latest"

# --- 4. SESSION INITIALIZATION ---
if "history" not in st.session_state: st.session_state.history = []
if "summary" not in st.session_state: st.session_state.summary = ""
if "model_name" not in st.session_state: st.session_state.model_name = init_scholar()
if "interests" not in st.session_state: st.session_state.interests = collections.Counter()
if "audio_cache" not in st.session_state: st.session_state.audio_cache = {}

# --- 5. UTILITIES ---
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
    keywords = ["science", "history", "math", "art", "space", "bio", "tech", "physics", "coding"]
    for word in keywords:
        if word in text.lower():
            st.session_state.interests[word] += 1

# --- 6. SIDEBAR TOOLS ---
with st.sidebar:
    st.markdown("## 🎓 Scholar Elite")
    st.caption(f"System: v3.1 (Active)")
    
    st.subheader("🎙️ Voice Persona")
    voice_choice = st.selectbox("Select Tutor", ["Global (Neutral)", "Arthur (UK)", "Grace (AUS)"])
    voice_map = {"Global (Neutral)": "en", "Arthur (UK)": "en-uk", "Grace (AUS)": "en-au"}

    uploaded_file = st.file_uploader("Upload Material (Optional)", type=['pdf', 'txt', 'png', 'jpg'], key="main_upload")
    
    if uploaded_file and not st.session_state.summary:
        if st.button("✨ Analyze with Citations"):
            with st.spinner("Analyzing content..."):
                try:
                    model = genai.GenerativeModel(st.session_state.model_name)
                    file_bytes = uploaded_file.getvalue()
                    mime_type = uploaded_file.type
                    
                    analysis_prompt = (
                        "Summarize this file in 2 paragraphs and provide 3 research FAQs. "
                        "Cite specific parts of the content in brackets like [Source]."
                    )
                    
                    res = model.generate_content([{"mime_type": mime_type, "data": file_bytes}, analysis_prompt])
                    st.session_state.summary = res.text
                    st.rerun()
                except Exception as e:
                    if "429" in str(e):
                        st.error("⏳ Quota Full: The AI is resting. Please wait 30 seconds.")
                    else:
                        st.error(f"Error: {e}")

    st.divider()
    if st.session_state.history:
        pdf_data = create_pdf(st.session_state.history)
        st.download_button("📥 Save Memo", data=pdf_data, file_name="memo.pdf", use_container_width=True)
        if st.button("🗑️ Clear Lab", use_container_width=True):
            st.session_state.history = []; st.session_state.summary = ""; st.session_state.audio_cache = {}
            st.rerun()

# --- 7. MAIN INTERFACE ---
st.title("🎓 Scholar Pro Lab")

# DYNAMIC PERSONALIZED INSPIRATION
st.subheader("💡 Research Inspiration")
suggestions = [("🧬 Quantum Bio", "Quantum Biology basics"), ("🏛️ History", "Bronze Age collapse"), ("🌌 Space", "Black holes")]
top_interest = st.session_state.interests.most_common(1)
if top_interest:
    interest_word = top_interest[0][0].capitalize()
    suggestions[0] = (f"🌟 For You: {interest_word}", f"Tell me something advanced about {interest_word}")

cols = st.columns(3)
for idx, (label, prompt) in enumerate(suggestions):
    if cols[idx].button(label):
        st.session_state.active_prompt = prompt

tab_chat, tab_insights, tab_visual = st.tabs(["💬 Chat", "📄 Insights & FAQs", "📊 Visual Map"])

with tab_insights:
    if st.session_state.summary:
        st.markdown("### Source Analysis")
        st.info(st.session_state.summary)
    else:
        st.write("Upload a file to unlock research insights.")

with tab_visual:
    st.subheader("📊 Conceptual Structure")
    if st.session_state.summary:
        if st.button("Generate Logic Flow"):
            model = genai.GenerativeModel(st.session_state.model_name)
            map_res = model.generate_content(f"Create a Mermaid.js graphTD flowchart for this: {st.session_state.summary}")
            st.code(map_res.text, language="mermaid")
    else:
        st.write("Upload content first to visualize structure.")

with tab_chat:
    for i, msg in enumerate(st.session_state.history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant":
                if st.button("🔊 Read Aloud", key=f"v_{i}"):
                    if i in st.session_state.audio_cache:
                        st.audio(st.session_state.audio_cache[i], format='audio/mp3', autoplay=True)
                    else:
                        try:
                            audio_text = msg["content"][:500]
                            fp = io.BytesIO()
                            tts = gTTS(text=audio_text, lang=voice_map[voice_choice], slow=False)
                            tts.write_to_fp(fp)
                            st.session_state.audio_cache[i] = fp.getvalue()
                            st.audio(st.session_state.audio_cache[i], format='audio/mp3', autoplay=True)
                        except Exception:
                            st.warning("⚠️ Voice service busy. Try again shortly.")

    query = st.chat_input("Ask a research question...")
    
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
                context_prompt = f"Context: {st.session_state.summary}\n\nQuestion: {query}" if st.session_state.summary else query
                
                stream = model.generate_content(context_prompt, stream=True)
                for chunk in stream:
                    full_text += chunk.text
                    res_box.markdown(full_text + "▌")
                res_box.markdown(full_text)
                st.session_state.history.append({"role": "assistant", "content": full_text})
                st.rerun()
            except Exception as e:
                # 429 HANDLING (Line 175-185)
                if "429" in str(e):
                    st.warning("🚨 Lab Overloaded: Cooling down for 20 seconds...")
                    progress_bar = st.progress(0)
                    for percent_complete in range(100):
                        time.sleep(0.2) # Approx 20 seconds total
                        progress_bar.progress(percent_complete + 1)
                    st.info("System ready. Please click 'Enter' to resubmit.")
                else:
                    st.error(f"Error: {e}")
























































































