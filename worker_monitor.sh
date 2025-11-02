#!/bin/bash
# Worker monitoring script for RQ workers
# Ensures 3 workers are always running and restarts them if they crash

# Don't use set -e here - we want to continue monitoring even if some operations fail

# Configuration
QUEUE_NAME="${RQ_QUEUE_NAME:-RECAP2-Classify}"
NUM_WORKERS="${NUM_WORKERS:-3}"
REDIS_URL="${RECAP_REDIS_URL}"
CHECK_INTERVAL="${CHECK_INTERVAL:-10}"  # seconds between checks

# Array to store worker PIDs
declare -a WORKER_PIDS
declare -a WORKER_NAMES

# Flag to control monitoring loop
MONITORING=true

# Logging function with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WORKER_MONITOR: $*" >&2
}

# Signal handler for graceful shutdown
cleanup() {
    log "Received shutdown signal, stopping workers..."
    MONITORING=false
    for pid in "${WORKER_PIDS[@]}"; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            log "Stopping worker PID $pid"
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    # Wait for workers to exit
    wait
    log "All workers stopped. Exiting monitor."
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT EXIT

# Start a single worker
start_worker() {
    local worker_index=$1
    local worker_name="worker-${worker_index}"
    local pid
    
    log "Starting $worker_name..."
    
    if [ -n "$REDIS_URL" ]; then
        rq worker --url "$REDIS_URL" "$QUEUE_NAME" --name "$worker_name" &
    else
        rq worker "$QUEUE_NAME" --name "$worker_name" &
    fi
    
    pid=$!
    WORKER_PIDS[$worker_index]=$pid
    WORKER_NAMES[$worker_index]=$worker_name
    
    # Give worker a moment to start
    sleep 1
    
    if kill -0 "$pid" 2>/dev/null; then
        log "$worker_name started successfully with PID $pid"
        return 0
    else
        log "ERROR: Failed to start $worker_name"
        WORKER_PIDS[$worker_index]=""
        return 1
    fi
}

# Check if a worker process is alive
is_worker_alive() {
    local pid=$1
    if [ -z "$pid" ]; then
        return 1
    fi
    
    # Check if process exists and is actually an rq worker
    if kill -0 "$pid" 2>/dev/null; then
        # Verify it's still an rq worker process
        if ps -p "$pid" -o args= | grep -q "rq worker"; then
            return 0
        fi
    fi
    return 1
}

# Restart a dead worker
restart_worker() {
    local worker_index=$1
    local worker_name="${WORKER_NAMES[$worker_index]}"
    
    log "Worker $worker_name (PID ${WORKER_PIDS[$worker_index]}) has died. Restarting..."
    WORKER_PIDS[$worker_index]=""
    start_worker "$worker_index"
}

# Main monitoring loop
monitor_loop() {
    log "Starting worker monitor for $NUM_WORKERS workers on queue '$QUEUE_NAME'"
    
    # Start all workers initially
    for i in $(seq 0 $((NUM_WORKERS - 1))); do
        start_worker "$i"
        sleep 1  # Stagger worker starts slightly
    done
    
    log "All workers started. Beginning monitoring loop (checking every ${CHECK_INTERVAL}s)..."
    
    # Monitoring loop
    while $MONITORING; do
        sleep "$CHECK_INTERVAL"
        
        # Check each worker
        for i in $(seq 0 $((NUM_WORKERS - 1))); do
            if ! is_worker_alive "${WORKER_PIDS[$i]}"; then
                restart_worker "$i"
            fi
        done
    done
}

# Main execution
if [ -z "$REDIS_URL" ]; then
    log "WARNING: RECAP_REDIS_URL not set, workers will try to connect to localhost:6379"
fi

monitor_loop
