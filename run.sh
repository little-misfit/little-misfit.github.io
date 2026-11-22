#!/usr/bin/env bash
set -euo pipefail
site_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$site_dir"
case "${1:-preview}" in
    preview) python3 tools/export_preview.py ;;
    fonts) python3 tools/export_slogan_options.py ;;
    serve) python3 -m http.server "${2:-8768}" --bind 127.0.0.1 ;;
    check) python3 tests/check_site.py ;;
    *) echo "Usage: bash run.sh [preview|fonts|serve [port]|check]" >&2; exit 2 ;;
esac
