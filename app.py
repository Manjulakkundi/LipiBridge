"""
Hinglish Smart Writing Assistant using AI4Bharat
Streamlit Web Application
"""

import html
import time
import streamlit as st
from transliteration import transliterate_text, get_transliteration_engine, SUPPORTED_LANGUAGES
from translation import translate_text, SUPPORTED_TRANSLATION_LANGUAGES
from text_improver import improve_text


# Page configuration
st.set_page_config(
    page_title="Hinglish Smart Writing Assistant | AI4Bharat",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .badge-success {
        background-color: #DEF7EC;
        color: #03543F;
        border: 1px solid #BCF0DA;
    }
    .badge-warning {
        background-color: #FEF08A;
        color: #713F12;
        border: 1px solid #FDE047;
    }
    .metric-card {
        background-color: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 12px;
        margin-top: 8px;
    }
    .output-box {
        background-color: #F8FAFC;
        border: 1.5px solid #CBD5E1;
        border-radius: 8px;
        padding: 16px;
        font-size: 1.35rem;
        font-weight: 500;
        min-height: 120px;
        color: #0F172A;
        word-wrap: break-word;
    }
    .stTextArea textarea {
        font-size: 1.1rem !important;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state variables
if "input_text" not in st.session_state:
    st.session_state.input_text = "mera naam manjunath hai"
if "processed_result" not in st.session_state:
    st.session_state.processed_result = None
if "is_translating" not in st.session_state:
    st.session_state.is_translating = False


def set_sample(sample_text: str):
    st.session_state.input_text = sample_text
    st.session_state.processed_result = None


def clear_text():
    st.session_state.input_text = ""
    st.session_state.processed_result = None


# Sidebar: Controls and Tech Explanation
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Transliteration Language Selection
    lang_options = {
        "hi": "Hindi (हिन्दी) - Devanagari",
        "kn": "Kannada (ಕನ್ನಡ) - Kannada Script"
    }
    selected_lang = st.selectbox(
        "Transliteration Script",
        options=list(lang_options.keys()),
        format_func=lambda x: lang_options[x],
        index=0
    )

    st.markdown("---")
    st.subheader("🌐 Translation Settings")
    source_lang_options = {
        code: meta["name"] for code, meta in SUPPORTED_TRANSLATION_LANGUAGES.items()
    }
    target_lang_options = {
        code: meta["name"]
        for code, meta in SUPPORTED_TRANSLATION_LANGUAGES.items()
        if code != "auto"
    }
    trans_source_lang = st.selectbox(
        "Source Language (for Translate)",
        options=list(source_lang_options.keys()),
        format_func=lambda x: source_lang_options[x],
        index=0,
    )
    trans_target_lang = st.selectbox(
        "Target Language (for Translation)",
        options=list(target_lang_options.keys()),
        format_func=lambda x: target_lang_options[x],
        index=0,
    )

    st.markdown("---")
    st.subheader("🛠️ Processing Features")
    enable_improvement = st.checkbox(
        "Smart Sentence Improvement",
        value=True,
        help="Fixes chat slang, punctuation spacing, capitalization, and adds Purna Viram for Hindi.",
    )
    enable_translation = st.checkbox(
        "Include Translation in Convert",
        value=True,
        help="Translates converted Indic text into the selected Target Language.",
    )

    st.markdown("---")
    st.subheader("💡 Quick Sample Inputs")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.button(
            "🇮🇳 Hindi Intro",
            use_container_width=True,
            on_click=set_sample,
            args=("mera naam manjunath hai",),
            disabled=st.session_state.is_translating,
        )
        st.button(
            "💬 Slang Hinglish",
            use_container_width=True,
            on_click=set_sample,
            args=("plz help me wid this work  ,  kya kar rahe ho???",),
            disabled=st.session_state.is_translating,
        )
        st.button(
            "🇬🇧 English Sample",
            use_container_width=True,
            on_click=set_sample,
            args=("Good morning! Artificial intelligence makes multilingual learning easier.",),
            disabled=st.session_state.is_translating,
        )
    with col_s2:
        st.button(
            "🌸 Kannada Greeting",
            use_container_width=True,
            on_click=set_sample,
            args=("namaskara hegiddira?",),
            disabled=st.session_state.is_translating,
        )
        st.button(
            "📅 Alphanumeric",
            use_container_width=True,
            on_click=set_sample,
            args=("2026 me hum AI seekh rahe hain!",),
            disabled=st.session_state.is_translating,
        )
        st.button(
            "🇫🇷 French Sample",
            use_container_width=True,
            on_click=set_sample,
            args=("Bonjour, comment allez-vous aujourd'hui ?",),
            disabled=st.session_state.is_translating,
        )

    st.markdown("---")
    st.subheader("🔬 AI4Bharat Architecture")
    engine = get_transliteration_engine()
    status = engine.get_status(selected_lang)
    
    if status.get("ai4bharat_available"):
        st.markdown('<div class="status-badge badge-success">● AI4Bharat IndicXlit: Active (CPU)</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge badge-warning">▲ Fallback Engine: Active</div>', unsafe_allow_html=True)
        
    st.caption("""
    - **Transliteration**: AI4Bharat IndicXlit (RNN v0.5) trained on Aksharantar.
    - **Fallback**: pure Python phonetic mapping via `indic-transliteration`.
    - **Translation**: Multi-tier neural translation (Google GTX / MyMemory) with auto-detect and offline lexicon.
    """)


# Main UI Header
st.markdown('<div class="main-title">✍️ Hinglish Smart Writing Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Transliterate Roman-script Hinglish into native Indian scripts, polish phrasing, and translate across English, Hindi, Kannada & French — Powered by AI4Bharat.</div>', unsafe_allow_html=True)

# Main Input Section
input_text = st.text_area(
    "Enter Text (Roman/Hinglish or Source Language):",
    key="input_text",
    height=120,
    placeholder="Type or paste text (e.g., 'mera naam manjunath hai', 'namaskara', or 'Good morning, how are you?')..."
)

# Control Buttons
btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 1])
with btn_col1:
    convert_clicked = st.button(
        "🚀 Convert & Improve",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.is_translating,
    )
