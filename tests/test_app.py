"""
Automated unit tests for Hinglish Smart Writing Assistant.
Run using pytest: pytest tests/test_app.py -v
"""

import os
import sys
import pytest

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import patch
from transliteration import transliterate_text, get_transliteration_engine
from translation import translate_text, get_translation_engine, detect_language
from text_improver import improve_text, get_text_improver


# ============================================================================
# Transliteration Tests
# ============================================================================

def test_hindi_transliteration_basic():
    """Verify standard Hindi transliteration."""
    res = transliterate_text("mera naam manjunath hai", lang="hi")
    assert res["result"] != ""
    assert "मंजुनाथ" in res["result"] or "नाम" in res["result"]
    assert res["lang"] == "hi"


def test_kannada_transliteration_basic():
    """Verify standard Kannada transliteration."""
    res = transliterate_text("namaskara", lang="kn")
    assert res["result"] != ""
    assert "ನಮಸ್ಕಾರ" in res["result"] or "ನಮಸ್ಕ" in res["result"]
    assert res["lang"] == "kn"


def test_transliteration_empty_input():
    """Verify handling of empty or blank string."""
    res_empty = transliterate_text("", lang="hi")
    assert res_empty["result"] == ""

    res_spaces = transliterate_text("    ", lang="hi")
    assert res_spaces["result"] == ""


def test_transliteration_numbers_and_punctuation():
    """Verify numbers and basic punctuation are preserved."""
    res = transliterate_text("aaj 15 august hai!", lang="hi")
    assert "15" in res["result"]
    assert "!" in res["result"]


# ============================================================================
# Text Improvement Tests
# ============================================================================

def test_text_improvement_contractions():
    """Verify that chat abbreviations are expanded."""
    res = improve_text("plz send msg wid details")
    assert "please" in res["improved_text"].lower()
    assert "with" in res["improved_text"].lower()
    assert "message" in res["improved_text"].lower()
    assert res["has_changes"] is True


def test_text_improvement_punctuation_spacing():
    """Verify correction of improper spacing before punctuation."""
    res = improve_text("namaste , dost . kya hal hai ???")
    # Should remove spaces before comma and period
    assert " ," not in res["improved_text"]
    assert " ." not in res["improved_text"]
    assert "???" not in res["improved_text"]
    assert "?" in res["improved_text"]


def test_text_improvement_capitalization():
    """Verify first letter capitalization of sentence."""
    res = improve_text("aap kaise ho")
    assert res["improved_text"].startswith("A")
    assert res["improved_text"].endswith(".")


def test_indic_improvement_hindi_danda():
    """Verify replacement of Western period with Hindi Purna Viram."""
    res = improve_text("मेरा नाम मंजुनाथ है.", is_indic=True, lang="hi")
    assert "।" in res["improved_text"]


# ============================================================================
# Translation Tests
# ============================================================================

def test_translation_hindi_to_english():
    """Verify translation of basic Hindi sentence."""
    res = translate_text("मेरा नाम मंजुनाथ है", lang="hi")
    assert res["success"] is True
    assert "manjunath" in res["result"].lower() or "name" in res["result"].lower()


def test_translation_kannada_to_english():
    """Verify translation of basic Kannada greeting."""
    res = translate_text("ನಮಸ್ಕಾರ", lang="kn")
    assert res["success"] is True
    assert res["result"] != ""


def test_translation_empty_input():
    """Verify empty input translation."""
    res = translate_text("", lang="hi")
    assert res["result"] == ""


def test_translation_offline_fallback():
    """Verify offline dictionary fallback operates when queried directly."""
    engine = get_translation_engine()
    offline_match = engine._offline_translate("धन्यवाद", lang="hi")
    assert offline_match == "Thank you." or offline_match == "Thank you"


def test_translation_english_to_hindi():
    """Verify English -> Hindi translation."""
    res = translate_text("Good morning, how are you?", source_lang="en", target_lang="hi")
    assert res["success"] is True
    assert res["result"] != ""
    assert res["result"].lower() != "good morning, how are you?"
    assert any("\u0900" <= ch <= "\u097F" for ch in res["result"])


def test_translation_english_to_kannada():
    """Verify English -> Kannada translation."""
    res = translate_text("Good morning, how are you?", source_lang="en", target_lang="kn")
    assert res["success"] is True
    assert res["result"] != ""
    assert res["result"].lower() != "good morning, how are you?"
    assert any("\u0C80" <= ch <= "\u0CFF" for ch in res["result"])


def test_translation_english_to_french():
    """Verify English -> French translation."""
    res = translate_text("Good morning, how are you today?", source_lang="en", target_lang="fr")
    assert res["success"] is True
    assert res["result"] != ""
    assert res["result"].lower() != "good morning, how are you today?"
    assert "bonjour" in res["result"].lower() or "comment" in res["result"].lower()


def test_translation_auto_detect_french():
    """Verify automatic source-language detection from French -> English."""
    res = translate_text("Bonjour, comment allez-vous ?", source_lang="auto", target_lang="en")
    assert res["success"] is True
    assert res["detected_lang"] == "fr"
    assert "hello" in res["result"].lower() or "good" in res["result"].lower() or "how are you" in res["result"].lower()


def test_translation_long_paragraphs():
    """Verify long multi-paragraph text (>500 chars) translates and preserves newlines."""
    para = (
        "Artificial intelligence empowers students to write and translate across "
        "multiple Indian and international languages easily."
    )
    long_text = "\n\n".join([para] * 6)
    assert len(long_text) > 700
    res = translate_text(long_text, source_lang="en", target_lang="hi")
    assert res["success"] is True
    assert "\n\n" in res["result"]
    assert any("\u0900" <= ch <= "\u097F" for ch in res["result"])


def test_translation_invalid_languages():
    """Verify unsupported source/target language codes fail gracefully."""
    res_bad_src = translate_text("Hello", source_lang="zz", target_lang="en")
    assert res_bad_src["success"] is False
    assert "Unsupported source language" in res_bad_src["error"]

    res_auto_tgt = translate_text("Hello", source_lang="en", target_lang="auto")
    assert res_auto_tgt["success"] is False
    assert "Unsupported target language" in res_auto_tgt["error"]


def test_translation_network_failure_fallback():
    """Verify behavior under network outage (offline dictionary hit vs graceful failure)."""
    with patch("requests.post", side_effect=ConnectionError("Network offline")), \
         patch("deep_translator.MyMemoryTranslator.translate", side_effect=ConnectionError("Offline")), \
         patch("deep_translator.GoogleTranslator.translate", side_effect=ConnectionError("Offline")):
        hit = translate_text("Hello", source_lang="en", target_lang="fr")
        assert hit["success"] is True
        assert hit["is_fallback"] is True
        assert hit["result"] == "Bonjour"

        miss = translate_text("Quantum entanglement is non-local.", source_lang="en", target_lang="fr")
        assert miss["success"] is False
        assert miss["result"] == ""
        assert "Translation failed" in miss["error"]


def test_language_detection_heuristics():
    """Verify offline heuristic language detector across scripts and French."""
    assert detect_language("नमस्ते दोस्त") == "hi"
    assert detect_language("ನಮಸ್ಕಾರ") == "kn"
    assert detect_language("Bonjour, comment allez-vous ?") == "fr"
    assert detect_language("Good morning friend") == "en"
