@echo off

echo Building client...
docker build -t go-client ./client

echo Building servers...

docker build -t ws-go ./servers/go

docker build -t ws-node-ws ./servers/node.js-ws

docker build -t ws-node-uws ./servers/node.js-uws

docker build -t ws-java-ws ./servers/java-ws

docker build -t ws-java-netty ./servers/java-netty

docker build -t ws-python ./servers/python

docker build -t ws-php ./servers/php

echo All server images built.
pause
