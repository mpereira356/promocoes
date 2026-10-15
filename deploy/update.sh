#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"
if [[ "$#" -gt 1 || ( "$#" -eq 1 && "$1" != "--no-pull" ) ]]; then
    printf 'Uso: bash deploy/update.sh [--no-pull]\n' >&2
    exit 1
fi
if [[ "${1:-}" != "--no-pull" ]]; then
    if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
        printf 'Existem alteracoes locais. Salve ou revise antes de atualizar.\n' >&2
        exit 1
    fi
    git pull --ff-only
    exec bash "$repo_dir/deploy/update.sh" --no-pull
fi
if [[ "$EUID" -eq 0 ]]; then
    bash deploy/install-kali.sh --with-browser
else
    sudo bash deploy/install-kali.sh --with-browser
fi
