#!/bin/bash
# cycle-report.sh — TaskCompleted hook for autoresearch
# Reads cycle/baseline task completion events and outputs a formatted
# report from the relevant summary files as additionalContext.

set -euo pipefail

INPUT=$(cat)
SUBJECT=$(echo "$INPUT" | jq -r '.task.subject // empty')

# Only act on autoresearch cycle/baseline tasks
case "$SUBJECT" in
  "Establish baseline"|Cycle\ *)
    ;;
  *)
    exit 0
    ;;
esac

RESULTS_DIR=".autoresearch/results"
SCORES_FILE="$RESULTS_DIR/scores.json"

REPORT=""

if [ "$SUBJECT" = "Establish baseline" ]; then
  SUMMARY_FILE="$RESULTS_DIR/summary_current.json"
  if [ -f "$SUMMARY_FILE" ]; then
    PASSED=$(jq -r '.passed' "$SUMMARY_FILE")
    TOTAL=$(jq -r '.total' "$SUMMARY_FILE")
    PCT=$(jq -r '.pass_rate * 100 | floor' "$SUMMARY_FILE")

    REPORT="## Baseline Established"$'\n\n'"Pass rate: ${PASSED}/${TOTAL} (${PCT}%)"

    ASSERTIONS=$(jq -r '.assertion_pass_rates | to_entries[] | "| " + .key + " | " + (.value * 100 | floor | tostring) + "% |"' "$SUMMARY_FILE" 2>/dev/null || true)
    if [ -n "$ASSERTIONS" ]; then
      REPORT="$REPORT"$'\n\n'"| Assertion | Pass Rate |"$'\n'"|-----------|-----------|"$'\n'"$ASSERTIONS"
    fi
  fi
else
  # Extract cycle number from "Cycle N"
  CYCLE_NUM=$(echo "$SUBJECT" | sed 's/Cycle //')

  # Only look at summary files for this cycle's variants + current
  REPORT="## ${SUBJECT} Results"$'\n\n'"| Variant | Pass Rate | vs Current |"$'\n'"|---------|-----------|------------|"

  CURRENT_RATE=""
  CURRENT_FILE="$RESULTS_DIR/summary_current.json"
  if [ -f "$CURRENT_FILE" ]; then
    CURRENT_RATE=$(jq -r '.pass_rate' "$CURRENT_FILE")
    PCT=$(jq -r '.pass_rate * 100 | floor' "$CURRENT_FILE")
    REPORT="$REPORT"$'\n'"| current | ${PCT}% | — |"
  fi

  # Find this cycle's candidate summaries: summary_v{N}a.json, summary_v{N}b.json, etc.
  FOUND_CANDIDATES=false
  for SUFFIX in a b c d e; do
    SUMMARY_FILE="$RESULTS_DIR/summary_v${CYCLE_NUM}${SUFFIX}.json"
    [ -f "$SUMMARY_FILE" ] || continue
    FOUND_CANDIDATES=true

    NAME=$(jq -r '.prompt' "$SUMMARY_FILE")
    PASS_RATE=$(jq -r '.pass_rate' "$SUMMARY_FILE")
    PCT=$(jq -r '.pass_rate * 100 | floor' "$SUMMARY_FILE")

    if [ -n "$CURRENT_RATE" ]; then
      DELTA=$(jq -n "($PASS_RATE - $CURRENT_RATE) * 100 | floor")
      if [ "$DELTA" -ge 0 ] 2>/dev/null; then
        DELTA_FMT="+${DELTA}%"
      else
        DELTA_FMT="${DELTA}%"
      fi
    else
      DELTA_FMT="—"
    fi

    REPORT="$REPORT"$'\n'"| ${NAME} | ${PCT}% | ${DELTA_FMT} |"
  done

  if [ "$FOUND_CANDIDATES" = false ]; then
    exit 0
  fi

  # Add trajectory from scores.json
  if [ -f "$SCORES_FILE" ]; then
    TRAJECTORY=$(jq -r '[.[].pass_rate | . * 100 | floor | tostring + "%"] | join(" → ")' "$SCORES_FILE" 2>/dev/null || true)
    if [ -n "$TRAJECTORY" ]; then
      REPORT="$REPORT"$'\n\n'"**Trajectory:** ${TRAJECTORY}"
    fi
  fi
fi

if [ -n "$REPORT" ]; then
  jq -n --arg ctx "$REPORT" '{"additionalContext": $ctx}'
fi

exit 0
