#!/usr/bin/env bash
#
# WarpFlow Frontend Test Script
# ==============================
# Runs type-check, lint, and build in sequence.
#
# Usage:   ./tests/test_frontend.sh
# Or:      bash tests/test_frontend.sh
#

set -e
cd "$(dirname "$0")/.."

GREEN='\033[92m'
RED='\033[91m'
CYAN='\033[96m'
BOLD='\033[1m'
RESET='\033[0m'

pass=0
fail=0

section() { printf "\n${BOLD}${CYAN}══════════════════════════════════════════════════${RESET}\n  ${BOLD}%s${RESET}\n${CYAN}══════════════════════════════════════════════════${RESET}\n" "$1"; }
ok()      { printf "  ${GREEN}✓${RESET} %s\n" "$1"; ((pass++)); }
err()     { printf "  ${RED}✗${RESET} %s\n" "$1"; ((fail++)); }

# ── 1. Dependencies ──
section "Dependencies"
if [ -d node_modules ]; then
    ok "node_modules exists"
else
    printf "  Installing dependencies...\n"
    npm install --silent && ok "npm install" || err "npm install failed"
fi

# ── 2. TypeScript ──
section "TypeScript Type Check"
if npx tsc --noEmit 2>&1; then
    ok "tsc --noEmit passed (zero type errors)"
else
    err "Type errors found"
fi

# ── 3. ESLint ──
section "ESLint"
if npx eslint . --max-warnings 0 2>&1; then
    ok "ESLint passed (zero warnings)"
else
    err "Lint issues found"
fi

# ── 4. Build ──
section "Vite Build"
if npx vite build 2>&1; then
    ok "Production build succeeded"
else
    err "Build failed"
fi

# ── 5. Component Checks ──
section "Component Verification"
configs=(
    "src/components/nodes/GoogleDocsConfig.tsx"
    "src/components/nodes/GoogleDriveConfig.tsx"
    "src/components/nodes/GmailConfig.tsx"
    "src/components/nodes/GoogleSheetsConfig.tsx"
    "src/components/nodes/GoogleFormsConfig.tsx"
    "src/components/nodes/OpenAIConfig.tsx"
    "src/components/nodes/GeminiConfig.tsx"
    "src/components/NodeConfigModal.tsx"
)
for f in "${configs[@]}"; do
    if [ -f "$f" ]; then
        ok "$f exists"
    else
        err "$f missing!"
    fi
done

# Verify NodeConfigModal imports all config components
modal="src/components/NodeConfigModal.tsx"
for name in GoogleDocsConfig GoogleDriveConfig GmailConfig GoogleSheetsConfig GoogleFormsConfig OpenAIConfig GeminiConfig; do
    if grep -q "$name" "$modal"; then
        ok "NodeConfigModal imports $name"
    else
        err "NodeConfigModal missing import: $name"
    fi
done

# ── Summary ──
section "Summary"
total=$((pass + fail))
printf "  ${GREEN}Passed: %d${RESET}\n" "$pass"
printf "  ${RED}Failed: %d${RESET}\n" "$fail"
printf "  Total:  %d\n" "$total"

if [ "$fail" -eq 0 ]; then
    printf "\n  ${GREEN}${BOLD}All checks passed! ✓${RESET}\n"
else
    printf "\n  ${RED}Some checks failed.${RESET}\n"
    exit 1
fi
