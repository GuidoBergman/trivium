#!/usr/bin/env bash
# Install the Trivium skills into ~/.claude/skills so they work in any repository.
#
# Symlinks rather than copies, so editing a skill here takes effect immediately
# with no reinstall step.
#
#   ./install.sh            install or refresh
#   ./install.sh --uninstall remove the links

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${HOME}/.claude/skills"
SKILLS=(trivium-shared trivium-init trivium-status trivium-study trivium-synthesize trivium-converse)

mkdir -p "$DEST"

if [[ "${1:-}" == "--uninstall" ]]; then
  for skill in "${SKILLS[@]}"; do
    if [[ -L "$DEST/$skill" ]]; then
      rm "$DEST/$skill"
      echo "removed $skill"
    fi
  done
  exit 0
fi

for skill in "${SKILLS[@]}"; do
  src="$REPO/skills/$skill"
  dst="$DEST/$skill"

  if [[ ! -d "$src" ]]; then
    echo "error: missing $src" >&2
    exit 1
  fi

  if [[ -e "$dst" && ! -L "$dst" ]]; then
    echo "error: $dst exists and is not a symlink. Move it aside first." >&2
    exit 1
  fi

  ln -sfn "$src" "$dst"
  echo "linked $skill"
done

echo
echo "Checking dependencies."
python3 - <<'PY'
import shutil, sys
ok = True
print(f"  python3: {sys.version.split()[0]}")
if shutil.which("pdftotext"):
    print("  pdftotext: found (preferred PDF extractor)")
else:
    try:
        import pypdf  # noqa: F401
        print("  pdftotext: missing, falling back to pypdf")
    except ImportError:
        ok = False
        print("  PDF extraction: UNAVAILABLE")
        print("    install poppler-utils, or: pip install pypdf")
print("  EPUB extraction: available (standard library)")
sys.exit(0 if ok else 1)
PY

echo
echo "Done. Start a topic with the trivium-init skill."
