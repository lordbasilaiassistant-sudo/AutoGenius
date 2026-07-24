"""REFLECT / RSI — the honest form of recursive self-improvement.

glm-4.5-flash's weights are frozen; capability instead compounds in the scaffold:
the citable verified corpus, the growing methods library, self-refined prompt
heuristics (LESSONS), and expanding sandbox tooling. Every N cycles the agent
reviews its own recent work and sharpens the instrument.
"""
from __future__ import annotations

from . import codex, glm, personas, state


def reflect() -> dict:
    """Read recent results, distil a lesson, and spawn fresh frontier questions."""
    idx = state.load_index()
    recent = idx[-8:]
    if not recent:
        return {"lesson": None, "new_questions": 0}
    digest = "\n".join(
        f"- [{e['verdict']}] {e['title']} (conf {e.get('confidence',0)}) — {e.get('question','')[:80]}"
        for e in recent
    )
    ledger = state.ledger_summary()
    user = f"""You are reviewing your own recent research to become a better scientist.

YOUR LAST RESULTS:
{digest}

WHAT YOU HAVE PROVEN SO FAR:
{ledger}

Return ONLY JSON:
{{
  "lesson": "ONE sharp, general heuristic that would have made this work better next time (about method, rigor, or where you waste effort). One sentence.",
  "new_questions": [
    {{"question": "a deeper frontier question your proven results now make tractable", "significance": 1-5, "tractability": 1-5, "novelty": 1-5}}
  ]
}}
Give 2-4 new questions. When crafting them, apply:
{codex.QUESTION_CRAFT}"""
    out = glm.chat_json(personas.THE_SCIENTIST, user, temperature=0.7, max_tokens=1200)
    lesson = (out.get("lesson") or "").strip()
    if lesson:
        state.append_lesson(lesson)
    newqs = out.get("new_questions") or []
    if newqs:
        q = state.load_queue()
        q = state.add_questions(q, newqs, parent="rsi")
        state.save_queue(q)
    return {"lesson": lesson or None, "new_questions": len(newqs)}
