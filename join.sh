#!/bin/sh
# Join the SDS brain on this machine (Linux, macOS, WSL), from a clone of the team repository:
#     git clone <team repository url> sds-brain && sh sds-brain/join.sh      [--no-sudo]
#     sh join.sh --leave        take the brain off this machine again (the clone and its knowledge stay)
# Safe to run again: it is also how a moved clone or a broken install is repaired.
#  1. links this clone as ~/.claude/sds-brain: the brain's home (rules/, knowledge/, docs/, connections/);
#  2. adds this folder as a Claude Code marketplace and installs the plugin brain-sds from it (skills, hooks, MCP);
#  3. adds one import line to ~/.claude/CLAUDE.md, so every session loads the team's rules (rules/main.md);
#  4. docs: with a VM docs service (docs-http in the plugin, written by vm-setup.py) trusts the VM's certificate and
#     checks that it answers; without one, builds the local index from docs/ (a few seconds).
# Nothing else on the machine is changed. Keep the clone where it is afterwards (or run join.sh again after moving it).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd -P)
PLUG=brain-sds
CFG=${CLAUDE_CONFIG_DIR:-$HOME/.claude}
LINK=$CFG/sds-brain
MD=$CFG/CLAUDE.md
IMPORT="@$LINK/rules/main.md"; [ "$CFG" = "$HOME/.claude" ] && IMPORT='@~/.claude/sds-brain/rules/main.md'
NOSUDO=0; LEAVE=0
for a in "$@"; do case "$a" in --no-sudo) NOSUDO=1 ;; --leave) LEAVE=1 ;; *) echo "join: unknown option $a"; exit 2 ;; esac; done
FAILED=0
ok() { printf '  ok    %s\n' "$*"; }
bad() { printf '  FAIL  %s\n' "$*"; FAILED=1; }
note() { printf '  note  %s\n' "$*"; }
command -v claude >/dev/null 2>&1 || { echo "join: Claude Code (claude) is not installed or not on PATH"; exit 1; }

if [ "$LEAVE" = 1 ]; then
  claude plugin uninstall "$PLUG@$PLUG" >/dev/null 2>&1 || true
  claude plugin marketplace remove "$PLUG" >/dev/null 2>&1 || true
  if [ -f "$MD" ] && grep -qxF "$IMPORT" "$MD"; then
    grep -vxF "$IMPORT" "$MD" > "$MD.sds-tmp" || true
    cat "$MD.sds-tmp" > "$MD"; rm -f "$MD.sds-tmp"
  fi
  [ -L "$LINK" ] && rm -f "$LINK"
  echo "left: the plugin, the import line in $MD and the link $LINK are gone; $HERE is untouched"
  exit 0
fi