with btn_col2:
    translate_clicked = st.button(
        "🌐 Translate Text",
        use_container_width=True,
        disabled=st.session_state.is_translating,
    )
with btn_col3:
    st.button(
        "🗑️ Clear",
        use_container_width=True,
        on_click=clear_text,
        disabled=st.session_state.is_translating,
    )

# Processing Logic: Convert & Improve (Transliteration + Improvement + Optional Translation)
if convert_clicked:
    if not input_text or not input_text.strip():
        st.warning("⚠️ Please enter some text before converting.")
    elif not st.session_state.is_translating:
        st.session_state.is_translating = True
        try:
            with st.spinner("Processing transliteration and translation..."):
                start_total = time.perf_counter()

                # Step 1: Sentence Improvement on Roman input
                improved_input = input_text.strip()
                changes_applied = []
                if enable_improvement:
                    imp_res = improve_text(improved_input, is_indic=False)
                    improved_input = imp_res["improved_text"]
                    changes_applied = imp_res["changes_applied"]

                # Step 2: Transliteration
                xlit_res = transliterate_text(improved_input, lang=selected_lang)
                indic_output = xlit_res["result"]

                # Step 3: Indic Script Post-processing
                indic_changes = []
                if enable_improvement and indic_output:
                    indic_imp = improve_text(indic_output, is_indic=True, lang=selected_lang)
                    indic_output = indic_imp["improved_text"]
                    indic_changes = indic_imp["changes_applied"]

                # Step 4: Translation of converted Indic text to chosen Target Language
                translation_res = None
                if enable_translation and indic_output:
                    translation_res = translate_text(
                        indic_output,
                        source_lang=selected_lang,
                        target_lang=trans_target_lang,
                    )

                total_time_ms = round((time.perf_counter() - start_total) * 1000.0, 2)

                st.session_state.processed_result = {
                    "mode": "convert",
                    "original_input": input_text.strip(),
                    "improved_input": improved_input,
                    "changes_applied": changes_applied + indic_changes,
                    "indic_output": indic_output,
                    "xlit_engine": xlit_res["engine_used"],
                    "is_xlit_fallback": xlit_res["is_fallback"],
                    "xlit_latency": xlit_res["latency_ms"],
                    "translation_res": translation_res,
                    "total_time_ms": total_time_ms,
                    "lang": selected_lang,
                    "target_lang": trans_target_lang,
                }
        finally:
            st.session_state.is_translating = False

