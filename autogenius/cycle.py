"""The research cycle: CONJECTURE -> DERIVE -> FALSIFY -> ADJUDICATE.

Stages 2-5 of the plan's seven. ORIENT lives in run.py (queue picking) and
ARCHIVE/REFLECT live in archive.py / rsi.py. Each reasoning voice can drive the
sandbox in a tool-loop, so its math is computed, not hallucinated.
"""
from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field

from . import config, glm, personas, sandbox, state


def _log(msg: str) -> None:
    print(msg, flush=True)

_CODE_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)


@dataclass
class Reasoning:
    final_text: str
    runs: list[dict] = field(default_factory=list)  # [{code, output}]

    def evidence(self, limit: int = 3000) -> str:
        parts = []
        for i, r in enumerate(self.runs, 1):
            parts.append(f"[sandbox run {i}]\n{r['code']}\n--- output ---\n{r['output']}")
        blob = "\n\n".join(parts)
        return blob[:limit] if blob else "(no sandbox runs)"


def reason_with_sandbox(system: str, user: str, *, temperature: float = 0.4,
                        max_steps: int | None = None, label: str = "reason") -> Reasoning:
    """Let a voice think, run code, read real output, and iterate to a conclusion."""
    max_steps = max_steps or config.MAX_DERIVE_STEPS
    messages = [
        {"role": "system", "content": system + "\n" + personas.SANDBOX_PROTOCOL},
        {"role": "user", "content": user},
    ]
    runs: list[dict] = []
    final = ""
    for step in range(max_steps):
        t0 = time.time()
        reply = glm.raw_chat(messages, temperature=temperature, max_tokens=2200)
        messages.append({"role": "assistant", "content": reply})
        m = _CODE_RE.search(reply)
        stripped = reply.lstrip()
        if not m or stripped.upper().startswith("DONE"):
            _log(f"    [{label} step {step+1}] think {time.time()-t0:.0f}s -> DONE")
            final = reply
            break
        res = sandbox.run_code(m.group(1))
        runs.append({"code": m.group(1).strip(), "output": res.summary(2000)})
        if res.ok:
            tag = "OK"
        elif res.blocked:
            tag = f"BLOCKED: {res.blocked}"
        else:
            tag = "ERR: " + (res.stderr.strip().splitlines()[-1][:120] if res.stderr.strip() else f"rc={res.returncode}")
        _log(f"    [{label} step {step+1}] think {time.time()-t0:.0f}s + sandbox {tag}")
        nudge = ("The code ERRORED. FIX that exact error in your next block (or use a "
                 "simpler check) — do NOT resubmit the same code. " if not res.ok
                 else "Continue building on this, or reply DONE with your conclusion. ")
        messages.append({"role": "user",
                         "content": f"SANDBOX RESULT:\n{res.summary(2000)}\n\n{nudge}"})
        final = reply
    return Reasoning(final_text=final, runs=runs)


# --- Stage 2: CONJECTURE ---------------------------------------------------
def conjecture(question: str, lessons: str = "", covered: str = "") -> dict:
    avoid = ""
    if covered:
        avoid = (f"\n\nALREADY COVERED — do NOT restate, rederive, or reword any of these; "
                 f"if the question above is essentially one of them, say so in your claim:\n{covered}")
    user = f"""QUESTION FROM THE FRONTIER:
{question}

Frame ONE precise, falsifiable hypothesis you can attack with mathematics and the
sandbox. Return ONLY a JSON object:
{{
  "claim": "the precise proposition, stated as an equation or exact statement",
  "domain_of_validity": "the assumptions/regime under which it should hold",
  "falsifier": "the concrete result (a number, a counterexample, a contradiction) that would prove it FALSE",
  "falsifiable": true/false,
  "approach": "how you will derive it from first principles and check it in the sandbox"
}}{avoid}{lessons}"""
    return glm.chat_json(personas.THE_SCIENTIST, user, temperature=0.85)


def semantic_duplicate(claim: str, ledger_claims: list[str]) -> dict:
    """Catch reworded-but-identical claims that lexical matching can't see."""
    if not ledger_claims:
        return {"duplicate": False}
    listing = "\n".join(f"{i+1}. {c}" for i, c in enumerate(ledger_claims))
    user = f"""A new claim is proposed:
"{claim}"

Already-ESTABLISHED results:
{listing}

Is the new claim ESSENTIALLY THE SAME as any established one — the same physical or
mathematical content, even if worded completely differently? Return ONLY JSON:
{{"duplicate": true/false, "of": <number or null>, "why": "one line"}}"""
    try:
        return glm.chat_json(personas.THE_JUDGE, user, temperature=0.0, max_tokens=300)
    except Exception:
        return {"duplicate": False}


