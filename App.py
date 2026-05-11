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
    page_title="Scholar AI Pro v3", 
    page_icon="🎓", 
    layout="wide"
)

# --- 2. ELITE UI STYLING (Glassmorphism & Glow) ---
st.markdown("""
    <style>
    /* Professional Background & Blur */
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
    /* Glowing Buttons */
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
    /* Hidden Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. CORE LOGIC & TOOLS ---
def init_scholar():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ API Key missing in Secrets!")
        return None
    genai.configure(api_key=api_key)
    return "gemini-1.5-flash"

def web_search(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n".join(results)
    except:
        return ""

# --- 4. SESSION INITIALIZATION ---
if "history" not in st.session_state: st.session_state.history = []
if "summary" not in st.session_state: st.session_state.summary = ""
if "model_name" not in st.session_state: st.session_state.model_name = init_scholar()
if "interests" not in st.session_state: st.session_state.interests = collections.Counter()
if "audio_cache" not in st.session_state: st.session_state.audio_cache = {}

# --- 5. SIDEBAR TOOLS ---
with st.sidebar:
    st.markdown("## 🎓 Scholar Elite")
    st.caption("AI Research Suite v3.0")
    
    # VOICE SELECTION
    st.subheader("🎙️ Tutor Voice")
    voice_choice = st.selectbox("Choose Persona", ["Default (Global)", "Arthur (UK Male)", "Grace (AUS Female)", "Liam (US Male)"])
    voice_map = {"Default (Global)": "en", "Arthur (UK Male)": "en-uk", "Grace (AUS Female)": "en-au", "Liam (US Male)": "en-us"}
    
    # LIVE SEARCH TOGGLE
    st.subheader("🌐 Knowledge Base")
    enable_web = st.toggle("Enable Live Web Search (2026)", value=False)
    
    # FILE UPLOADER
    uploaded_file = st.file_uploader("Upload Source Material", type=['pdf', 'txt', 'png', 'jpg'], key="main_upload")
    
    if uploaded_file and not st.session_state.summary:
        if st.button("✨ Deep Analyze"):
            with st.spinner("Extracting insights..."):
                model = genai.GenerativeModel(st.session_state.model_name)
                # Note: For simplicity, we handle Text/Images. For PDFs, PyPDF2 would be needed here.
                if "text" in uploaded_file.type:
                    file_content = uploaded_file.read().decode()
                else:
                    file_content = "An image file was uploaded."
                
                res = model.generate_content([file_content, "Provide a high-level research summary and 3 FAQ questions."])
                st.session_state.summary = res.text
                st.rerun()

    st.divider()
    if st.button("🗑️ Clear All Data"):
        st.session_state.history = []
        st.session_state.summary = ""
        st.rerun()

# --- 6. MAIN LAB ---
st.title("🎓 Scholar Pro Lab")

tab_chat, tab_visual, tab_settings = st.tabs(["💬 Research Chat", "📊 Mind Map", "⚙️ Lab Config"])

with tab_chat:
    # Render History
    for i, msg in enumerate(st.session_state.history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant":
                if st.button(f"🔊 Listen", key=f"v_{i}"):
                    tts = gTTS(text=msg["content"][:400], lang=voice_map[voice_choice])
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    st.audio(fp.getvalue(), format='audio/mp3', autoplay=True)

    # Chat Input
    query = st.chat_input("Enter your research hypothesis or question...")

    if query:
        st.session_state.history.append({"role": "user", "content": query})
        with st.chat_message("user"): st.write(query)
        
        with st.chat_message("assistant"):
            res_box = st.empty()
            full_text = ""
            
            # Augment with Web Search if enabled
            context = st.session_state.summary
            if enable_web:
                web_data = web_search(query)
                context += f"\n\nLive Web Data (2026): {web_data}"
            
            model = genai.GenerativeModel(st.session_state.model_name)
            prompt = f"Context: {context}\n\nQuestion: {query}" if context else query
            
            stream = model.generate_content(prompt, stream=True)
            for chunk in stream:
                full_text += chunk.text
                res_box.markdown(full_text + "▌")
            res_box.markdown(full_text)
            st.session_state.history.append({"role": "assistant", "content": full_text})

with tab_visual:
    st.subheader("📊 Conceptual Mind Map")
    if st.session_state.summary:
        if st.button("Generate Mind Map"):
            with st.spinner("Mapping connections..."):
                model = genai.GenerativeModel(st.session_state.model_name)
                map_prompt = f"Based on this text, create a simple Mermaid.js graphTD flowchart showing the 5 main concepts. Return ONLY the code block starting with graph TD."
                map_res = model.generate_content([st.session_state.summary, map_prompt])
                st.code(map_res.text, language="mermaid")
                st.info("Copy the code above into a Mermaid visualizer or stay tuned for our direct render update!")
    else:
        st.write("Upload a document first to visualize its structure.")

with tab_settings:
    st.subheader("Personalization Engine")
    st.write("The AI currently tracks your research interests to provide better suggestions.")
    st.json(dict(st.session_state.interests))



























































































