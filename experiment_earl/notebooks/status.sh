#!/usr/bin/env bash
# Status of a simulation notebook run started from the terminal: running or not, CPU and memory, latest progress.
# Usage (repository root):  bash experiment_earl/notebooks/status.sh [lines]      live: watch -n 5 bash experiment_earl/notebooks/status.sh
cd "$(dirname "$0")/../.." || exit 1
RUNS=experiment_earl/runs
LINES=${1:-20}

PID=$(cat "$RUNS/notebook_run.pid" 2>/dev/null)
if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
    echo "RUNNING (PID $PID)"
    ps -o pid,etime,%cpu,%mem,cmd -p "$PID"
    ps -o pid,etime,%cpu,%mem,cmd --ppid "$PID" --no-headers   # the kernel doing the work
else
    echo "NOT RUNNING${PID:+ (last PID $PID)}"
    if grep -q "Error\|Traceback" "$RUNS/notebook_run.log" 2>/dev/null; then
        echo "--- the run stopped with an error ($RUNS/notebook_run.log):"
        tail -n 15 "$RUNS/notebook_run.log"
    fi
fi

if [ -f "$RUNS/batch_log.csv" ]; then
    echo
    echo "batch runs logged: $(($(wc -l < "$RUNS/batch_log.csv") - 1)) ($(grep -c ',failed,' "$RUNS/batch_log.csv") failed)"
fi

echo
echo "--- last $LINES progress lines ($RUNS/notebook_progress.log)"
tail -n "$LINES" "$RUNS/notebook_progress.log" 2>/dev/null || echo "(no progress log yet)"
