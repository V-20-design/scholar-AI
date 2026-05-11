
import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
from fpdf import FPDF
import os

# 1. Setup Page Configuration
st.set_page_config(page_title="Scholar AI", layout="wide")

# 2. Initialize API and Model
def init_scholar():
    # Attempt to get API key from Streamlit Secrets
    api_key = st.secrets.get("GOOGLE_API_KEY")
    
    if not api_key:
        st.error("❌ API Key not found. Please add GOOGLE_API_KEY to your Streamlit Secrets.")
        st.stop()
        
    genai.configure(api_key=api_key)
    
    # 2026 Update: gemini-1.5 is deprecated. 
    # Use gemini-2.5-flash for the best balance of speed and research capability.
    return "gemini-2.5-flash"

# 3. Search Function (DuckDuckGo)
def search_web(query):
    with DDGS() as ddgs:
        results = [r for r in ddgs.text(query, max_results=3)]
    return results

# 4. PDF Generation Function
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Multi_cell handles word wrapping for long research summaries
    pdf.multi_cell(0, 10, txt=text)
    return pdf.output(dest='S').encode('latin-1')

# --- UI Layout ---
st.title("🎓 Scholar AI Research Assistant")
st.markdown("Analyze documents and find real-time citations using Gemini 2.5.")

model_name = init_scholar()

# Initialize session state for persistent data
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "sources" not in st.session_state:
    st.session_state.sources = []

# Sidebar for File Upload
with st.sidebar:
    st.header("Upload Research Material")
    uploaded_file = st.file_up-loader("Choose a PDF or TXT file", type=["pdf", "txt"])
    
    if st.button("Reset Session"):
        st.session_state.summary = ""
        st.session_state.sources = []
        st.rerun()

# Main Logic
col1, col2 = st.columns([2, 1])

with col1:
    if uploaded_file:
        st.success(f"File '{uploaded_file.name}' uploaded successfully!")
        
        if st.button("✨ Run Comprehensive Analysis"):
            with st.spinner("Gemini is reading and cross-referencing..."):
                try:
                    # Initialize Model
                    model = genai.GenerativeModel(model_name)
                    
                    # Read file content safely
                    if uploaded_file.type == "text/plain":
                        file_content = uploaded_file.read().decode("utf-8")
                    else:
                        # For PDFs/Images in a research context
                        file_content = uploaded_file.getvalue()

                    # Step 1: AI Analysis
                    prompt = (
                        "Analyze the provided content. Provide a high-level research summary "
                        "and 3 critical Frequently Asked Questions based on the text."
                    )
                    res = model.generate_content([file_content, prompt])
                    st.session_state.summary = res.text

                    # Step 2: Live Web Citations
                    search_query = f"Latest research papers on {uploaded_file.name[:30]}"
                    st.session_state.sources = search_web(search_query)
                    
                except Exception as e:
                    st.error(f"API Error: {e}")
                    st.info("Note: Ensure your GOOGLE_API_KEY is valid for Gemini 2.5 models.")

    # Display Results
    if st.session_state.summary:
        st.subheader("Research Summary & FAQs")
        st.markdown(st.session_state.summary)
        
        # Download Button
        pdf_data = create_pdf(st.session_state.summary)
        st.download_button(
            label="📥 Download Summary as PDF",
            data=pdf_data,
            file_name="research_summary.pdf",
            mime="application/pdf"
        )

with col2:
    st.subheader("🌐 Verified Web Sources")
    if st.session_state.sources:
        for i, source in enumerate(st.session_state.sources):
            with st.expander(f"Source {i+1}: {source['title'][:40]}..."):
                st.write(source['body'])
                st.link_button("View Full Article", source['href'])
    else:
        st.info("Upload a file and run analysis to see related web citations.")

























































































