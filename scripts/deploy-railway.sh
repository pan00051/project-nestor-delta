#!/usr/bin/env bash
# The single entry point for deploying one Railway service.
#
# Why this exists
# ---------------
# This project deploys by CLI upload, so `railway source` reports repo: null and
# Railway injects no RAILWAY_GIT_COMMIT_SHA. The deploy image also excludes
# .git (.dockerignore, .railwayignore). Every automatic source of the running
# revision is therefore unavailable and the service would report "unknown".
#
# This script writes NESTOR_BUILD_SHA immediately before uploading, so the value
# is set once per deploy and can never become a hand-set constant that outlives
# the code it names. Do NOT set NESTOR_BUILD_SHA in the Railway dashboard: a
# variable that survives the next deploy is a hardcoded version string, which is
# the defect this whole mechanism exists to prevent.
#
# Railway CLI flag syntax differs between major versions and was NOT verified
# from the authoring environment. If a railway command below fails, correct the
# flags here rather than working around it by hand.
#
# Usage:
#   scripts/deploy-railway.sh <service> [health-url]
#   scripts/deploy-railway.sh api https://api-production-9849.up.railway.app/health

set -euo pipefail

SERVICE="${1:-}"
HEALTH_URL="${2:-}"

if [[ -z "$SERVICE" ]]; then
  echo "usage: $0 <service> [health-url]" >&2
  exit 64
fi

command -v git >/dev/null     || { echo "git not found" >&2; exit 69; }
command -v railway >/dev/null  || { echo "railway CLI not found" >&2; exit 69; }

# 1. Refuse to deploy a working tree that does not match any commit. A revision
#    that names a commit whose contents were not what shipped is worse than
#    "unknown", because it looks authoritative.
if [[ -n "$(git status --porcelain)" ]]; then
  echo "working tree is dirty; commit or stash before deploying" >&2
  git status --short >&2
  exit 65
fi

SHA="$(git rev-parse --short=12 HEAD)"
echo "service        : $SERVICE"
echo "source revision: $SHA"

# 2. Stamp, then deploy immediately. The two steps must not be separated.
railway variables --set "NESTOR_BUILD_SHA=$SHA" --service "$SERVICE"
railway up --service "$SERVICE"

# 3. Verify the running process reports what we stamped. Cache-busted: the
#    canonical capabilities URL has been observed returning stale responses and
#    the mechanism is undiagnosed, so an uncached check could confirm a deploy
#    that never happened.
if [[ -z "$HEALTH_URL" ]]; then
  echo
  echo "no health URL given; verify manually once the deploy settles:"
  echo "  curl -s '<service>/health?cb=\$RANDOM'   # expect source_revision $SHA"
  exit 0
fi

echo
echo "verifying $HEALTH_URL ..."
for attempt in $(seq 1 30); do
  BODY="$(curl -fsS "${HEALTH_URL}?cb=${RANDOM}${attempt}" 2>/dev/null || true)"
  LIVE="$(printf '%s' "$BODY" | sed -n 's/.*"source_revision" *: *"\([^"]*\)".*/\1/p')"
  if [[ -n "$LIVE" ]]; then
    if [[ "$LIVE" == "$SHA"* || "$SHA" == "$LIVE"* ]]; then
      echo "OK  live source_revision=$LIVE matches $SHA"
      exit 0
    fi
    if [[ "$LIVE" == "unknown" ]]; then
      echo "  attempt $attempt: source_revision=unknown (old build still serving)"
    else
      echo "  attempt $attempt: source_revision=$LIVE (expected $SHA)"
    fi
  fi
  sleep 10
done

echo "FAILED: $HEALTH_URL never reported source_revision $SHA" >&2
echo "        'unknown' means the variable did not reach the process." >&2
exit 1
