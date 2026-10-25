#!/bin/bash

START_TEST=1

CLIENT_COUNTS=(1 32 128 512 2048)
MSG_SIZES=(100 33000 66000)
INTERVALS=(1 2 5 10)
TIMEOUTS=(500 2000 5000 10000)

MESSAGES=305
PORT=8006

TEST_NO=0
CURRENT_ID=$START_TEST

# Use the directory containing this script as the project directory.
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

SERVER_LOG_DIR="$PROJECT_DIR/logs/Python-websockets/server"
CLIENT_LOG_DIR="$PROJECT_DIR/logs/Python-websockets/client"

mkdir -p "$SERVER_LOG_DIR" "$CLIENT_LOG_DIR"

for C in "${CLIENT_COUNTS[@]}"; do
  for S in "${MSG_SIZES[@]}"; do
    for I in "${INTERVALS[@]}"; do
      for T in "${TIMEOUTS[@]}"; do

        TEST_NO=$((TEST_NO + 1))

        if [ "$TEST_NO" -lt "$START_TEST" ]; then
          continue
        fi

        echo
        echo "================================"
        echo "TEST ID $CURRENT_ID"
        echo "Clients=$C Size=$S Interval=$I Timeout=$T"
        echo "================================"

        # Start the Python WebSocket server.
        docker run \
          --name python-server \
          --rm -d \
          --cpus="2" \
          --memory="1.5g" \
          -p "$PORT:$PORT" \
          -v "$SERVER_LOG_DIR:/logs" \
          ws-python \
          python3 server.py \
          --port="$PORT" \
          --test-id="$CURRENT_ID"

        echo "Waiting for Python server on port $PORT..."

        READY=0

        for attempt in $(seq 1 60); do
          if nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
            READY=1
            break
          fi
          sleep 1
        done

        if [ "$READY" -ne 1 ]; then
          echo "ERROR: Python server did not become ready within 60 seconds."
          docker logs python-server
          docker stop -t 5 python-server
          exit 1
        fi

        echo "Python server is ready."

        # Run the Go client.
        docker run \
          --rm \
          --cpus="3" \
          --memory="2g" \
          --add-host=host.docker.internal:host-gateway \
          -v "$CLIENT_LOG_DIR:/logs" \
          go-client \
          --host host.docker.internal \
          --port "$PORT" \
          --test-id "$CURRENT_ID" \
          --clients "$C" \
          --messages "$MESSAGES" \
          --interval "$I" \
          --timeout "$T" \
          --message-size "$S"

        CLIENT_EXIT=$?

        echo "Client exit code: $CLIENT_EXIT"
        echo "Waiting to write logs"

        # Stop the server and allow graceful shutdown.
        docker stop -t 120 python-server

        sleep 5

        CURRENT_ID=$((CURRENT_ID + 1))

      done
    done
  done
done

echo
echo "ALL TESTS COMPLETED"
