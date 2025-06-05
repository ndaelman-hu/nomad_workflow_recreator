#!/bin/bash
"""
MCP Server Manager - Start/stop all MCP servers
"""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_DIR="$SCRIPT_DIR/.pids"
LOG_DIR="$SCRIPT_DIR/logs"

# Create directories if they don't exist
mkdir -p "$PID_DIR" "$LOG_DIR"

start_servers() {
    echo "Starting MCP servers..."
    
    # Activate virtual environment
    source "$SCRIPT_DIR/.venv/bin/activate"
    
    # Start NOMAD server
    python "$SCRIPT_DIR/src/nomad_server_enhanced.py" > "$LOG_DIR/nomad.log" 2>&1 &
    echo $! > "$PID_DIR/nomad.pid"
    echo "✓ NOMAD server started (PID: $(cat $PID_DIR/nomad.pid))"
    
    # Start Memgraph server
    python "$SCRIPT_DIR/src/memgraph_server_enhanced.py" > "$LOG_DIR/memgraph.log" 2>&1 &
    echo $! > "$PID_DIR/memgraph.pid"
    echo "✓ Memgraph server started (PID: $(cat $PID_DIR/memgraph.pid))"
    
    # Start Logger server
    python "$SCRIPT_DIR/src/logger_server.py" > "$LOG_DIR/logger.log" 2>&1 &
    echo $! > "$PID_DIR/logger.pid"
    echo "✓ Logger server started (PID: $(cat $PID_DIR/logger.pid))"
    
    echo ""
    echo "All servers started! Logs in: $LOG_DIR"
    echo "Now run: claude --config claude_config.json"
}

stop_servers() {
    echo "Stopping MCP servers..."
    
    for server in nomad memgraph logger; do
        if [ -f "$PID_DIR/$server.pid" ]; then
            PID=$(cat "$PID_DIR/$server.pid")
            if kill -0 $PID 2>/dev/null; then
                kill $PID
                echo "✓ Stopped $server server (PID: $PID)"
            else
                echo "⚠ $server server not running (stale PID: $PID)"
            fi
            rm "$PID_DIR/$server.pid"
        else
            echo "⚠ No PID file for $server server"
        fi
    done
}

status_servers() {
    echo "MCP Server Status:"
    echo "=================="
    
    for server in nomad memgraph logger; do
        if [ -f "$PID_DIR/$server.pid" ]; then
            PID=$(cat "$PID_DIR/$server.pid")
            if kill -0 $PID 2>/dev/null; then
                echo "✓ $server: Running (PID: $PID)"
            else
                echo "✗ $server: Not running (stale PID file)"
            fi
        else
            echo "✗ $server: Not running"
        fi
    done
    
    echo ""
    echo "Recent logs:"
    for log in nomad memgraph logger; do
        if [ -f "$LOG_DIR/$log.log" ]; then
            echo "--- $log.log (last 3 lines) ---"
            tail -3 "$LOG_DIR/$log.log"
        fi
    done
}

restart_servers() {
    stop_servers
    echo ""
    sleep 2
    start_servers
}

case "$1" in
    start)
        start_servers
        ;;
    stop)
        stop_servers
        ;;
    restart)
        restart_servers
        ;;
    status)
        status_servers
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start all MCP servers in background"
        echo "  stop    - Stop all MCP servers"
        echo "  restart - Restart all MCP servers"
        echo "  status  - Check server status"
        exit 1
        ;;
esac