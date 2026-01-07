import streamlit as st
from google import genai
from google.genai import types
import os, io, time
from fpdf import FPDF
from gtts import gTTS

# --- 1. ENGINE: Pydantic-Safe Initialization ---
def get_api_key():
    return st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

api_key = get_api_key()

# FIX: Pydantic Validation Error fix. 
# We remove the custom timeout dictionary that was causing the crash 
# and use the SDK's internal default handling which is safer for Cloud environments.
client = genai.Client(
    api_key=api_key,
    http_options={'headers': {'x-goog-api-key': api_key}}
)

def safe_gemini_call(prompt, file_uri, mime_type, model_choice):
    model_map = {
        "Gemini 1.5 Flash": "gemini-1.5-flash",
        "Gemini 1.5 Pro": "gemini-1.5-pro",
        "Gemini 2.0 Flash": "gemini-2.0-flash-exp"
    }
    target_model = model_map.get(model_choice, "gemini-1.5-flash")
    
    try:
        file_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)
        response = client.models.generate_content(
            model=target_model,
            contents=[file_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are 'The Scholar,' an expert Research Professor.",
                temperature=0.3
            )
        )
        return response.text
    except Exception as e:
        st.error(f"Professor Busy: {str(e)[:150]}")
        return None

# --- 2. UI STYLING ---
st.set_page_config(page_title="ScholarAI Pro", page_icon="🎓", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .main .block-container { 
        background: rgba(255, 255, 255, 0.03); 
        border-radius: 15px; padding: 2rem; 
        border: 1px solid rgba(255, 255, 255, 0.1); 
    }
    .stButton>button { border-radius: 8px; border: 1px solid #4dabf7; background: #1c1f26; color: white; width: 100%; }
    .stButton>button:hover { background: #4dabf7; color: black; }
    </style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Scholar Admin")
    uploaded_file = st.file_uploader("Upload Source (PDF/MP4)", type=['pdf', 'mp4'])
    model_choice = st.selectbox("Intelligence Tier", ["Gemini 1.5 Flash", "Gemini 1.5 Pro", "Gemini 2.0 Flash"])
    if st.button("🧹 Clear & Reset"):
        st.session_state.clear()
        st.rerun()

# --- 4. THE HANDSHAKE ---
if uploaded_file:
    if "file_uri" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.status("Professor is indexing the context...") as status:
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                # Standard upload call
                status.write("Transferring to Google Cloud...")
                g_file = client.files.upload(file=temp_path)
                
                # Polling for completion
                progress_bar = st.progress(0)
                start_time = time.time()
                
                while g_file.state.name == "PROCESSING":
                    elapsed = time.time() - start_time
                    percent = min(int((elapsed / 60) * 100), 98) 
                    progress_bar.progress(percent)
                    
                    if elapsed > 300: # 5 minute safety cap
                        raise Exception("Indexing timeout.")
                    
                    time.sleep(5) 
                    g_file = client.files.get(name=g_file.name)
                
                progress_bar.progress(100)
                st.session_state.file_uri = g_file.uri
                st.session_state.mime = uploaded_file.type
                st.session_state.file_name = uploaded_file.name
                status.update(label="Handshake Successful!", state="complete")
                
            except Exception as e:
                st.error(f"Handshake Failed: {str(e)}")
                st.stop()
            finally:
                if os.path.exists(temp_path): os.remove(temp_path)

    # --- 5. DASHBOARD ---
    st.title("🎓 Scholar Research Lab")
    col_v, col_a = st.columns([1, 1], gap="large")

    with col_v:
        if "video" in st.session_state.mime: 
            st.video(uploaded_file)
        else: 
            st.info(f"📄 Active File: {st.session_state.file_name}")

    with col_a:
        tabs = st.tabs(["💬 Chat", "🎙️ Audio", "📄 Thesis"])
        
        with tabs[0]:
            if "msgs" not in st.session_state: st.session_state.msgs = []
            container = st.container(height=350)
            for m in st.session_state.msgs: container.chat_message(m["role"]).write(m["content"])
            
            if p := st.chat_input("Ask the Professor..."):
                st.session_state.msgs.append({"role": "user", "content": p})
                container.chat_message("user").write(p)
                ans = safe_gemini_call(p, st.session_state.file_uri, st.session_state.mime, model_choice)
                if ans:
                    container.chat_message("assistant").write(ans)
                    st.session_state.msgs.append({"role": "assistant", "content": ans})

        with tabs[1]:
            if st.button("🔊 Voice Summary"):
                txt = safe_gemini_call("Summarize this in 2 sentences.", st.session_state.file_uri, st.session_state.mime, model_choice)
                if txt:
                    audio_io = io.BytesIO()
                    gTTS(text=txt, lang='en').write_to_fp(audio_io)
                    st.audio(audio_io.getvalue())

        with tabs[2]:
            if st.button("✨ Draft Report"):
                rep = safe_gemini_call("Generate a formal report.", st.session_state.file_uri, st.session_state.mime, model_choice)
                if rep:
                    st.markdown(rep)
                    st.session_state.last_rep = rep
            
            if "last_rep" in st.session_state:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=11)
                pdf.multi_cell(0, 10, txt=st.session_state.last_rep.encode('latin-1', 'replace').decode('latin-1'))
                st.download_button("📥 Download PDF", pdf.output(dest='S'), "Report.pdf")
else:
    st.info("Upload a file to begin.")



















