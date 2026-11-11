"""
Evaluation and Benchmark Script for Hinglish Smart Writing Assistant.
Executes 35 representative test cases from data/test_cases.json.
Calculates Character Error Rate (CER), Levenshtein Distance, and Character Accuracy.
Generates a detailed evaluation summary and writes evaluation_summary.json.
"""

import os
import sys
import json
import time
from typing import Dict, Any, List

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from transliteration import transliterate_text
from text_improver import improve_text
from translation import translate_text


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def compute_cer(reference: str, hypothesis: str) -> float:
    """Compute Character Error Rate (CER) between reference and hypothesis."""
    ref = reference.strip()
    hyp = hypothesis.strip()
    
    if not ref and not hyp:
        return 0.0
    if not ref:
        return 1.0
        
    dist = levenshtein_distance(ref, hyp)
    return min(1.0, dist / max(len(ref), 1))


def run_evaluation(test_cases_path: str = "data/test_cases.json") -> Dict[str, Any]:
    """Execute the full benchmark test suite and return detailed statistics."""
    if not os.path.exists(test_cases_path):
        raise FileNotFoundError(f"Test cases file not found at: {test_cases_path}")

    with open(test_cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"\n========================================================")
    print(f" HINGLISH SMART WRITING ASSISTANT - MODEL EVALUATION ")
    print(f"========================================================")
    print(f"Loaded {len(cases)} test cases from {test_cases_path}\n")

    results: List[Dict[str, Any]] = []
    total_cer = 0.0
    total_accuracy = 0.0
    passed_count = 0
    failed_count = 0

    hi_cases = 0
    hi_accuracy = 0.0
    kn_cases = 0
    kn_accuracy = 0.0

    start_all = time.perf_counter()

    for tc in cases:
        tc_id = tc["id"]
        category = tc["category"]
        lang = tc["lang"]
        inp = tc["input"]
        expected_xlit = tc.get("expected_transliteration", "")
        expected_trans = tc.get("expected_translation", "")

        # 1. Text Improvement step (for Hinglish)
        improved_inp = improve_text(inp)["improved_text"] if inp.strip() else inp

        # 2. Transliteration step
        xlit_res = transliterate_text(inp, lang=lang)
        actual_xlit = xlit_res["result"]

        # 3. CER calculation
        cer = compute_cer(expected_xlit, actual_xlit)
        accuracy = max(0.0, 1.0 - cer) * 100.0

        # Pass criteria:
        # Exact match or CER <= 0.35 (accounting for valid phonetic spelling variations in Indic script)
        # Empty inputs pass if both are empty
        is_pass = (cer <= 0.35) or (expected_xlit.strip() == actual_xlit.strip())

        if is_pass:
            passed_count += 1
        else:
            failed_count += 1

        total_cer += cer
        total_accuracy += accuracy

        if lang == "hi":
            hi_cases += 1
            hi_accuracy += accuracy
        elif lang == "kn":
            kn_cases += 1
            kn_accuracy += accuracy

        status_str = "PASS" if is_pass else "FAIL"
        print(f"[{tc_id:02d}] [{status_str}] {category[:30]:<30} | CER: {cer:.2f} | Acc: {accuracy:5.1f}%")
        print(f"     In : {inp}")
        print(f"     Exp: {expected_xlit}")
        print(f"     Act: {actual_xlit}")

        results.append({
            "id": tc_id,
            "category": category,
            "lang": lang,
            "input": inp,
            "expected_transliteration": expected_xlit,
            "actual_transliteration": actual_xlit,
            "cer": round(cer, 4),
            "character_accuracy": round(accuracy, 2),
            "engine_used": xlit_res["engine_used"],
            "is_fallback": xlit_res["is_fallback"],
            "latency_ms": xlit_res["latency_ms"],
            "status": status_str
        })

    total_time = time.perf_counter() - start_all
    avg_cer = total_cer / len(cases)
    avg_accuracy = total_accuracy / len(cases)
    avg_hi_accuracy = (hi_accuracy / hi_cases) if hi_cases else 0.0
    avg_kn_accuracy = (kn_accuracy / kn_cases) if kn_cases else 0.0

    summary = {
        "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_test_cases": len(cases),
        "passed_cases": passed_count,
        "failed_cases": failed_count,
        "pass_rate_percentage": round((passed_count / len(cases)) * 100.0, 2),
        "average_character_accuracy": round(avg_accuracy, 2),
        "average_cer": round(avg_cer, 4),
        "hindi_accuracy": round(avg_hi_accuracy, 2),
        "kannada_accuracy": round(avg_kn_accuracy, 2),
        "total_evaluation_time_seconds": round(total_time, 2),
        "known_limitations": [
            "Colloquial English loanwords (e.g., 'technology') may be transliterated phonetically into Indic characters rather than translated.",
            "Romanized Hinglish has no standardized orthography (e.g., 'main' vs 'mein' vs 'me' for 'मैं').",
            "Kannada retroflex consonants ('t' vs 'T', 'd' vs 'D') can produce minor vowel length differences depending on input Roman spelling.",
            "Pure symbols and ASCII noise are filtered or preserved as-is without semantic transformation."
        ],
        "detailed_results": results
    }

    # Save summary
    output_summary_path = os.path.join(os.path.dirname(test_cases_path), "evaluation_summary.json")
    with open(output_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n========================================================")
    print(f" EVALUATION SUMMARY ")
    print(f"========================================================")
    print(f" Total Cases       : {summary['total_test_cases']}")
    print(f" Passed Cases      : {summary['passed_cases']}")
    print(f" Failed Cases      : {summary['failed_cases']}")
    print(f" Pass Rate         : {summary['pass_rate_percentage']}%")
    print(f" Character Accuracy: {summary['average_character_accuracy']}%")
    print(f" Average CER       : {summary['average_cer']}")
    print(f" Hindi Accuracy    : {summary['hindi_accuracy']}%")
    print(f" Kannada Accuracy  : {summary['kannada_accuracy']}%")
    print(f" Total Time        : {summary['total_evaluation_time_seconds']}s")
    print(f" Saved full summary: {output_summary_path}")
    print(f"========================================================\n")

    return summary


if __name__ == "__main__":
    run_evaluation()
