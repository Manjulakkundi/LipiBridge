"""
Transliteration Module for Hinglish Smart Writing Assistant.
Integrates AI4Bharat IndicXlit neural model with a robust phonetic fallback.
"""

import time
import re
from typing import Dict, Any, Optional

# Supported language configuration
SUPPORTED_LANGUAGES = {
    "hi": {
        "name": "Hindi",
        "native_name": "हिन्दी",
        "script": "Devanagari",
        "sanscript_code": "devanagari",
        "sample": "mera naam manjunath hai"
    },
    "kn": {
        "name": "Kannada",
        "native_name": "ಕನ್ನಡ",
        "script": "Kannada",
        "sanscript_code": "kannada",
        "sample": "namaskara"
    }
}


class TransliterationEngine:
    """
    Unified Transliteration Engine.
    Tries to load AI4Bharat IndicXlit (RNN CPU model).
    Falls back gracefully to indic-transliteration phonetic mapping if unavailable.
    """

    def __init__(self):
        self._engines: Dict[str, Any] = {}
        self._engine_status: Dict[str, Dict[str, Any]] = {}
        self._init_models()

    def _init_models(self):
        """Initialize AI4Bharat engines for supported languages."""
        for lang in SUPPORTED_LANGUAGES:
            self._engine_status[lang] = {
                "ai4bharat_available": False,
                "model_name": "None",
                "error": None
            }
            try:
                from ai4bharat.transliteration import XlitEngine
                # Initialize AI4Bharat RNN engine on CPU
                engine = XlitEngine(lang, model_type="rnn")
                self._engines[lang] = engine
                self._engine_status[lang]["ai4bharat_available"] = True
                self._engine_status[lang]["model_name"] = "AI4Bharat IndicXlit (RNN v0.5)"
            except Exception as e:
                self._engine_status[lang]["ai4bharat_available"] = False
                self._engine_status[lang]["model_name"] = "Rule-based Fallback (indic-transliteration)"
                self._engine_status[lang]["error"] = str(e)

    def get_status(self, lang: str = "hi") -> Dict[str, Any]:
        """Return the current status of the transliteration engine for a language."""
        return self._engine_status.get(lang, {
            "ai4bharat_available": False,
            "model_name": "Unknown",
            "error": "Unsupported language"
        })

    def _fallback_transliterate(self, text: str, lang: str) -> str:
        """
        Phonetic rule-based fallback using indic-transliteration.
        Guarantees that transliteration always succeeds even without model weights.
        """
        try:
            from indic_transliteration import sanscript
            from indic_transliteration.sanscript import transliterate

            target_scheme = sanscript.DEVANAGARI if lang == "hi" else sanscript.KANNADA
            # Normalize common Hinglish lowercase conventions to ITRANS-friendly mapping
            # Simple word-by-word conversion
            words = text.split()
            out_words = []
            for w in words:
                # Keep punctuation/numbers separate
                prefix = re.match(r"^[^a-zA-Z0-9]*", w).group(0)
                suffix = re.search(r"[^a-zA-Z0-9]*$", w).group(0)
                core = w[len(prefix):len(w) - len(suffix)] if (len(prefix) + len(suffix)) < len(w) else ""
                
                if core:
                    trans = transliterate(core.lower(), sanscript.ITRANS, target_scheme)
                    out_words.append(f"{prefix}{trans}{suffix}")
                else:
                    out_words.append(w)
            return " ".join(out_words)
        except Exception as e:
            # Absolute minimal fallback: return original text if library fails
            return text

    def transliterate(self, text: str, lang: str = "hi") -> Dict[str, Any]:
        """
        Transliterate input Roman/Hinglish text to the target Indic language.
        
        Args:
            text: Input Roman script string.
            lang: Target language code ('hi' or 'kn').
            
        Returns:
            Dictionary containing:
                - result: Transliterated string
                - engine_used: Description of the engine
                - is_fallback: Boolean flag
                - latency_ms: Execution time in milliseconds
                - lang: Target language code
        """
        if not text or not text.strip():
            return {
                "result": "",
                "engine_used": self._engine_status.get(lang, {}).get("model_name", "None"),
                "is_fallback": False,
                "latency_ms": 0.0,
                "lang": lang
            }

        start_time = time.perf_counter()
        clean_text = text.strip()

        # Check if AI4Bharat model is available
        if self._engine_status.get(lang, {}).get("ai4bharat_available", False) and lang in self._engines:
            try:
                engine = self._engines[lang]
                # AI4Bharat translit_sentence expects single-line or multi-line strings
                # Split by newline to preserve paragraph structure
                lines = clean_text.splitlines()
                out_lines = []
                for line in lines:
                    if not line.strip():
                        out_lines.append("")
                        continue
                    res = engine.translit_sentence(line.strip())
                    # Format of res: {'hi': 'मेरा नाम...'}
                    if isinstance(res, dict) and lang in res:
                        out_lines.append(res[lang])
                    elif isinstance(res, str):
                        out_lines.append(res)
                    else:
                        out_lines.append(str(res))

                result_text = "\n".join(out_lines)
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                return {
                    "result": result_text,
                    "engine_used": "AI4Bharat IndicXlit (Neural RNN)",
                    "is_fallback": False,
                    "latency_ms": round(elapsed_ms, 2),
                    "lang": lang
                }
            except Exception as e:
                # If AI4Bharat fails at runtime, fall back
                pass

        # Fallback path
        fallback_res = self._fallback_transliterate(clean_text, lang)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "result": fallback_res,
            "engine_used": "Rule-Based Phonetic Fallback (indic-transliteration)",
            "is_fallback": True,
            "latency_ms": round(elapsed_ms, 2),
            "lang": lang
        }


# Global singleton instance for Streamlit session efficiency
_engine_instance: Optional[TransliterationEngine] = None


def get_transliteration_engine() -> TransliterationEngine:
    """Return cached TransliterationEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = TransliterationEngine()
    return _engine_instance


def transliterate_text(text: str, lang: str = "hi") -> Dict[str, Any]:
    """Convenience functional wrapper for transliteration."""
    engine = get_transliteration_engine()
    return engine.transliterate(text, lang)
