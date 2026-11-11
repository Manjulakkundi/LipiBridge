"""
Text Improver Module for Hinglish Smart Writing Assistant.
Provides sentence improvement:
- Normalizes informal SMS/chat contractions without altering original semantics.
- Cleans and fixes irregular punctuation spacing.
- Ensures sentence capitalization and proper terminal punctuation.
- Enhances Indic script post-transliteration (e.g., Hindi Purna Viram '।').
"""

import re
from typing import Dict, Any, List, Tuple, Optional


# Standard Hinglish / chat slang contraction mapping
CONTRACTIONS_MAP = {
    r"\bplz\b": "please",
    r"\bpls\b": "please",
    r"\bu\b": "you",
    r"\bur\b": "your",
    r"\br\b": "are",
    r"\bhv\b": "have",
    r"\bbcoz\b": "because",
    r"\bbcz\b": "because",
    r"\bcoz\b": "because",
    r"\bwid\b": "with",
    r"\bw/o\b": "without",
    r"\btnx\b": "thanks",
    r"\bthx\b": "thanks",
    r"\btq\b": "thanks",
    r"\bty\b": "thank you",
    r"\babt\b": "about",
    r"\bwat\b": "what",
    r"\bbfore\b": "before",
    r"\bmsg\b": "message",
    r"\btxt\b": "text",
    r"\bgud\b": "good",
    r"\bnite\b": "night",
    r"\bmrn\b": "morning",
    r"\bmorng\b": "morning",
    r"\bkya hal h\b": "kya haal hai",
    r"\bkaise ho h\b": "kaise ho"
}


class TextImprover:
    """
    Intelligent sentence improvement engine.
    Improves clarity and structure of Roman Hinglish and Indic script sentences.
    """

    def improve_hinglish(self, text: str) -> Dict[str, Any]:
        """
        Improve Roman Hinglish text before transliteration.
        Fixes abbreviations, spacing, punctuation, and capitalization.
        """
        if not text or not text.strip():
            return {
                "improved_text": "",
                "changes_applied": [],
                "has_changes": False
            }

        original = text
        current = original
        changes: List[str] = []

        # 1. Expand chat contractions
        for pattern, replacement in CONTRACTIONS_MAP.items():
            if re.search(pattern, current, flags=re.IGNORECASE):
                current = re.sub(pattern, replacement, current, flags=re.IGNORECASE)
                changes.append(f"Expanded abbreviation matching '{pattern}' to '{replacement}'")

        # 2. Normalize repeated punctuation (e.g. '???', '!!!')
        if re.search(r"\?{2,}", current):
            current = re.sub(r"\?{2,}", "?", current)
            changes.append("Normalized repeated question marks to single '?'")

        if re.search(r"!{2,}", current):
            current = re.sub(r"!{2,}", "!", current)
            changes.append("Normalized repeated exclamation marks to single '!'")

        if re.search(r"\.{2,}", current):
            current = re.sub(r"\.{2,}", ".", current)
            changes.append("Normalized multiple periods to single '.'")

        # 3. Fix spacing before and after punctuation marks
        # Remove space before comma, period, question mark, exclamation
        if re.search(r"\s+([,\.?!;:])", current):
            current = re.sub(r"\s+([,\.?!;:])", r"\1", current)
            changes.append("Removed irregular whitespace before punctuation")

        # Ensure single space after punctuation if followed by a word character
        if re.search(r"([,\.?!;:])([A-Za-z0-9])", current):
            current = re.sub(r"([,\.?!;:])([A-Za-z0-9])", r"\1 \2", current)
            changes.append("Added proper spacing after punctuation")

        # 4. Collapse consecutive whitespace
        if re.search(r"[ \t]{2,}", current):
            current = re.sub(r"[ \t]{2,}", " ", current)
            changes.append("Collapsed redundant whitespace")

        # 5. Capitalize first letter of sentences
        def capitalize_match(match):
            return match.group(1) + match.group(2).upper()

        new_val = re.sub(r"(^|[.?!]\s+)([a-z])", capitalize_match, current)
        if new_val != current:
            current = new_val
            changes.append("Capitalized sentence beginning")

        # 6. Ensure terminal punctuation if none exists
        stripped = current.strip()
        if stripped and stripped[-1] not in ".?!।":
            current = stripped + "."
            changes.append("Added terminal period for sentence completeness")

        return {
            "improved_text": current.strip(),
            "changes_applied": changes,
            "has_changes": current.strip() != original.strip()
        }

    def improve_indic(self, text: str, lang: str = "hi") -> Dict[str, Any]:
        """
        Polish Indic script output post-transliteration.
        - Replaces English periods with Hindi Purna Viram '।' where appropriate.
        - Cleans up spaces around Indic punctuation.
        """
        if not text or not text.strip():
            return {
                "improved_text": "",
                "changes_applied": [],
                "has_changes": False
            }

        original = text
        current = original
        changes: List[str] = []

        # 1. Spacing around Indic punctuation
        if re.search(r"\s+([।,\.?!])", current):
            current = re.sub(r"\s+([।,\.?!])", r"\1", current)
            changes.append("Removed whitespace before punctuation")

        # 2. Hindi Purna Viram (replace '.' with '।')
        if lang == "hi":
            if "." in current:
                current = current.replace(".", "।")
                changes.append("Standardized Western period '.' to Devanagari Purna Viram '।'")

        # 3. Collapse multiple spaces
        if re.search(r"[ \t]{2,}", current):
            current = re.sub(r"[ \t]{2,}", " ", current)
            changes.append("Collapsed redundant whitespace")

        return {
            "improved_text": current.strip(),
            "changes_applied": changes,
            "has_changes": current.strip() != original.strip()
        }


# Global instance
_improver_instance: Optional[TextImprover] = None


def get_text_improver() -> TextImprover:
    """Return singleton TextImprover instance."""
    global _improver_instance
    if _improver_instance is None:
        _improver_instance = TextImprover()
    return _improver_instance


def improve_text(text: str, is_indic: bool = False, lang: str = "hi") -> Dict[str, Any]:
    """Functional wrapper for text improvement."""
    improver = get_text_improver()
    if is_indic:
        return improver.improve_indic(text, lang)
    return improver.improve_hinglish(text)
