"""
Translation Module for WWLLM / Hinglish Smart Writing Assistant.
Supports multilingual text translation across English, Hindi, Kannada, and French
with automatic source-language detection, paragraph-preserving chunking, and
fault-tolerant multi-tier fallbacks.

Tiers:
1. Google Translate Neural Endpoint (POST translate.googleapis.com, auto-detect & long text)
2. MyMemory Neural Translation (via deep-translator, chunked <= 450 chars)
3. GoogleTranslator (via deep-translator, chunked)
4. Offline Bilingual Lexicon Fallback (curated phrase dictionary)
"""

import re
import time
import logging
from typing import Dict, Any, Optional, List

import requests

logger = logging.getLogger(__name__)


# Supported translation languages and provider locale mappings
SUPPORTED_TRANSLATION_LANGUAGES: Dict[str, Dict[str, Optional[str]]] = {
    "auto": {"name": "Auto-Detect", "mymemory": None},
    "en": {"name": "English", "mymemory": "en-GB"},
    "hi": {"name": "Hindi (हिन्दी)", "mymemory": "hi-IN"},
    "kn": {"name": "Kannada (ಕನ್ನಡ)", "mymemory": "kn-IN"},
    "fr": {"name": "French (Français)", "mymemory": "fr-FR"},
}

LANGUAGE_ALIASES: Dict[str, str] = {
    "auto": "auto",
    "auto-detect": "auto",
    "detect": "auto",
    "en": "en",
    "en-gb": "en",
    "en-us": "en",
    "english": "en",
    "hi": "hi",
    "hi-in": "hi",
    "hindi": "hi",
    "kn": "kn",
    "kn-in": "kn",
    "kannada": "kn",
    "fr": "fr",
    "fr-fr": "fr",
    "french": "fr",
    "français": "fr",
}

FRENCH_MARKERS = {
    "bonjour", "bonsoir", "merci", "salut", "comment", "allez", "vous", "nous",
    "je", "suis", "est", "sont", "avec", "pour", "dans", "les", "des", "une",
    "mon", "ton", "votre", "notre", "oui", "non", "aujourd'hui", "demain",
    "français", "très", "bien", "maison", "école", "quel", "quelle", "pourquoi",
}


