#!/usr/bin/env bash
set -e
trap 'echo "ERROR: D1 setup failed. Use Python 3 with numpy and matplotlib already available." >&2' ERR
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
echo '=== Check Python simulation dependencies ==='
python3 -c 'import numpy, matplotlib; print("numpy and matplotlib: OK")'
echo '=== Ready: run bash d1_bayes_sim/run.sh from the repository root ==='
