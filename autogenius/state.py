"""Persistent state: the question queue, the ledger of proven truth, the index,
and the self-written lessons. All plain JSON/markdown in the public archive, so
the agent's whole mind is auditable by anyone."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import config


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def slug(text: str, n: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:n] or "untitled"


def _load(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


# --- queue -----------------------------------------------------------------
def load_queue() -> list[dict]:
    return _load(config.QUEUE_JSON, [])


def save_queue(q: list[dict]) -> None:
    _save(config.QUEUE_JSON, q)


def _score(item: dict) -> float:
    s = float(item.get("significance", 3))
    t = float(item.get("tractability", 3))
    nov = float(item.get("novelty", 3))
    # penalise questions that keep failing so we don't grind a dead end forever
    penalty = 1.0 / (1.0 + item.get("attempts", 0))
    return s * t * nov * penalty


def pick_next(q: list[dict]) -> dict | None:
    """Highest significance*tractability*novelty among open questions."""
    live = [x for x in q if x.get("status", "open") == "open"]
    if not live:
        return None
    return max(live, key=_score)


def covered_corpus(q: list[dict] | None = None) -> list[str]:
    """Everything the agent has already asked or concluded — the anti-loop memory."""
    from . import novelty  # local import to keep novelty dependency-free
    q = q if q is not None else load_queue()
    corpus = [x.get("question", "") for x in q]
    corpus += [e.get("title", "") for e in load_index()]
    corpus += [e.get("claim", "") for e in load_ledger()]
    return [c for c in corpus if c]


def add_questions(q: list[dict], questions: list[dict], parent: str | None = None) -> list[dict]:
    from . import novelty
    # corpus = existing queue + all past artifact titles + ledger claims
    corpus = covered_corpus(q)
    for item in questions:
        text = (item.get("question") or "").strip()
        # paraphrase-aware: drop if too similar to anything already covered
        if not text or not novelty.is_novel(text, corpus):
            continue
        corpus.append(text)  # so a batch can't smuggle in near-dups of itself
        q.append({
            "id": gen_id("q"),
            "question": text,
            "significance": item.get("significance", 3),
            "tractability": item.get("tractability", 3),
            "novelty": item.get("novelty", 3),
            "attempts": 0,
            "status": "open",
            "parent": parent,
            "added": now_iso(),
        })
    return q


# --- ledger (established truth) --------------------------------------------
def load_ledger() -> list[dict]:
    return _load(config.LEDGER_JSON, [])


def add_to_ledger(entry: dict) -> None:
    led = load_ledger()
    led.append(entry)
    _save(config.LEDGER_JSON, led)


def ledger_summary(limit: int = 40) -> str:
    led = load_ledger()
    if not led:
        return "(the ledger is empty — no results have been proven yet)"
    lines = [f"- [{e['id']}] {e['claim']}" for e in led[-limit:]]
    return "\n".join(lines)


# --- index (all artifacts) -------------------------------------------------
def load_index() -> list[dict]:
    return _load(config.INDEX_JSON, [])


def add_index_entry(entry: dict) -> None:
    idx = load_index()
    idx.append(entry)
    _save(config.INDEX_JSON, idx)


# --- lessons (the RSI prompt layer) ----------------------------------------
def load_lessons() -> str:
    if not config.LESSONS_MD.exists():
        return ""
    return config.LESSONS_MD.read_text(encoding="utf-8")


def append_lesson(text: str) -> None:
    header = "" if config.LESSONS_MD.exists() else \
        "# LESSONS — heuristics AutoGenius has taught itself\n\n"
    with config.LESSONS_MD.open("a", encoding="utf-8") as f:
        if header:
            f.write(header)
        f.write(f"- {text.strip()}\n")


def lessons_for_prompt(limit_chars: int = 1500) -> str:
    txt = load_lessons()
    if not txt:
        return ""
    body = txt.split("\n\n", 1)[-1][-limit_chars:]
    return f"\nHARD-WON LESSONS (obey these — you wrote them):\n{body}\n"