# Curated offline bilingual dictionary keyed by (source_lang, target_lang)
OFFLINE_PAIR_DICTIONARY: Dict[tuple, Dict[str, str]] = {
    ("hi", "en"): {
        "नमस्ते": "Hello / Greetings",
        "नमस्कार": "Greetings",
        "मेरा नाम मंजुनाथ है": "My name is Manjunath.",
        "मेरा नाम मंजुनाथ है.": "My name is Manjunath.",
        "आप कैसे हो?": "How are you?",
        "आप कैसे हैं?": "How are you?",
        "आप कइसे हो?": "How are you?",
        "शुभ प्रभात": "Good morning.",
        "शुभ प्रभात, आपका दिन शुभ हो!": "Good morning, have a great day!",
        "आज 15 अगस्त है": "Today is August 15th.",
        "कृपया मेरी मदद करें": "Please help me.",
        "मैं ठीक हूँ": "I am fine.",
        "मेरा भारत महान": "My India is great.",
        "धन्यवाद दोस्तों": "Thank you, friends.",
        "धन्यवाद": "Thank you.",
        "शुक्रिया": "Thank you.",
        "दिल्ली भारत की राजधानी है": "Delhi is the capital of India.",
        "आज मौसम बहुत अच्छा है": "Today the weather is very good.",
        "विद्यालय": "School",
        "दिवाली की शुभकामनाएं": "Happy Diwali wishes.",
        "हाँ": "Yes",
        "नहीं": "No",
        "अलविदा": "Goodbye",
        "शुभ रात्रि": "Good night",
    },
    ("kn", "en"): {
        "ನಮಸ್ಕಾರ": "Hello / Greetings",
        "ನಮಸ್ಕಾರ ಹೇಗಿದ್ದಿರ": "Hello, how are you?",
        "ಹೇಗಿದ್ದೀರ?": "How are you?",
        "ಹೇಗಿದ್ದೀರಾ?": "How are you?",
        "ನನ್ನ ಹೆಸರು ಮಂಜುನಾಥ": "My name is Manjunath.",
        "ಕರ್ನಾಟಕ ಸುಂದರ ರಾಜ್ಯ": "Karnataka is a beautiful state.",
        "ಧನ್ಯವಾದಗಳು": "Thank you.",
        "ಧನ್ಯವಾದ": "Thank you.",
        "ಶುಭೋದಯ": "Good morning.",
        "ಊಟ ಆಯ್ತಾ?": "Did you have food?",
        "ಇವತ್ತು ತುಂಬಾ ಬಿಸಿ ಇದೆ": "Today is very hot.",
        "ಬನ್ನಿ ಕೂತ್ಕೊಳ್ಳಿ": "Please come and sit.",
        "ಹೌದು": "Yes",
        "ಇಲ್ಲ": "No",
        "ಶುಭ ರಾತ್ರಿ": "Good night",
    },
    ("en", "hi"): {
        "hello": "नमस्ते",
        "good morning": "शुभ प्रभात",
        "thank you": "धन्यवाद",
        "how are you?": "आप कैसे हैं?",
        "i am fine": "मैं ठीक हूँ",
        "yes": "हाँ",
        "no": "नहीं",
        "good night": "शुभ रात्रि",
    },
    ("en", "kn"): {
        "hello": "ನಮಸ್ಕಾರ",
        "good morning": "ಶುಭೋದಯ",
        "thank you": "ಧನ್ಯವಾದಗಳು",
        "how are you?": "ನೀವು ಹೇಗಿದ್ದೀರಾ?",
        "yes": "ಹೌದು",
        "no": "ಇಲ್ಲ",
        "good night": "ಶುಭ ರಾತ್ರಿ",
    },
    ("en", "fr"): {
        "hello": "Bonjour",
        "good morning": "Bonjour",
        "thank you": "Merci",
        "how are you?": "Comment allez-vous ?",
        "i am fine": "Je vais bien",
        "yes": "Oui",
        "no": "Non",
        "good night": "Bonne nuit",
    },
    ("fr", "en"): {
        "bonjour": "Hello",
        "merci": "Thank you",
        "oui": "Yes",
        "non": "No",
        "bonne nuit": "Good night",
        "comment allez-vous ?": "How are you?",
    },
}

# Preserve backward-compatible module attribute
OFFLINE_DICTIONARY = {
    "hi": OFFLINE_PAIR_DICTIONARY[("hi", "en")],
    "kn": OFFLINE_PAIR_DICTIONARY[("kn", "en")],
}


def normalize_language_code(lang: Optional[str]) -> Optional[str]:
    """Normalize a language code or name to canonical ISO code ('auto', 'en', 'hi', 'kn', 'fr')."""
    if not lang or not isinstance(lang, str):
        return None
    return LANGUAGE_ALIASES.get(lang.strip().lower())


def detect_language(text: str) -> str:
    """
    Lightweight script and token-based language detector for offline/pre-flight resolution.
    Returns one of: 'hi', 'kn', 'fr', 'en'.
    """
    if not text or not text.strip():
        return "en"

    # Script detection using Unicode ranges
    devanagari_count = len(re.findall(r"[\u0900-\u097F]", text))
    kannada_count = len(re.findall(r"[\u0C80-\u0CFF]", text))

    if devanagari_count > 0 and devanagari_count >= kannada_count:
        return "hi"
    if kannada_count > 0:
        return "kn"

    # French diacritic or stop-word detection
    if re.search(r"[àâäçéèêëîïôöùûüÿœæÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒÆ]", text):
        return "fr"

    tokens = set(re.findall(r"[a-zA-ZÀ-ÿ']+", text.lower()))
    if len(tokens.intersection(FRENCH_MARKERS)) >= 2 or (
        len(tokens) <= 3 and len(tokens.intersection(FRENCH_MARKERS)) >= 1
    ):
        return "fr"

    return "en"


