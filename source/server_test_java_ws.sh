#!/bin/bash

set -u

START_TEST=1

CLIENT_COUNTS=(1 32 128 512 2048)
MSG_SIZES=(100 33000 66000)
INTERVALS=(1 2 5 10)
TIMEOUTS=(500 2000 5000 10000)

MESSAGES=305
PORT=8002

TEST_NO=0
CURRENT_ID=$START_TEST

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

SERVER_LOG_DIR="$SCRIPT_DIR/logs/Java-WebSocket/server"
CLIENT_LOG_DIR="$SCRIPT_DIR/logs/Java-WebSocket/client"

mkdir -p "$SERVER_LOG_DIR" "$CLIENT_LOG_DIR"

for C in "${CLIENT_COUNTS[@]}"; do
  for S in "${MSG_SIZES[@]}"; do
    for I in "${INTERVALS[@]}"; do
      for T in "${TIMEOUTS[@]}"; do

        TEST_NO=$((TEST_NO + 1))

        if [ "$TEST_NO" -ge "$START_TEST" ]; then

          echo
          echo "================================"
          echo "TEST ID $CURRENT_ID"
          echo "Clients=$C Size=$S Interval=$I Timeout=$T"
          echo "================================"

          # Start the server container
          if ! docker run --name java-ws-server --rm -d \
            --cpus="2" --memory="1.5g" \
            -p "$PORT:$PORT" \
            -v "$SERVER_LOG_DIR:/logs" \
            ws-java-ws \
            java -jar server.jar \
            --port="$PORT" \
            --test-id="$CURRENT_ID"; then

            echo "ERROR: Failed to start server for test $CURRENT_ID"
            exit 1
          fi

          if [ $? -ne 0 ]; then
            echo "ERROR: Failed to start server for test $CURRENT_ID"
            exit 1
          fi

          echo "Waiting for Java ws server on port $PORT..."

            READY=0

            for attempt in $(seq 1 60); do
                if nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
                    READY=1
                    break
                fi
                sleep 1
            done

            if [ "$READY" -ne 1 ]; then
                echo "ERROR:  Java ws server did not become ready within 60 seconds."
                docker logs java-ws-server
                docker stop -t 5 java-ws-server
                exit 1
            fi

            echo "Java ws server is ready."

          # Run the client container
          docker run --rm \
            --cpus="3" --memory="2g" \
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

          CLIENT_EXIT_CODE=$?
          echo "Client exit code: $CLIENT_EXIT_CODE"

          echo "Waiting to write logs"

          # Stop the server container
          docker stop -t 120 java-ws-server

          sleep 5

          CURRENT_ID=$((CURRENT_ID + 1))
        fi

      done
    done
  done
done

echo
echo "ALL TESTS COMPLETED"
```