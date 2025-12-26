from __future__ import annotations
import re
from collections import Counter
from typing import Dict, List

from .models import LoreText


def normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n"))


def acrostic_first_letters_by_line(lore: LoreText) -> str:
    lines = normalize_text(lore.body).split("\n")
    chars = []
    for line in lines:
        stripped = line.lstrip()
        if stripped:
            chars.append(stripped[0])
    return "".join(chars)


def acrostic_last_letters_by_line(lore: LoreText) -> str:
    lines = normalize_text(lore.body).split("\n")
    chars = []
    for line in lines:
        stripped = line.rstrip()
        if stripped:
            chars.append(stripped[-1])
    return "".join(chars)


def first_letters_of_sentences(lore: LoreText) -> str:
    text = normalize_text(lore.body)
    sentences = re.split(r"[.!?]+", text)
    chars = []
    for s in sentences:
        stripped = s.strip()
        if not stripped:
            continue
        for ch in stripped:
            if ch.isalpha():
                chars.append(ch)
                break
    return "".join(chars)


def numeric_tokens(lore: LoreText) -> List[str]:
    return re.findall(r"\d+", lore.body)


def word_frequency(lore: LoreText, min_length: int = 4) -> Dict[str, int]:
    text = lore.body.lower()
    words = re.findall(r"[a-zA-Z']+", text)
    freq = Counter(w for w in words if len(w) >= min_length)
    return dict(freq.most_common())


def nth_word_selector(lore: LoreText, indices: List[int]) -> str:
    words = re.findall(r"[A-Za-z0-9']+", lore.body)
    selected = []
    for idx in indices:
        if 1 <= idx <= len(words):
            selected.append(words[idx - 1])
    return " ".join(selected)


def report_basic_lore_analysis(lore: LoreText) -> Dict[str, str]:
    acrostic_first = acrostic_first_letters_by_line(lore)
    acrostic_last = acrostic_last_letters_by_line(lore)
    first_sent = first_letters_of_sentences(lore)
    nums = numeric_tokens(lore)
    freq = word_frequency(lore)

    top_words = list(freq.items())[:10]
    top_words_str = ", ".join(f"{w}({c})" for w, c in top_words)

    return {
        "identifier": lore.identifier,
        "title": lore.title,
        "source": lore.source,
        "acrostic_first_letters_by_line": acrostic_first,
        "acrostic_last_letters_by_line": acrostic_last,
        "first_letters_of_sentences": first_sent,
        "numeric_tokens": ", ".join(nums),
        "top_words": top_words_str,
    }