[ -f "$HERE/$PLUG/.claude-plugin/plugin.json" ] && [ -d "$HERE/knowledge" ] && [ -f "$HERE/rules/main.md" ] ||
  { echo "join: run this from a clone of the team repository (no $PLUG/, knowledge/ and rules/ beside join.sh)"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "join: git is missing (the team's notes are shared through it)"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "join: python3 is missing (the brain's hooks and docs-local run on it)"; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || { echo "join: python3 is older than 3.9"; exit 1; }
echo "SDS brain: $HERE"

# 1. the home
mkdir -p "$CFG"
if [ -e "$LINK" ] && [ "$(cd "$LINK" && pwd -P)" = "$HERE" ]; then ok "home: $LINK"
elif [ -L "$LINK" ]; then rm -f "$LINK"; ln -s "$HERE" "$LINK"; ok "home: $LINK now points here (it pointed at another clone)"
elif [ -e "$LINK" ]; then bad "$LINK exists and is another folder: move it away, or run its own join.sh"; exit 1
else ln -s "$HERE" "$LINK"; ok "home: $LINK -> $HERE"; fi

# 2. the plugin (the marketplace is this folder; a marketplace of the same name from another folder is replaced)
WAS=$(python3 - "$CFG" "$PLUG" <<'PY' 2>/dev/null || true
import json, os, sys
d = json.load(open(os.path.join(sys.argv[1], "plugins", "known_marketplaces.json"))).get(sys.argv[2]) or {}
print(os.path.realpath(d.get("installLocation") or (d.get("source") or {}).get("path") or ""))
PY
)
if [ -n "$WAS" ] && [ "$WAS" != "$HERE" ]; then
  claude plugin uninstall "$PLUG@$PLUG" >/dev/null 2>&1 || true
  claude plugin marketplace remove "$PLUG" >/dev/null 2>&1 || true
  WAS=""
fi
if [ -n "$WAS" ]; then claude plugin marketplace update "$PLUG" >/dev/null 2>&1 || true
else claude plugin marketplace add "$HERE" >/dev/null 2>&1 || bad "claude plugin marketplace add $HERE failed"; fi
if claude plugin list 2>/dev/null | grep -q "$PLUG@$PLUG"; then claude plugin update "$PLUG@$PLUG" >/dev/null 2>&1 || true
else claude plugin install "$PLUG@$PLUG" >/dev/null 2>&1 || bad "claude plugin install $PLUG@$PLUG failed"; fi
if claude plugin list 2>/dev/null | grep -q "$PLUG@$PLUG"; then ok "plugin $PLUG installed"; else bad "plugin $PLUG is not installed"; fi
[ -z "$(git -C "$HERE" status --porcelain -- "$PLUG" 2>/dev/null)" ] ||
  note "$PLUG/ has uncommitted changes: commit them (Claude Code takes a new copy of the plugin only when the commit changes)"

# 3. the rules
touch "$MD"
if grep -qxF "$IMPORT" "$MD"; then ok "rules: $MD imports rules/main.md"
else printf '\n%s\n' "$IMPORT" >> "$MD"; ok "rules: import line added to $MD"; fi

# 4. docs
DOCS=$(sed -n 's/.*"url": *"\(https\{0,1\}:[^"]*\)".*/\1/p' "$HERE/$PLUG/.mcp.json" 2>/dev/null | grep '?team=' | head -1 || true)
CRT="$HERE/$PLUG/lib/paas-ui.crt"
EXTRA=""
if [ -z "$DOCS" ]; then
  if python3 "$HERE/$PLUG/tools/docs_server.py" --index >/dev/null 2>&1; then ok "docs: no VM docs service set up; docs-local searches this clone's docs/ (index built)"
  else bad "docs: the local index could not be built (python3 $PLUG/tools/docs_server.py --index shows why)"; fi
else
  base=${DOCS%%/mcp*}
  CA=""
  if [ "${DOCS#https://}" != "$DOCS" ] && [ -f "$CRT" ]; then
    CA="--cacert $CRT"
    installed=""
    if [ "$(uname -s)" = Darwin ]; then
      security add-trusted-cert -r trustRoot -k "$HOME/Library/Keychains/login.keychain-db" "$CRT" 2>/dev/null && installed="login keychain"
    elif [ "$NOSUDO" = 0 ] && command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
      if [ -d /etc/pki/ca-trust/source/anchors ]; then
        sudo cp "$CRT" /etc/pki/ca-trust/source/anchors/paas-sds.crt && sudo update-ca-trust && installed="system store (update-ca-trust)"
      elif [ -d /usr/local/share/ca-certificates ]; then
        sudo cp "$CRT" /usr/local/share/ca-certificates/paas-sds.crt && sudo update-ca-certificates >/dev/null 2>&1 && installed="system store (update-ca-certificates)"
      fi
    fi
    if [ -n "$installed" ]; then ok "docs: the VM's certificate is trusted: $installed"
    else                                                   # no sudo: Claude Code reads NODE_EXTRA_CA_CERTS when it starts
      cp "$CRT" "$CFG/paas-sds.crt"; EXTRA="$CFG/paas-sds.crt"
      for rc in "$HOME/.profile" "$HOME/.bashrc" "$HOME/.zshrc"; do
        [ -f "$rc" ] || [ "$rc" = "$HOME/.profile" ] || continue
        grep -q "NODE_EXTRA_CA_CERTS=$EXTRA" "$rc" 2>/dev/null || echo "export NODE_EXTRA_CA_CERTS=$EXTRA" >> "$rc"
      done
      ok "docs: the VM's certificate: NODE_EXTRA_CA_CERTS=$EXTRA in your shell profile (open a new terminal before starting claude)"
    fi
  fi
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 $CA "$base/health" 2>/dev/null || true)
  case "$code" in
    200) ok "docs: the VM's docs service answers: $base (docs-http: the library; docs-local: the team's knowledge here)" ;;
    000|"") bad "docs: the VM's docs service is not reachable at $base (the port must be open from this machine, the name must resolve)" ;;
    *) bad "docs: the VM's docs service at $base answered $code" ;;
  esac
fi

# what the person should know
if URL=$(git -C "$HERE" remote get-url origin 2>/dev/null); then
  note "notes are shared through $(printf '%s' "$URL" | sed 's#://[^/@]*@#://#') (you need push access)"
else note "this clone has no remote: notes stay on this machine until it has one"; fi
git -C "$HERE" config user.name >/dev/null 2>&1 || note "no git identity: notes are committed as $(id -un)@$(hostname) (git config --global user.name / user.email)"
if [ "$FAILED" = 0 ]; then echo "done: start claude in any folder; the first time, type /$PLUG:brain-setup to describe your clusters and grids"
else echo "some checks failed (above)"; exit 1; fi
