#!/bin/bash

set -u

START_TEST=1

CLIENT_COUNTS=(1 32 128 512 2048)
MSG_SIZES=(100 33000 66000)
INTERVALS=(1 2 5 10)
TIMEOUTS=(500 2000 5000 10000)

MESSAGES=305
PORT=8005

TEST_NO=0
CURRENT_ID=$START_TEST

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

SERVER_LOG_DIR="$SCRIPT_DIR/logs/PHP-Swoole/server"
CLIENT_LOG_DIR="$SCRIPT_DIR/logs/PHP-Swoole/client"

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

          # Start the PHP-Swoole server
          if ! docker run --name php-server --rm -d \
            --cpus="2" --memory="1.5g" \
            -p "$PORT:$PORT" \
            -v "$SERVER_LOG_DIR:/logs" \
            ws-php \
            php server.php \
            --port="$PORT" \
            --test-id="$CURRENT_ID"; then

            echo "ERROR: Failed to start server for test $CURRENT_ID"
            exit 1
          fi

          if [ $? -ne 0 ]; then
            echo "ERROR: Failed to start server for test $CURRENT_ID"
            exit 1
          fi

          echo "Waiting for PHP-Swoole server on port $PORT..."

            READY=0

            for attempt in $(seq 1 60); do
                if nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
                    READY=1
                    break
                fi
                sleep 1
            done

            if [ "$READY" -ne 1 ]; then
                echo "ERROR:  PHP-Swoole server did not become ready within 60 seconds."
                docker logs php-server
                docker stop -t 5 php-server
                exit 1
            fi

            echo "PHP-Swoole server is ready."

          # Run the Go client
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

          # Stop the server
          docker stop -t 120 php-server

          sleep 5

          CURRENT_ID=$((CURRENT_ID + 1))
        fi

      done
    done
  done
done

echo
echo "ALL TESTS COMPLETED"