# --- Stage 3: DERIVE -------------------------------------------------------
def derive(claim: str, approach: str, lessons: str = "") -> Reasoning:
    user = f"""CLAIM TO DERIVE AND VERIFY:
{claim}

INTENDED APPROACH:
{approach}

Derive this from first principles. Use the sandbox to do the symbolic work and to
CHECK DIMENSIONS and numbers — do not trust a step you have not run. When finished,
reply DONE followed by: the completed derivation, and one sentence stating whether the
sandbox SUPPORTED or CONTRADICTED the claim.{lessons}"""
    return reason_with_sandbox(personas.THE_SCIENTIST, user, temperature=0.4, label="derive")


# --- Stage 4: FALSIFY ------------------------------------------------------
def falsify(claim: str, derivation: Reasoning, ledger: str, lessons: str = "") -> Reasoning:
    user = f"""A CLAIM HAS BEEN LAID ON THE ALTAR. DESTROY IT IF YOU CAN.

CLAIM:
{claim}

THE SCIENTIST'S DERIVATION:
{derivation.final_text[:2500]}

ITS SANDBOX EVIDENCE:
{derivation.evidence(2000)}

ALREADY-ESTABLISHED RESULTS (a contradiction with any of these is fatal):
{ledger}

Attack with everything: hidden assumptions, dimensional slips, boundary cases,
numerical counterexamples (hunt them in the sandbox), contradictions with the ledger.
When finished, reply DONE followed by: your sharpest attack, whether you found a FATAL
flaw or counterexample (state it explicitly), and whether the claim SURVIVES.{lessons}"""
    return reason_with_sandbox(personas.THE_SKEPTIC, user, temperature=0.5, label="falsify")


# --- Stage 5: ADJUDICATE ---------------------------------------------------
def adjudicate(question: str, claim: str, derivation: Reasoning,
               falsification: Reasoning, ledger: str) -> dict:
    user = f"""RENDER JUDGMENT.

ORIGINAL QUESTION: {question}
CLAIM: {claim}

DERIVATION (scientist):
{derivation.final_text[:2000]}
DERIVATION SANDBOX EVIDENCE:
{derivation.evidence(1800)}

FALSIFICATION (skeptic):
{falsification.final_text[:2000]}
FALSIFICATION SANDBOX EVIDENCE:
{falsification.evidence(1500)}

ESTABLISHED LEDGER:
{ledger}

Return ONLY a JSON object:
{{
  "title": "a short title for this result",
  "verdict": "PROVEN | DISPROVEN | OPEN | CONJECTURE",
  "reason": "the specific evidence that decides it (cite the sandbox result or the flaw)",
  "confidence": 0.0-1.0,
  "method": {{"name": "reusable lemma name", "statement": "the lemma"}} or null,
  "followups": [
    {{"question": "sharpest follow-up this opened", "significance": 1-5, "tractability": 1-5, "novelty": 1-5}}
  ]
}}
Remember: you may NOT return PROVEN when in doubt. Prefer OPEN or CONJECTURE."""
    return glm.chat_json(personas.THE_JUDGE, user, temperature=0.2, max_tokens=1500)


@dataclass
class CycleResult:
    question: dict
    conjecture: dict
    derivation: Reasoning
    falsification: Reasoning
    verdict: dict


def run_cycle(question: dict) -> CycleResult:
    lessons = state.lessons_for_prompt()
    ledger = state.ledger_summary()
    led_entries = state.load_ledger()
    covered = "\n".join(f"- {c}" for c in state.covered_corpus()[-30:])
    t0 = time.time()
    conj = conjecture(question["question"], lessons, covered)
    claim = conj.get("claim", question["question"])
    _log(f"  [conjecture] {time.time()-t0:.0f}s -> {claim[:80]}")

    # anti-loop layer 3: refuse to re-prove something already established
    dup = semantic_duplicate(claim, [e["claim"] for e in led_entries])
    if dup.get("duplicate"):
        return CycleResult(question, conj, Reasoning(""), Reasoning(""),
                           {"title": claim[:80], "verdict": "DUPLICATE", "confidence": 1.0,
                            "reason": f"Already established — {dup.get('why','duplicate of prior result')}.",
                            "method": None, "followups": []})

    if not conj.get("falsifiable", True):
        # An unfalsifiable conjecture never reaches the sandbox — cardinal sin.
        return CycleResult(question, conj, Reasoning(""), Reasoning(""),
                           {"title": conj.get("claim", "unfalsifiable")[:80],
                            "verdict": "CONJECTURE", "confidence": 0.0,
                            "reason": "Not falsifiable — quarantined at the frontier without spending compute.",
                            "method": None, "followups": []})
    _log("  [derive] deriving...")
    deriv = derive(claim, conj.get("approach", ""), lessons)
    _log(f"  [falsify] attacking ({len(deriv.runs)} derive runs done)...")
    falsi = falsify(claim, deriv, ledger, lessons)
    _log(f"  [adjudicate] judging ({len(falsi.runs)} falsify runs done)...")
    verdict = adjudicate(question["question"], claim, deriv, falsi, ledger)
    return CycleResult(question, conj, deriv, falsi, verdict)