# Processing Logic: Direct Text Translation
elif translate_clicked:
    if not input_text or not input_text.strip():
        st.warning("⚠️ Please enter some text to translate.")
    elif not st.session_state.is_translating:
        st.session_state.is_translating = True
        try:
            with st.spinner("Translating text..."):
                start_total = time.perf_counter()
                translation_res = translate_text(
                    input_text.strip(),
                    source_lang=trans_source_lang,
                    target_lang=trans_target_lang,
                )
                total_time_ms = round((time.perf_counter() - start_total) * 1000.0, 2)

                st.session_state.processed_result = {
                    "mode": "translate",
                    "original_input": input_text.strip(),
                    "improved_input": input_text.strip(),
                    "changes_applied": [],
                    "indic_output": translation_res["result"],
                    "xlit_engine": None,
                    "is_xlit_fallback": False,
                    "xlit_latency": 0.0,
                    "translation_res": translation_res,
                    "total_time_ms": total_time_ms,
                    "lang": trans_source_lang,
                    "target_lang": trans_target_lang,
                }
        finally:
            st.session_state.is_translating = False


# Display Results
if st.session_state.processed_result:
    res = st.session_state.processed_result
    st.markdown("---")
    
    out_col1, out_col2 = st.columns(2)
    
    with out_col1:
        st.subheader("📥 Input & Preprocessing")
        st.markdown("**Original Text:**")
        st.info(res["original_input"])
        
        if res["mode"] == "convert" and enable_improvement and res["changes_applied"]:
            st.markdown("**Polished Hinglish:**")
            st.code(res["improved_input"], language="text")
            with st.expander("🔍 View Applied Improvements", expanded=False):
                for ch in res["changes_applied"]:
                    st.write(f"- {ch}")
        
        # Execution Details
        st.markdown("### 📊 Processing Metadata")
        if res["mode"] == "convert" and res["xlit_engine"]:
            badge_cls = "badge-warning" if res["is_xlit_fallback"] else "badge-success"
            st.markdown(f'<div class="status-badge {badge_cls}">Engine: {html.escape(str(res["xlit_engine"]))}</div>', unsafe_allow_html=True)
            st.caption(f"⚡ Total pipeline latency: **{res['total_time_ms']} ms** (Transliteration: {res['xlit_latency']} ms)")
        elif res.get("translation_res"):
            trans = res["translation_res"]
            badge_cls = "badge-warning" if trans.get("is_fallback") else "badge-success"
            st.markdown(f'<div class="status-badge {badge_cls}">Engine: {html.escape(str(trans["engine_used"]))}</div>', unsafe_allow_html=True)
            detected = trans.get("detected_lang")
            if detected and res["lang"] == "auto":
                detected_label = SUPPORTED_TRANSLATION_LANGUAGES.get(detected, {}).get("name", detected)
                st.caption(f"🔍 Auto-detected source language: **{detected_label}** (`{detected}`)")
            st.caption(f"⚡ Translation latency: **{res['total_time_ms']} ms**")

    with out_col2:
        if res["mode"] == "convert":
            lang_title = "Hindi (Devanagari)" if res["lang"] == "hi" else "Kannada"
            st.subheader(f"✨ Converted Output ({lang_title})")
            
            safe_indic = html.escape(res["indic_output"]).replace("\n", "<br>")
            st.markdown(f'<div class="output-box">{safe_indic}</div>', unsafe_allow_html=True)
            st.write("")
            st.code(res["indic_output"], language="text")

            if res.get("translation_res"):
                trans = res["translation_res"]
                tgt_label = SUPPORTED_TRANSLATION_LANGUAGES.get(
                    res.get("target_lang", "en"), {}
                ).get("name", "English")
                st.subheader(f"🌐 {tgt_label} Translation")
                if trans.get("success"):
                    if trans.get("is_fallback"):
                        st.info(trans["result"])
                    else:
                        st.success(trans["result"])
                else:
                    st.error(trans.get("error") or "Translation failed. Please verify your network connection.")
                st.caption(f"Translation Engine: {trans['engine_used']} ({trans['latency_ms']} ms)")
        else:
            trans = res["translation_res"]
            tgt_code = res.get("target_lang", "en")
            tgt_label = SUPPORTED_TRANSLATION_LANGUAGES.get(tgt_code, {}).get("name", tgt_code)
            st.subheader(f"🌐 Translated Output ({tgt_label})")

            if trans.get("success"):
                safe_trans = html.escape(trans["result"]).replace("\n", "<br>")
                st.markdown(f'<div class="output-box">{safe_trans}</div>', unsafe_allow_html=True)
                st.write("")
                st.code(trans["result"], language="text")
                if trans.get("is_fallback"):
                    st.info(f"Notice: Translated using fallback ({trans['engine_used']}).")
            else:
                st.error(trans.get("error") or "Translation failed. Please check your network connection or language selection.")

        # Export & Action Tools
        st.write("")
        col_down1, col_down2 = st.columns(2)
        with col_down1:
            if res["mode"] == "convert":
                export_content = (
                    f"--- Hinglish Smart Writing Assistant ---\n"
                    f"Target Script: {res['lang']}\n"
                    f"Original Input: {res['original_input']}\n"
                    f"Transliterated: {res['indic_output']}\n"
                )
                if res.get("translation_res") and res["translation_res"].get("success"):
                    export_content += f"Translation ({res.get('target_lang', 'en')}): {res['translation_res']['result']}\n"
                export_content += f"Engine: {res['xlit_engine']}\n"
                export_text_available = bool(res["indic_output"])
            else:
                trans = res["translation_res"]
                export_content = (
                    f"--- Hinglish Smart Writing Assistant (Translation) ---\n"
                    f"Source Language: {trans.get('detected_lang') or res['lang']}\n"
                    f"Target Language: {res.get('target_lang', 'en')}\n"
                    f"Original Input: {res['original_input']}\n"
                    f"Translated Output: {trans.get('result', '')}\n"
                    f"Engine: {trans.get('engine_used', '')}\n"
                )
                export_text_available = bool(trans.get("success") and trans.get("result"))

            if export_text_available:
                st.download_button(
                    label="📥 Download Output (.txt)",
                    data=export_content,
                    file_name=f"output_{res['lang']}_{int(time.time())}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

# Informational Tabs
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📚 Technology & Models", "🧪 Evaluation Summary", "ℹ️ About Project"])

with tab1:
    st.markdown("""
    ### 🧠 AI4Bharat Resources & System Design
    This project demonstrates cutting-edge Indian language NLP using AI4Bharat open-source technologies:
    
    1. **AI4Bharat IndicXlit**:
       - State-of-the-art multilingual transliteration engine trained on the **Aksharantar** dataset (largest public dataset for Indic transliteration containing over 26 million word pairs).
       - Runs directly on CPU using an optimized Recurrent Neural Network (RNN seq2seq with attention) or Transformer architecture.
    
    2. **Graceful Phonetic Fallback**:
       - To guarantee zero downtime and reliable lab demonstration, an automated fallback engine (`indic-transliteration`) handles edge cases or offline environments seamlessly.
       - The UI dynamically badges whether the pretrained neural weights or the phonetic fallback was invoked.

    3. **Multilingual Translation & Auto-Detection**:
       - Supports English, Hindi, Kannada, and French with automatic source-language detection, paragraph-preserving chunking for long inputs, multi-tier online fallback (Google GTX / MyMemory / deep-translator), and a curated offline bilingual lexicon.
    """)

with tab2:
    st.markdown("### 📊 Benchmark Results (35 Representative Cases)")
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Total Test Cases", "35")
    col_m2.metric("Pass Rate", "97.14%")
    col_m3.metric("Avg Character Accuracy", "91.19%")
    col_m4.metric("Avg CER", "0.088")
    
    st.markdown("""
    - **Hindi Character Accuracy**: **93.11%**
    - **Kannada Character Accuracy**: **87.51%**
    - **Evaluation Metric**: Character Error Rate (CER) via Levenshtein Distance.
    - Run the evaluation locally anytime: `python evaluate.py`
    """)

with tab3:
    st.markdown("""
    ### 🎓 College Mini-Project Submission
    - **Project Name**: Hinglish Smart Writing Assistant using AI4Bharat
    - **Domain**: Multilingual Natural Language Processing (NLP) & Computational Linguistics
    - **Submission Type**: College Lab Mini-Project 4
    - **Environment**: Windows 11, VS Code, Python 3.12, Streamlit, CPU-only (No GPU required)
    - **Official AI4Bharat Repositories**:
      - [AI4Bharat IndicXlit GitHub](https://github.com/AI4Bharat/IndianNLP-Transliteration)
      - [AI4Bharat IndicTrans2 GitHub](https://github.com/AI4Bharat/IndicTrans2)
    """)
