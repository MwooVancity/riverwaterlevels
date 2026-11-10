#!/usr/bin/env bash
# Shell half of the river-request-indexing scheduled task (owner 2026-11-10: no console windows, no prompts).
#   bash tools/index_job.sh next          -> up to 10 URLs to request today
#   bash tools/index_job.sh done URL...   -> record Google-confirmed URLs, commit that one file, push to check
# Edge cases: Python by glob (plain `python` is the Windows Store shim that opens a console; a 3.15 update must not
# break this); git never prompts or opens an editor; only data/reindex-done.txt is committed (another session may be
# working here); push only on branch check; zero URLs = no commit; a rebase conflict aborts cleanly.
cd "$(dirname "$0")/.." || exit 1
PY=$(ls -d /c/Users/mwoo7/AppData/Local/Python/pythoncore-3.*-64/python.exe 2>/dev/null | sort -V | tail -1)
[ -x "$PY" ] || { echo "FAIL: no Python found under AppData/Local/Python"; exit 1; }
export GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never GIT_EDITOR=true
case "$1" in
  next) timeout 120 "$PY" -I tools/reindex.py next 10 ;;
  done)
    shift
    [ $# -gt 0 ] || { echo "nothing confirmed: no commit"; exit 0; }
    "$PY" -I tools/reindex.py done "$@" || exit 1
    git commit -q -m "Request indexing: $# confirmed ($(date +%F))" -- data/reindex-done.txt || { echo "FAIL: commit"; exit 1; }
    if [ "$(git rev-parse --abbrev-ref HEAD)" != check ]; then echo "not on branch check: committed locally, not pushed"; exit 0; fi
    if ! timeout 120 git pull -q --rebase --autostash origin check; then git rebase --abort 2>/dev/null; echo "FAIL: pull conflict, committed locally, not pushed"; exit 1; fi
    timeout 120 git push -q origin check && echo "pushed $# confirmed" || echo "FAIL: push"
    ;;
  *) echo "usage: index_job.sh next | done URL..."; exit 2 ;;
esac
