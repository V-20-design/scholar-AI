🎓 Scholar AI Pro: The Intelligent Research Laboratory
Scholar AI Pro is an academic-grade assistant designed to transform static research materials into interactive learning experiences. By leveraging the Gemini 1.5 Flash multimodal engine, it bridges the gap between massive datasets (PDFs, Videos, Images) and efficient, quota-aware AI reasoning.

🌟 Key Innovations
1. Stateless Context Injection (Quota Saver)
Standard AI apps re-send large files with every chat message, quickly hitting 429 RESOURCE_EXHAUSTED errors. Scholar AI Pro uses a "Heavy-to-Light" architecture:

The Heavy Lift: Analyzes the raw file (PDF/Video) once to generate a high-density summary and research FAQs.

The Light Chat: Injects the summary as a persistent "knowledge base" for chat, saving thousands of tokens and ensuring long-running stability on free-tier APIs.

2. Dynamic Model Discovery (Zero-404 Logic)
The app performs a real-time "handshake" with the Google GenAI API upon startup. It automatically identifies and connects to the most resilient available model (e.g., gemini-1.5-flash-latest), eliminating "Model Not Found" errors common in hard-coded applications.

3. Multimodal "Professor" Persona
Visual/Video: Directly "watches" lecture videos or "reads" complex scientific diagrams.

Audio: Integrated gTTS engine for vocalizing research insights for accessibility.

Documentation: Automatic FPDF generation to export your research session into a professional PDF Memo.
