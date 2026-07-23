"""AutoGenius configuration.

Loads the z.ai / GLM key from the OFF-OneDrive secrets store (never committed),
with an environment-variable override so the same code runs unchanged in GitHub
Actions (where the key is injected as a repo secret named ZAI_API_KEY).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Force UTF-8 everywhere (Windows console defaults to cp1252 and mangles the
# em-dashes / Greek letters the archive is full of).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# --- paths -----------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = REPO_ROOT / "archive"
ESTABLISHED = ARCHIVE / "established"
DISPROVEN = ARCHIVE / "disproven"
OPEN = ARCHIVE / "open"
CONJECTURES = ARCHIVE / "conjectures"
METHODS = ARCHIVE / "methods"
INDEX_JSON = ARCHIVE / "index.json"
LEDGER_JSON = ARCHIVE / "ledger.json"
QUEUE_JSON = ARCHIVE / "queue.json"
LESSONS_MD = ARCHIVE / "LESSONS.md"
AXIOMS_MD = ARCHIVE / "AXIOMS.md"

for _d in (ARCHIVE, ESTABLISHED, DISPROVEN, OPEN, CONJECTURES, METHODS):
    _d.mkdir(parents=True, exist_ok=True)

# --- GLM / z.ai ------------------------------------------------------------
GLM_BASE_URL = os.environ.get("GLM_BASE_URL", "https://api.z.ai/api/paas/v4")
GLM_URL = f"{GLM_BASE_URL}/chat/completions"
# Free model. IMPORTANT: glm-4.5-flash returns EMPTY content unless the request
# carries {"thinking": {"type": "disabled"}} — see glm.py. (3x-confirmed gotcha.)
GLM_MODEL = os.environ.get("GLM_MODEL", "glm-4.5-flash")

SECRETS_ENV = Path.home() / ".claude" / "secrets" / "zai.env"


def _load_key_from_env_file(path: Path) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == "ZAI_API_KEY":
            return v.strip().strip('"').strip("'")
    return None


def get_api_key() -> str:
    """Env var wins (GitHub Actions); fall back to the local secrets file."""
    key = os.environ.get("ZAI_API_KEY") or _load_key_from_env_file(SECRETS_ENV)
    if not key:
        raise RuntimeError(
            "No ZAI_API_KEY found. Set the env var or create "
            f"{SECRETS_ENV} with a line 'ZAI_API_KEY=...'."
        )
    return key


# --- research-cycle knobs --------------------------------------------------
MAX_DERIVE_STEPS = int(os.environ.get("AG_MAX_DERIVE_STEPS", "4"))   # sandbox tool-loop cap
RSI_EVERY = int(os.environ.get("AG_RSI_EVERY", "5"))                 # reflect every N cycles
QUESTION_FAIL_CAP = int(os.environ.get("AG_QUESTION_FAIL_CAP", "3")) # quarantine after K fails
SANDBOX_TIMEOUT = int(os.environ.get("AG_SANDBOX_TIMEOUT", "25"))    # seconds per sandbox run
GH_REPO = os.environ.get("AG_GH_REPO", "lordbasilaiassistant-sudo/AutoGenius")
