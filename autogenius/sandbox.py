"""The math/sim sandbox — where the agent's math becomes real.

The scientist writes Python (sympy/numpy/scipy); this runs it in a fresh,
time-limited subprocess and hands back the *actual* stdout. That is the whole
point: a derivation is not "proven" until it has been run and seen to return
the right number. The model proposes; sympy/scipy disposes.

TRUST BOUNDARY (honest): this executes code the LLM writes, on the local
machine. A lightweight denylist blocks the obviously destructive stuff
(filesystem writes, network, process spawning), but this is NOT a security
sandbox — a determined adversary could escape it. It is safe for THIS use
(a non-adversarial research model on Anthony's own box). Hardening path for
untrusted/24-7 cloud use: run inside a container or a seccomp/nsjail wrapper.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import config

# Rich preamble prepended to every snippet: the agent's standing toolkit.
PREAMBLE = r'''# -- AutoGenius sandbox preamble --
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # print pi/theta/checkmarks safely
except Exception: pass
import math, cmath, itertools, functools, json
import numpy as np
import scipy
import sympy as sp
from sympy import *          # Function, Derivative, Sum, dsolve, all trig, S, oo, ...
# numpy/scipy stay namespaced (np., scipy.) so nothing sympy shadows them.

import sympy.physics.units as u

def _dimdict(expr):
    """Reduce a quantity-expr (u.kilogram*u.meter**2) OR a dimension-expr
    (u.energy) to a {base_dimension: power} dict — the canonical form for
    honest comparison. Avoids the trap where passing a Dimension collapses to
    dimensionless (a silent false-OK)."""
    from sympy.physics.units import Dimension
    from sympy.physics.units.systems.si import SI, dimsys_SI
    de = SI.get_dimensional_expr(expr)
    if de == 1 and expr != 1:          # expr was itself a Dimension, not a quantity
        dim = expr if isinstance(expr, Dimension) else Dimension(expr)
    else:
        dim = Dimension(de)
    return {str(getattr(k, "name", k)): int(v)
            for k, v in dimsys_SI.get_dimensional_dependencies(dim).items()}

def check_dimensions(expr, expected, subs=None):
    """Verify `expr` and `expected` share SI dimensions. Two ways to call it:
      * build from units:  check_dimensions(u.kilogram*(u.meter/u.second)**2, u.energy)
      * plain-symbol formula + a subs map giving each symbol's units:
            L, g = symbols('L g'); T = 2*pi*sqrt(L/g)
            check_dimensions(T, u.time, subs={L: u.meter, g: u.meter/u.second**2})  -> OK
    Prints a verdict line and returns bool. Never raises — a bad call prints a tip."""
    try:
        e = expr.subs(subs) if subs else expr
        got, want = _dimdict(e), _dimdict(expected)
        ok = got == want
        print(f"[dim] got={got} expected={want} -> {'OK' if ok else 'MISMATCH'}")
        return ok
    except Exception as ex:
        print(f"[dim] could not check: {ex}. Tip: build from u.* units, or pass "
              f"subs={{symbol: u.unit, ...}} so every symbol has a dimension.")
        return False

# Meet the model where it is: many attempts do `from sympy.physics.units import
# check_dimensions` or even `import sympy.physics.units.check_dimensions`.
# Register both so either import resolves instead of crashing.
u.check_dimensions = check_dimensions
import types as _types
_shim = _types.ModuleType("sympy.physics.units.check_dimensions")
_shim.check_dimensions = check_dimensions
_sys.modules["sympy.physics.units.check_dimensions"] = _shim
# -- end preamble --
'''

# Patterns that indicate escape-from-math intent. Rejected before execution.
_DENY = [
    r"\bimport\s+os\b", r"\bimport\s+shutil\b", r"\bimport\s+subprocess\b",
    r"\bimport\s+socket\b", r"\bimport\s+requests\b", r"\bimport\s+urllib\b",
    r"\b__import__\b", r"\beval\s*\(", r"\bexec\s*\(", r"\bos\.",
    r"\bopen\s*\(", r"\bPath\s*\(", r"\bsys\.exit", r"\bpickle\b",
    r"\bctypes\b", r"\bshutil\b",
]
_DENY_RE = [re.compile(p) for p in _DENY]


@dataclass
class SandboxResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int
    blocked: str | None = None

    def summary(self, limit: int = 4000) -> str:
        if self.blocked:
            return f"[SANDBOX BLOCKED] {self.blocked}"
        head = "[SANDBOX OK]" if self.ok else f"[SANDBOX ERROR rc={self.returncode}]"
        body = self.stdout if self.ok else (self.stdout + "\n--- stderr ---\n" + self.stderr)
        return f"{head}\n{body[:limit]}"


def _deny_reason(code: str) -> str | None:
    for rx in _DENY_RE:
        m = rx.search(code)
        if m:
            return f"forbidden pattern: {m.group(0)!r} (sandbox is math-only)"
    return None


def run_code(code: str, timeout: int | None = None) -> SandboxResult:
    """Run a snippet with the preamble in a fresh subprocess."""
    timeout = timeout or config.SANDBOX_TIMEOUT
    reason = _deny_reason(code)
    if reason:
        return SandboxResult(False, "", "", -1, blocked=reason)

    src = PREAMBLE + "\n" + code
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8", dir=_scratch()) as f:
        f.write(src)
        path = Path(f.name)
    try:
        env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        proc = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", env=env,
        )
        return SandboxResult(proc.returncode == 0, proc.stdout, proc.stderr,
                             proc.returncode)
    except subprocess.TimeoutExpired:
        return SandboxResult(False, "", f"timeout after {timeout}s", -9)
    finally:
        try:
            path.unlink()
        except Exception:
            pass


def _scratch() -> str:
    d = Path(tempfile.gettempdir()) / "autogenius_sandbox"
    d.mkdir(exist_ok=True)
    return str(d)
