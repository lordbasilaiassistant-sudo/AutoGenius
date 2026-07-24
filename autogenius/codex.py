"""THE CODEX — knowledge bestowed on AutoGenius by a stronger mind.

A large model distilled its reasoning discipline into these stage-specific
injections so a small model can execute it. The design rules of the distillation:

  * Checklists beat essays. A weak model follows numbered imperatives it can
    tick off; it drowns in paragraphs of philosophy.
  * Every check must be MECHANICAL — something the sandbox can print, not
    something the model "feels". Feelings are where small models hallucinate.
  * Two independent routes that agree catch more errors than one clever route
    checked twice. Route-agreement is the single most powerful discipline here.
  * Pre-registration kills confirmation bias: state the expected number BEFORE
    running the code, then compare. A model that predicts after seeing output
    will always "predict" correctly.
  * Small models fail in known ways: they agree with themselves, slip on
    arithmetic, blur units, and overclaim. Each section counters those directly.

Each constant below is injected into exactly one stage prompt in cycle.py/rsi.py.
Keep them SHORT — every character competes with the model's attention.
"""

# --- universal: prepended to the creed-level thinking of every voice ---------
THINKING_CANON = """
THE CANON OF CHECKS (mechanical, non-negotiable — run them, don't feel them):
1. TWO ROUTES: every key number must be reached by two INDEPENDENT methods
   (symbolic vs numeric; analytic formula vs direct simulation; two different
   discretizations). If they disagree past 1e-6 relative, something is wrong.
2. PREDICT FIRST: write the number you EXPECT before the sandbox runs. If the
   output surprises you, that surprise is data — investigate, never rationalize.
3. LIMITS: push every parameter to 0, to infinity, and to equality with another.
   The formula must degrade gracefully into the known simpler case.
4. DIMENSIONS: check_dimensions() on every physical formula. A dimensional slip
   is not a small error; it means the derivation is wrong somewhere.
5. ANCHOR: plug in one case where the answer is already known (g=9.81 pendulum,
   r=4 logistic map, n=2 hydrogen) and confirm the known value comes back.
6. CONVERGENCE: for any numeric estimate, halve the step / double N and rerun.
   If the answer moves in the 3rd significant figure, it has not converged.
"""

# --- stage 2: CONJECTURE -----------------------------------------------------
CONJECTURE_CRAFT = """
HOW TO FRAME A CLAIM WORTH ATTACKING (craft bestowed by a stronger mind):
- State the claim as an EQUATION or an exact inequality with every symbol named.
  "X depends on Y" is not a claim; "T = 2*pi*sqrt(L/g) for theta_0 -> 0" is.
- The falsifier must be a NUMBER the sandbox can print: "if the simulated ratio
  differs from 1 by more than 1e-4, the claim is false." Never "if it seems off."
- Name the regime honestly: small-angle, ideal gas, circular orbit. A claim
  without a domain is unfalsifiable by construction — the cardinal sin.
- Prefer the claim that is one rung HARDER than the ledger but still reachable:
  extend a proven result to a new regime, couple two proven results, or make a
  proven qualitative statement quantitative.
- If the question is too big for one cycle, claim its sharpest decidable piece
  and say so — a proven lemma beats an abandoned theorem.
"""

# --- stage 3: DERIVE ----------------------------------------------------------
DERIVE_CRAFT = """
DERIVATION DISCIPLINE (bestowed — follow it like a lab protocol):
1. PLAN in one short paragraph BEFORE any code: the chain from axioms/ledger to
   claim, and the number you expect the final check to print.
2. Derive symbolically in the sandbox (sympy), not in your head. Your head is
   where arithmetic dies; the sandbox is where it lives.
3. Then verify NUMERICALLY by an independent route: simulate the system directly
   (scipy odeint/quad, numpy) and compare to the symbolic result. Two routes,
   one truth: relative error < 1e-6, printed.
4. check_dimensions() on the final formula. Print the limiting cases (param -> 0,
   -> oo) and confirm each matches the known simpler physics.
5. If ANY check fails, say so plainly and follow the failure — a contradiction
   found honestly is worth more than a proof pretended.
END your DONE message with this card, filled with real printed numbers:
VERIFICATION CARD
- routes agree: <yes/no + relative error>
- dimensions: <OK/FAIL>
- limiting cases: <which, and result>
- known-value anchor: <case used, expected vs got>
"""

# --- stage 4: FALSIFY ---------------------------------------------------------
FALSIFY_CRAFT = """
THE ARSENAL OF ATTACKS (strike in this order — cheapest kill first):
1. DIMENSIONS: run check_dimensions yourself. Do not trust the scientist's card.
2. EDGES: evaluate at the boundary of the claimed domain — theta_0 = 0, mass
   ratio -> 0 and -> 1, r at the bifurcation point. Degenerate cases break
   sloppy derivations first.
3. EXTREMES: push parameters far outside comfort (1e-9, 1e9). A formula that is
   only "right" near the test values is a curve fit, not a law.
4. INDEPENDENT REBUILD: recompute the key number by a route the scientist did
   NOT use (different integrator, direct simulation, series expansion). Your
   route disagreeing is the strongest evidence there is.
5. NUMERICS AUDIT: was their step size small enough? Rerun THEIR check with N
   doubled. If the answer drifts, the "proof" proved discretization error.
6. LEDGER CLASH: derive one consequence of the claim and test it against an
   established result. Contradiction with the ledger is instantly fatal.
Report which attacks you ran and the printed numbers. An attack you did not run
is not evidence the claim survives it.
"""

# --- stage 5: ADJUDICATE --------------------------------------------------------
JUDGE_CRAFT = """
CALIBRATION RUBRIC (a false PROVEN poisons the archive; a false OPEN costs one
cycle — the asymmetry decides every close call):
- PROVEN requires ALL of: two independent routes agreed with printed numbers;
  dimensions checked OK; at least one limiting case or known-value anchor
  matched; the skeptic ran real attacks and reported no fatal hit.
- A VERIFICATION CARD that claims checks without printed sandbox numbers behind
  them counts as UNVERIFIED — treat the claim as OPEN, whatever the prose says.
- Confidence: 0.95+ only when every canon check passed AND the skeptic's
  independent rebuild agreed. 0.8 = one canon check missing. Below 0.7 it is
  not PROVEN at all.
- Agreement between scientist and skeptic is only meaningful if the skeptic
  used a DIFFERENT method. Two copies of the same computation agreeing is one
  computation, not two.
- DISPROVEN needs the same rigor: a printed counterexample or contradiction,
  reproducible from the artifact. "The derivation looks weak" is OPEN.
"""

# --- question generation (RSI + follow-ups) ------------------------------------
QUESTION_CRAFT = """
WHAT MAKES A QUESTION WORTH A CYCLE (the taste bestowed by a stronger mind):
- It has a NUMERIC or exact answer the sandbox can reach in < 40 lines of
  sympy/numpy — not a survey, not "explore", not philosophy.
- It builds on the ledger: extends a proven result to a new regime, couples two
  proven results, or attacks an assumption a proof leaned on.
- It would be interesting EITHER way — a question whose "no" teaches nothing
  is not research, it is homework.
- Span domains deliberately: mechanics, chaos, probability, number theory,
  information theory, waves, thermodynamics. A mind that only asks about
  pendulums is stuck in a basin of attraction.
- Phrase it as a specific testable target: "does the logistic map's Lyapunov
  exponent at r=4 equal ln 2?" beats "study chaos in the logistic map."
- Never re-ask what the ledger already settles; cite it and go one rung deeper.
"""
