#!/usr/bin/env bash
# Create .venv and install deps for the given plane.
# Usage: ./setup.sh conductor   (on the NUC)
#        ./setup.sh forge        (on the workstation)
set -euo pipefail

PLANE="${1:-}"
if [[ "$PLANE" != "conductor" && "$PLANE" != "forge" ]]; then
    echo "Usage: $0 conductor|forge" >&2
    exit 1
fi

python3 -m venv .venv
echo "Created .venv"

case "$PLANE" in
    conductor)
        .venv/bin/pip install -r control/requirements.txt
        ;;
    forge)
        .venv/bin/pip install -r compute/requirements.txt
        ;;
esac

echo "Done. Activate with: source .venv/bin/activate"
