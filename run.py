"""AutoGenius main loop.

ORIENT (pick the next frontier question) -> run the cycle -> ARCHIVE -> commit,
with a REFLECT/RSI meta-cycle every N iterations. His PC is not 24/7, so the
truly-autonomous cadence lives in GitHub Actions cron (see .github/workflows);
this script is the unit of work that runs one or many cycles.

Usage:
  py run.py --once              # a single research cycle (used by the CI gate)
  py run.py --cycles 5          # five cycles + RSI where due
  py run.py --forever           # never stop (local only)
  py run.py --no-push           # don't git push (local dev)
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback

from autogenius import archive, config, rsi, state


def seed_topup(min_open: int = 3) -> None:
    """Keep the frontier alive: whenever open questions run low, offer the seed
    curriculum again. The novelty guard drops everything already asked or
    settled, so only genuinely uncovered seeds enter."""
    q = state.load_queue()
    n_open = sum(1 for x in q if x.get("status", "open") == "open")
    if n_open >= min_open:
        return
    seed_path = config.REPO_ROOT / "seed_questions.json"
    seeds = json.loads(seed_path.read_text(encoding="utf-8")) if seed_path.exists() else []
    before = len(q)
    q = state.add_questions(q, seeds, parent="seed")
    state.save_queue(q)
    if len(q) > before:
        print(f"[orient] seeded {len(q) - before} frontier questions ({n_open} were open)")


def one_cycle(push: bool) -> bool:
    from autogenius import cycle  # lazy: avoids import cost when just seeding
    q = state.load_queue()
    question = state.pick_next(q)
    if question is None:
        print("[orient] no open questions — the frontier is momentarily quiet")
        return False
    print(f"\n{'='*70}\n[orient] pursuing: {question['question']}\n{'='*70}")
    try:
        res = cycle.run_cycle(question)
    except Exception as e:
        print(f"[cycle] ERROR: {e}")
        traceback.print_exc()
        # bump attempts so a poison question eventually quarantines itself
        for item in q:
            if item["id"] == question["id"]:
                item["attempts"] = item.get("attempts", 0) + 1
                if item["attempts"] >= config.QUESTION_FAIL_CAP:
                    item["status"] = "quarantined"
        state.save_queue(q)
        return False
    v = res.verdict
    print(f"[judge] {v.get('verdict')} (conf {v.get('confidence')}) — {v.get('title','')}")
    if v.get("verdict") == "DUPLICATE":
        # anti-loop: close the question, write no artifact, spend no more compute
        for item in q:
            if item["id"] == question["id"]:
                item["status"] = "closed"
                item["note"] = v.get("reason", "duplicate")
                break
        state.save_queue(q)
        print(f"[anti-loop] {v.get('reason','duplicate — skipped')}")
        return True
    path = archive.archive_result(res)
    print(f"[archive] {path.relative_to(config.REPO_ROOT)}")
    msg = f"{v.get('verdict','?')}: {v.get('title', question['question'])[:60]}"
    print(f"[git] {archive.commit_and_push(msg, push=push)}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--cycles", type=int, default=1)
    ap.add_argument("--forever", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    push = not args.no_push
    n = 0
    target = float("inf") if args.forever else (1 if args.once else args.cycles)
    while n < target:
        seed_topup()
        did = one_cycle(push)
        n += 1
        if not did and not args.forever:
            break
        if n % config.RSI_EVERY == 0:
            print("\n[rsi] reflecting on recent work...")
            r = rsi.reflect()
            print(f"[rsi] lesson: {r['lesson']}  (+{r['new_questions']} new questions)")
            archive.commit_and_push("rsi: refined heuristics + new frontier questions",
                                    push=push)
    print(f"\n[done] ran {n} cycle(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
