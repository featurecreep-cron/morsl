#!/bin/bash
# Server management script for Morsl

PORT=8321
PIDFILE="/tmp/morsl.pid"
LOGFILE="/tmp/morsl.log"

start() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "Server is already running (PID: $(cat $PIDFILE))"
        return 1
    fi

    # Check if port is in use
    if lsof -i :$PORT >/dev/null 2>&1; then
        echo "Port $PORT is already in use"
        lsof -i :$PORT
        return 1
    fi

    echo "Starting server on port $PORT..."
    nohup uvicorn morsl.app.main:app --port $PORT --host 127.0.0.1 > "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    sleep 2

    if kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "Server started (PID: $(cat $PIDFILE))"
        echo "Log file: $LOGFILE"
    else
        echo "Failed to start server. Check $LOGFILE for details"
        rm -f "$PIDFILE"
        return 1
    fi
}

stop() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 $PID 2>/dev/null; then
            echo "Stopping server (PID: $PID)..."
            kill $PID
            sleep 2
            if kill -0 $PID 2>/dev/null; then
                echo "Force killing..."
                kill -9 $PID
            fi
            echo "Server stopped"
        else
            echo "Server not running (stale PID file)"
        fi
        rm -f "$PIDFILE"
    else
        echo "No PID file found"
    fi

    # Also kill any orphaned processes on the port
    if lsof -i :$PORT >/dev/null 2>&1; then
        echo "Killing processes on port $PORT..."
        fuser -k $PORT/tcp 2>/dev/null
    fi
}

restart() {
    echo "Restarting server..."
    stop
    sleep 1
    start
}

status() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "Server is running (PID: $(cat $PIDFILE))"
        curl -s http://localhost:$PORT/api/status | python3 -m json.tool 2>/dev/null || echo "API not responding"
    else
        echo "Server is not running"
        if lsof -i :$PORT >/dev/null 2>&1; then
            echo "Warning: Port $PORT is in use by another process:"
            lsof -i :$PORT
        fi
    fi
}

logs() {
    if [ -f "$LOGFILE" ]; then
        tail -f "$LOGFILE"
    else
        echo "No log file found at $LOGFILE"
    fi
}

cache_clear() {
    echo "API cache is in-memory — restarting server to clear it..."
    restart
}

restart_clean() {
    cache_clear
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    restart-clean)
        restart_clean
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    cache-clear)
        cache_clear
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|restart-clean|status|logs|cache-clear}"
        echo ""
        echo "Commands:"
        echo "  start         - Start the uvicorn server"
        echo "  stop          - Stop the server"
        echo "  restart       - Restart the server"
        echo "  restart-clean - Clear cache and restart the server"
        echo "  status        - Check if server is running"
        echo "  logs          - Tail the server log file"
        echo "  cache-clear   - Restart server to clear in-memory API cache"
        exit 1
        ;;
esac
