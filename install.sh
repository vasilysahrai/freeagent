#!/usr/bin/env bash
# FreeAgent installer — macOS & Linux.
#   curl -fsSL https://raw.githubusercontent.com/vasilysahrai/freeagent/main/install.sh | bash
set -euo pipefail

REPO="vasilysahrai/freeagent"
SOURCE="git+https://github.com/${REPO}.git"

bold()   { printf '\033[1m%s\033[0m\n' "$*"; }
note()   { printf '  %s\n' "$*"; }
fail()   { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1; }

bold "Installing FreeAgent"

# ── Python ──────────────────────────────────────────────────────────────
if need python3; then
  PY=python3
elif need python; then
  PY=python
else
  fail "Python 3 is required. Install it from https://www.python.org/downloads/ or 'brew install python'."
fi
PY_VER=$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
note "python: $PY ($PY_VER)"

# ── Install path: pipx > pip --user ─────────────────────────────────────
if need pipx; then
  note "using pipx"
  pipx install --force "$SOURCE"
else
  note "pipx not found — using 'pip install --user' (consider 'brew install pipx' for cleaner installs)"
  "$PY" -m pip install --user --upgrade --quiet "$SOURCE"
fi

# ── PATH check ─────────────────────────────────────────────────────────
if ! need freeagent; then
  USER_BIN="$("$PY" -c 'import site, os; print(os.path.join(site.getuserbase(), "bin"))')"
  echo
  bold "freeagent installed but not on PATH"
  note "add this to your shell rc (~/.zshrc or ~/.bashrc):"
  echo "    export PATH=\"$USER_BIN:\$PATH\""
  exit 0
fi

echo
bold "Done."
note "next: set a key for any provider you want to use, e.g.:"
note "  export ZAI_API_KEY=...   # free GLM-4.5-flash · https://z.ai"
note "  export GROQ_API_KEY=...  # free tier         · https://console.groq.com/keys"
note "then run:"
note "  freeagent          # interactive REPL"
note "  freeagent --list-models"