def chunk_text_preserving_paragraphs(text: str, max_chars: int = 1500) -> List[Dict[str, Any]]:
    """
    Split text into line/sentence chunks <= max_chars while preserving newline structure.
    Returns list of dicts: {'text': str, 'is_break': bool}
    """
    lines = text.split("\n")
    chunks: List[Dict[str, Any]] = []

    for idx, line in enumerate(lines):
        if idx > 0:
            chunks.append({"text": "\n", "is_break": True})

        stripped = line.strip()
        if not stripped:
            continue

        if len(stripped) <= max_chars:
            chunks.append({"text": stripped, "is_break": False})
            continue

        # Split long line by sentence boundaries first
        sentences = re.split(r"(?<=[.!?।])\s+", stripped)
        current_buf = ""
        for sent in sentences:
            if not sent:
                continue
            if len(sent) > max_chars:
                if current_buf:
                    chunks.append({"text": current_buf, "is_break": False})
                    current_buf = ""
                words = sent.split(" ")
                word_buf = ""
                for w in words:
                    candidate = f"{word_buf} {w}".strip() if word_buf else w
                    if len(candidate) <= max_chars:
                        word_buf = candidate
                    else:
                        if word_buf:
                            chunks.append({"text": word_buf, "is_break": False})
                        if len(w) > max_chars:
                            for i in range(0, len(w), max_chars):
                                chunks.append({"text": w[i:i + max_chars], "is_break": False})
                            word_buf = ""
                        else:
                            word_buf = w
                if word_buf:
                    chunks.append({"text": word_buf, "is_break": False})
            else:
                candidate = f"{current_buf} {sent}".strip() if current_buf else sent
                if len(candidate) <= max_chars:
                    current_buf = candidate
                else:
                    if current_buf:
                        chunks.append({"text": current_buf, "is_break": False})
                    current_buf = sent

        if current_buf:
            chunks.append({"text": current_buf, "is_break": False})

    return chunks


