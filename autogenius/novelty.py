"""Anti-repetition guard — so the agent never loops the same idea forever.

Autonomous LLM loops love to re-ask the same question in slightly different words
("derive the pendulum period" / "find the period of a simple pendulum"). Exact-text
dedup misses that. This module fingerprints text down to a normalized keyword set and
compares by Jaccard overlap, so paraphrases collide too. Three lines of defense:

  1. enqueue-time: near-duplicate questions are dropped before they ever join the queue.
  2. conjecture-time: the scientist is shown what has already been covered and told not
     to restate it.
  3. cycle-time: if a fresh claim duplicates something already PROVEN, the cycle
     short-circuits (DUPLICATE) instead of burning compute re-proving it.
"""
from __future__ import annotations

import re

_STOP = {
    "the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "is", "are",
    "be", "that", "this", "it", "its", "from", "with", "as", "by", "at", "we",
    "does", "do", "show", "derive", "find", "prove", "using", "use", "via",
    "then", "than", "into", "out", "if", "so", "which", "what", "how", "why",
    "verify", "check", "compute", "calculate", "determine", "consider", "given",
    "let", "can", "will", "would", "should", "must", "has", "have", "not",
}


def _stem(w: str) -> str:
    for suf in ("ational", "ization", "iveness", "tion", "sion", "ing", "ies",
                "ed", "es", "s", "ly", "ical", "ic", "al"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def fingerprint(text: str) -> frozenset[str]:
    """Normalized content-keyword set. Numbers kept (4.6692 distinguishes claims)."""
    toks = re.findall(r"[a-zA-Z]+|\d+\.?\d*", text.lower())
    keep = set()
    for t in toks:
        if t.isalpha():
            if t in _STOP or len(t) <= 2:
                continue
            keep.add(_stem(t))
        else:
            keep.add(t)  # numeric literal
    return frozenset(keep)


def similarity(a: str, b: str) -> float:
    fa, fb = fingerprint(a), fingerprint(b)
    if not fa or not fb:
        return 0.0
    inter = len(fa & fb)
    union = len(fa | fb)
    return inter / union if union else 0.0


# Genuinely-different questions measure <=0.20 on this metric; obvious paraphrases
# measure ~0.55+. 0.5 sits in the clean gap. Reworded-but-different-vocabulary
# duplicates (that share no literal words) are caught by the LLM semantic check in
# cycle.py, not here — lexical matching structurally cannot see them.
DEFAULT_THRESHOLD = 0.5


def is_novel(text: str, corpus: list[str], threshold: float = DEFAULT_THRESHOLD) -> bool:
    return not any(similarity(text, c) >= threshold for c in corpus if c)


def most_similar(text: str, corpus: list[str]) -> tuple[float, str | None]:
    best, who = 0.0, None
    for c in corpus:
        s = similarity(text, c)
        if s > best:
            best, who = s, c
    return best, who


def dedupe(candidates: list[str], corpus: list[str],
           threshold: float = DEFAULT_THRESHOLD) -> list[str]:
    """Keep only candidates novel vs the corpus AND vs each other."""
    kept: list[str] = []
    seen = list(corpus)
    for c in candidates:
        if c and is_novel(c, seen, threshold):
            kept.append(c)
            seen.append(c)
    return kept
