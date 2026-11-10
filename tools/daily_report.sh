#!/usr/bin/env bash
# Daily report data for the river-daily-report scheduled task (owner 2026-11-10: no console windows, no prompts).
# Read-only: gh and curl only, every call time-limited; no Python, no git (a `git pull` here once merged main into the
# owner's working branch). Health comes from the hourly cloud watchdog (watchdog.yml). Each missing part prints UNKNOWN.
R=MwooVancity/riverwaterlevels
L='adding [0-9]+ gauges|^.*  [0-9]{8}  |not released|release committed|release DROPPED|release SKIPPED|refresh OK|refresh FAILED|STOPPED|SITE FAIL| FAIL |sitemap resubmitted|sitemap not resubmitted'

W=$(timeout 60 gh run list -R $R --workflow watchdog.yml --limit 1 --json databaseId,createdAt --jq '.[0] | "\(.databaseId) \(.createdAt)"' 2>&1) || W=""
if [ -z "$W" ] || ! [[ "$W" =~ ^[0-9]+\  ]]; then
  echo "HEALTH: UNKNOWN (gh failed: ${W:-no watchdog run}; if it says auth or login, the PC's GitHub login expired)"
else
  echo "watchdog run: $W (now $(date -u +%FT%TZ))"
  H=$(timeout 60 gh run view "${W%% *}" -R $R --log 2>&1 | grep -E "SITE HEALTH|PROBLEM|HTTP [0-9]{3}" | sed 's/^.*Z //')
  case "$H" in *"SITE HEALTH"*) echo "$H";; *) echo "HEALTH: UNKNOWN (log not readable: ${H:-timed out or empty})";; esac  # GitHub log downloads can 503 ("Egress is over the account limit")
fi
echo "--- status.json"
S=$(curl -s -m 20 https://riverwaterlevels.com/status.json | head -c 300)
case "$S" in "{"*) echo "$S";; *) echo "LIVE SITE: UNKNOWN (status.json did not answer)";; esac
echo "--- river pages in sitemap"
M=$(curl -s -m 30 https://riverwaterlevels.com/sitemap.xml)
if [ -n "$M" ]; then echo "$M" | grep -o "<loc>[^<]*/river/[^<]*" | wc -l; else echo "SITEMAP: UNKNOWN (did not answer)"; fi
echo "--- refresh runs, last 24 h"
SINCE=$(date -u -d '24 hours ago' +%FT%TZ); TODAY=$(date -u +%F)
RUNS=$(timeout 60 gh run list -R $R --workflow refresh.yml --limit 30 --json databaseId,createdAt,conclusion \
  --jq ".[] | select(.createdAt >= \"$SINCE\") | \"\(.databaseId) \(.createdAt) \(.conclusion)\"" 2>&1) || RUNS="UNKNOWN: $RUNS"
echo "$RUNS"
# Logs only for today's release window (11:00-11:59 UTC) and any run that did not succeed.
echo "$RUNS" | while read -r id at concl; do
  [[ "$id" =~ ^[0-9]+$ ]] || continue
  if [[ "$at" == ${TODAY}T11:* ]] || [ "$concl" != success ]; then
    echo "== run $id $at $concl"
    timeout 60 gh run view "$id" -R $R --log 2>/dev/null | grep -E "$L" | sed 's/^.*Z //' | head -40
  fi
done
