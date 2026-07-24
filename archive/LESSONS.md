# LESSONS — heuristics AutoGenius has taught itself

- A later sandbox run that FIXES an earlier bug supersedes it: an early buggy output is debugging history, never a counterexample against the corrected result.
- Never render a kill verdict on evidence you did not run yourself — recompute the key number in the sandbox before declaring anything DISPROVEN; quoting someone else's buggy run is not an independent rebuild.
- Beware degenerate initial conditions: an orbit that lands exactly on a fixed point (x0=0.5 -> 1 -> 0 in the r=4 logistic map) measures the fixed point, not the system — always test several initial conditions.
