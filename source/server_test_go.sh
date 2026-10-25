#!/bin/bash

START_TEST=1

CLIENT_COUNTS=(1 32 128 512 2048)
MSG_SIZES=(100 33000 66000)
INTERVALS=(1 2 5 10)
TIMEOUTS=(500 2000 5000 10000)

MESSAGES=305
PORT=8000

TEST_NO=0
CURRENT_ID=$START_TEST

# Use the directory containing this script as the project directory.
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

SERVER_LOG_DIR="$PROJECT_DIR/logs/go/server"
CLIENT_LOG_DIR="$PROJECT_DIR/logs/go/client"

mkdir -p "$SERVER_LOG_DIR" "$CLIENT_LOG_DIR"

for c in "${CLIENT_COUNTS[@]}"; do
  for s in "${MSG_SIZES[@]}"; do
    for i in "${INTERVALS[@]}"; do
      for t in "${TIMEOUTS[@]}"; do

          TEST_NO=$((TEST_NO + 1))

          if [ $TEST_NO -ge $START_TEST ]; then

            echo ""
            echo "================================"
            echo "TEST ID $CURRENT_ID"
            echo "Clients=$c Size=$s Interval=$i Timeout=$t"
            echo "================================"
              
            docker run --name go-server --rm -d \
              --cpus="2" --memory="1.5g" \
              -p "$PORT:$PORT" \
              -v "$SERVER_LOG_DIR:/logs" \
              ws-go ./server -port "$PORT" -test-id "$CURRENT_ID"
              
            echo "Waiting for Go server on port $PORT..."

            READY=0

            for attempt in $(seq 1 60); do
                if nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
                    READY=1
                    break
                fi
                sleep 1
            done

            if [ "$READY" -ne 1 ]; then
                echo "ERROR:  Go server did not become ready within 60 seconds."
                docker logs go-server
                docker stop -t 5 go-server
                exit 1
            fi

            echo "Go server is ready."
              
            docker run --rm \
              --cpus="3" --memory="2g" \
              --add-host=host.docker.internal:host-gateway \
              -v "$(pwd)/logs/Go/client:/logs" \
              go-client \
              --host host.docker.internal \
              --port "$PORT" \
              --test-id "$CURRENT_ID" \
              --clients "$c" \
              --messages "$MESSAGES" \
              --interval "$i" \
              --timeout "$t" \
              --message-size "$s"
            
            echo "Waiting to write logs"
            docker stop -t 120 go-server
            sleep 5

            CURRENT_ID=$((CURRENT_ID + 1))
          fi
      done
    done
  done
done

echo ""
echo "ALL TESTS COMPLETED"