#!/usr/bin/env bash
# Safe push for PolyVox — audit then commit + publish
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
LOG="$ROOT/_push_audit.txt"

fail() { echo "FAIL: $*" | tee -a "$LOG"; exit 1; }
ok() { echo "OK: $*" | tee -a "$LOG"; }

: > "$LOG"
echo "=== PolyVox safe push audit ===" | tee -a "$LOG"

# 1. Secrets files must not exist in index
test -f .env && fail ".env exists — must stay local only"
ok "no .env file"

grep -qxF '.env' .gitignore || fail ".env not in .gitignore"
ok ".env gitignored"

# 2. Secret patterns in tracked text (exclude png, venv)
if rg -i "sk-ant-[a-z0-9]|gsk_[a-z0-9]|ghp_[a-z0-9]" \
  --glob '!.venv/**' --glob '!*.png' --glob '!_push_audit.txt' . 2>/dev/null; then
  fail "possible API key in repo — fix before push"
fi
ok "no API key patterns"

# 2b. Real client/hospital names — keep this list updated as new clients are added.
# config.local.yaml carries real values locally and is gitignored, so it's excluded here.
if rg -il "kims|kimshealth|rainbow" \
  --glob '!.venv/**' --glob '!*.png' --glob '!_push_audit.txt' \
  --glob '!config.local.yaml' --glob '!templates/kims.yaml' . 2>/dev/null; then
  fail "possible client name in repo — genericize before push (see README Privacy note)"
fi
ok "no client name patterns"

# 3. Dry-run add — block sensitive extensions
while IFS= read -r f; do
  case "$f" in
    *.env|*/.env) fail "would commit .env: $f" ;;
    *.csv|*.xlsx|*.xls) fail "would commit data file: $f" ;;
    .venv/*|*/__pycache__/*) fail "would commit venv/cache: $f" ;;
  esac
done < <(git add -n -A 2>/dev/null | sed -n 's/^add //p')

ok "dry-run add clean"

git add -A
git status -sb | tee -a "$LOG"

if git diff --cached --quiet; then
  ok "nothing to commit (already committed?)"
else
  git commit -m "$(cat <<'EOF'
Add PolyVox: multilingual call QA pipeline with portfolio README.

Sanitized config, redacted screenshots, no client data or secrets.
EOF
)"
  ok "committed"
fi

if git remote get-url origin &>/dev/null; then
  ok "remote origin exists"
else
  if gh repo view ishanshaurya/polyvox &>/dev/null; then
    git remote add origin https://github.com/ishanshaurya/polyvox.git
  else
    gh repo create ishanshaurya/polyvox --public --source=. --remote=origin \
      --description "Multilingual call QA — telephony export to transcription, AI scoring, Excel reports"
    ok "created GitHub repo"
  fi
fi

git push -u origin main
ok "pushed"
echo ""
echo "https://github.com/ishanshaurya/polyvox"
