#!/bin/bash

echo "Test is starting.."
sleep 5

echo "================================"
echo "STARTING GO-GORILLA TESTS"
echo "================================"

./server_test_go.sh

echo "================================"
echo "GO-GORILLA TESTS FINISHED"
echo "================================"

echo "================================"
echo "STARTING JAVA-NETTY TESTS"
echo "================================"

./server_test_java_netty.sh

echo "================================"
echo "JAVA-NETTY TESTS FINISHED"
echo "================================"

echo "================================"
echo "STARTING JAVA-WEBSOCKET TESTS"
echo "================================"

./server_test_java_ws.sh

echo "================================"
echo "JAVA-WEBSOCKET TESTS FINISHED"
echo "================================"

echo "================================"
echo "STARTING NODE-UWS TESTS"
echo "================================"

./server_test_node_uws.sh

echo "================================"
echo "NODE-UWS TESTS FINISHED"
echo "================================"

echo "================================"
echo "STARTING NODE-WS TESTS"
echo "================================"

./server_test_node_ws.sh

echo "================================"
echo "NODE-WS TESTS FINISHED"
echo "================================"

echo "================================"
echo "STARTING PHP-SWOOLE TESTS"
echo "================================"

./server_test_php.sh

echo "================================"
echo "PHP-SWOOLE TESTS FINISHED"
echo "================================"

echo "================================"
echo "STARTING PYTHON-WEBSOCKETS TESTS"
echo "================================"

./server_test_python.sh

echo "================================"
echo "ALL TESTS FINISHED"
echo "================================"

# Shutdown the computer 60 seconds from now
sudo shutdown -h +1