class TranslationEngine:
    """
    Multilingual Translation Engine supporting bidirectional translation between
    English, Hindi, Kannada, and French with Auto-Detect and offline fallback.
    """

    GTX_URL = "https://translate.googleapis.com/translate_a/single"

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds

    def _offline_translate(
        self, text: str, lang: str = "hi", target_lang: str = "en"
    ) -> Optional[str]:
        """Check the curated offline lexicon for exact or word-by-word matches."""
        src = normalize_language_code(lang) or lang
        tgt = normalize_language_code(target_lang) or target_lang
        clean = text.strip()
        lang_dict = OFFLINE_PAIR_DICTIONARY.get((src, tgt), {})
        if not lang_dict:
            return None

        # 1. Exact match (case-sensitive, then lowercased for Latin languages)
        if clean in lang_dict:
            return lang_dict[clean]
        if clean.lower() in lang_dict:
            return lang_dict[clean.lower()]

        # 2. Match without trailing punctuation
        core = clean.rstrip(".?!।, ")
        if core in lang_dict:
            return lang_dict[core]
        if core.lower() in lang_dict:
            return lang_dict[core.lower()]

        # 3. Word-by-word lookup if every token exists
        tokens = clean.split()
        translated_tokens = []
        for t in tokens:
            token_core = t.rstrip(".?!।,")
            match = lang_dict.get(token_core) or lang_dict.get(token_core.lower())
            if match is None:
                return None
            translated_tokens.append(match)

        return " ".join(translated_tokens) if translated_tokens else None

    def _translate_via_gtx(
        self, text: str, source_lang: str, target_lang: str
    ) -> Dict[str, Any]:
        """Translate text via Google Translate GTX POST endpoint with chunking."""
        chunks = chunk_text_preserving_paragraphs(text, max_chars=1500)
        translated_parts: List[str] = []
        detected_lang: Optional[str] = None

        for item in chunks:
            if item["is_break"]:
                translated_parts.append("\n")
                continue

            resp = requests.post(
                self.GTX_URL,
                params={
                    "client": "gtx",
                    "sl": source_lang,
                    "tl": target_lang,
                    "dt": "t",
                },
                data={"q": item["text"]},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            payload = resp.json()

            if not isinstance(payload, list) or not payload or not payload[0]:
                raise ValueError("Unexpected response structure from GTX endpoint")

            chunk_text = "".join(
                seg[0] for seg in payload[0] if isinstance(seg, list) and seg and seg[0]
            )
            if not chunk_text:
                raise ValueError("Empty translation returned by GTX endpoint")

            if detected_lang is None and len(payload) > 2 and isinstance(payload[2], str):
                detected_lang = normalize_language_code(payload[2]) or payload[2]

            translated_parts.append(chunk_text)

        return {
            "text": "".join(translated_parts).strip(),
            "detected_lang": detected_lang,
        }

    def _translate_via_mymemory(
        self, text: str, source_lang: str, target_lang: str
    ) -> Dict[str, Any]:
        """Translate text via MyMemoryTranslator with explicit locale codes and <=450 char chunking."""
        from deep_translator import MyMemoryTranslator

        resolved_src = detect_language(text) if source_lang == "auto" else source_lang
        src_locale = SUPPORTED_TRANSLATION_LANGUAGES[resolved_src]["mymemory"]
        tgt_locale = SUPPORTED_TRANSLATION_LANGUAGES[target_lang]["mymemory"]

        if not src_locale or not tgt_locale:
            raise ValueError(f"MyMemory locale unavailable for {resolved_src} -> {target_lang}")

        if resolved_src == target_lang:
            return {"text": text.strip(), "detected_lang": resolved_src}

        translator = MyMemoryTranslator(source=src_locale, target=tgt_locale)
        chunks = chunk_text_preserving_paragraphs(text, max_chars=450)
        translated_parts: List[str] = []

        for item in chunks:
            if item["is_break"]:
                translated_parts.append("\n")
                continue

            res = translator.translate(item["text"])
            if not res or "MYMEMORY WARNING" in res.upper() or "QUERY LENGTH LIMIT" in res.upper():
                raise ValueError(f"MyMemory API error: {res}")
            translated_parts.append(res)

        return {
            "text": "".join(translated_parts).strip(),
            "detected_lang": resolved_src,
        }

    def _translate_via_deep_google(
        self, text: str, source_lang: str, target_lang: str
    ) -> Dict[str, Any]:
        """Translate text via deep_translator GoogleTranslator with chunking."""
        from deep_translator import GoogleTranslator

        translator = GoogleTranslator(source=source_lang, target=target_lang)
        chunks = chunk_text_preserving_paragraphs(text, max_chars=1500)
        translated_parts: List[str] = []

        for item in chunks:
            if item["is_break"]:
                translated_parts.append("\n")
                continue
            res = translator.translate(item["text"])
            if not res:
                raise ValueError("Empty response from deep_translator GoogleTranslator")
            translated_parts.append(res)

        return {
            "text": "".join(translated_parts).strip(),
            "detected_lang": detect_language(text) if source_lang == "auto" else source_lang,
        }

    def translate(
        self,
        text: str,
        lang: Optional[str] = None,
        source_lang: Optional[str] = None,
        target_lang: str = "en",
    ) -> Dict[str, Any]:
        """
        Translate text between supported languages ('auto', 'en', 'hi', 'kn', 'fr').

        Maintains backward compatibility with legacy calls like translate(text, lang='hi')
        which map to source_lang='hi', target_lang='en'.
        """
        start_time = time.perf_counter()

        raw_src = source_lang if source_lang is not None else (lang if lang is not None else "auto")
        raw_tgt = target_lang

        src = normalize_language_code(raw_src)
        tgt = normalize_language_code(raw_tgt)

        if src is None or src not in SUPPORTED_TRANSLATION_LANGUAGES:
            return {
                "result": "",
                "engine_used": "Validation Error",
                "is_fallback": False,
                "latency_ms": 0.0,
                "success": False,
                "source_lang": raw_src,
                "target_lang": raw_tgt,
                "detected_lang": None,
                "error": f"Unsupported source language: '{raw_src}'. Supported: auto, en, hi, kn, fr.",
            }

        if tgt is None or tgt == "auto" or tgt not in SUPPORTED_TRANSLATION_LANGUAGES:
            return {
                "result": "",
                "engine_used": "Validation Error",
                "is_fallback": False,
                "latency_ms": 0.0,
                "success": False,
                "source_lang": src,
                "target_lang": raw_tgt,
                "detected_lang": None,
                "error": f"Unsupported target language: '{raw_tgt}'. Supported: en, hi, kn, fr.",
            }

        if not text or not text.strip():
            return {
                "result": "",
                "engine_used": "None",
                "is_fallback": False,
                "latency_ms": 0.0,
                "success": False,
                "source_lang": src,
                "target_lang": tgt,
                "detected_lang": None,
                "error": "Input text is empty. Please enter text to translate.",
            }

        clean_text = text.strip()

        if src != "auto" and src == tgt:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "result": clean_text,
                "engine_used": "Identity (Source equals Target)",
                "is_fallback": False,
                "latency_ms": round(elapsed_ms, 2),
                "success": True,
                "source_lang": src,
                "target_lang": tgt,
                "detected_lang": src,
                "error": None,
            }

        errors: List[str] = []

        # Tier 1: Google Translate GTX POST endpoint
        try:
            gtx_res = self._translate_via_gtx(clean_text, src, tgt)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "result": gtx_res["text"],
                "engine_used": "Google Neural Translation (Online)",
                "is_fallback": False,
                "latency_ms": round(elapsed_ms, 2),
                "success": True,
                "source_lang": src,
                "target_lang": tgt,
                "detected_lang": gtx_res["detected_lang"] or (detect_language(clean_text) if src == "auto" else src),
                "error": None,
            }
        except Exception as exc:
            msg = f"Google GTX error: {exc}"
            logger.warning(msg)
            errors.append(msg)

        # Tier 2: MyMemory Neural Translation (chunked)
        try:
            mm_res = self._translate_via_mymemory(clean_text, src, tgt)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "result": mm_res["text"],
                "engine_used": "MyMemory Neural Translation (Online Fallback)",
                "is_fallback": True,
                "latency_ms": round(elapsed_ms, 2),
                "success": True,
                "source_lang": src,
                "target_lang": tgt,
                "detected_lang": mm_res["detected_lang"],
                "error": None,
            }
        except Exception as exc:
            msg = f"MyMemory error: {exc}"
            logger.warning(msg)
            errors.append(msg)

        # Tier 3: deep_translator GoogleTranslator (chunked)
        try:
            dt_res = self._translate_via_deep_google(clean_text, src, tgt)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "result": dt_res["text"],
                "engine_used": "GoogleTranslator Backup (Online Fallback)",
                "is_fallback": True,
                "latency_ms": round(elapsed_ms, 2),
                "success": True,
                "source_lang": src,
                "target_lang": tgt,
                "detected_lang": dt_res["detected_lang"],
                "error": None,
            }
        except Exception as exc:
            msg = f"GoogleTranslator error: {exc}"
            logger.warning(msg)
            errors.append(msg)

        # Tier 4: Offline Bilingual Lexicon Fallback
        resolved_src = detect_language(clean_text) if src == "auto" else src
        offline_match = self._offline_translate(clean_text, lang=resolved_src, target_lang=tgt)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        if offline_match:
            return {
                "result": offline_match,
                "engine_used": "Curated Offline Bilingual Lexicon (Offline Fallback)",
                "is_fallback": True,
                "latency_ms": round(elapsed_ms, 2),
                "success": True,
                "source_lang": src,
                "target_lang": tgt,
                "detected_lang": resolved_src,
                "error": None,
            }

        # Tier 5: Clear, structured error reporting when all translation layers fail
        return {
            "result": "",
            "engine_used": "Translation Failed (Offline / Network Unavailable)",
            "is_fallback": True,
            "latency_ms": round(elapsed_ms, 2),
            "success": False,
            "source_lang": src,
            "target_lang": tgt,
            "detected_lang": resolved_src,
            "error": (
                f"Translation failed for '{resolved_src} -> {tgt}'. "
                f"Online services were unreachable ({'; '.join(errors)}) and no offline dictionary match was found."
            ),
        }


# Global singleton instance
_translation_engine_instance: Optional[TranslationEngine] = None


def get_translation_engine() -> TranslationEngine:
    """Return cached TranslationEngine instance."""
    global _translation_engine_instance
    if _translation_engine_instance is None:
        _translation_engine_instance = TranslationEngine()
    return _translation_engine_instance


def translate_text(
    text: str,
    lang: Optional[str] = None,
    source_lang: Optional[str] = None,
    target_lang: str = "en",
) -> Dict[str, Any]:
    """Convenience functional wrapper for translation."""
    engine = get_translation_engine()
    return engine.translate(
        text, lang=lang, source_lang=source_lang, target_lang=target_lang
    )
