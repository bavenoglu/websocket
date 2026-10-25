FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y wget tar ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN wget -q https://go.dev/dl/go1.25.6.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go1.25.6.linux-amd64.tar.gz \
    && rm go1.25.6.linux-amd64.tar.gz

ENV PATH="/usr/local/go/bin:${PATH}"

COPY client.go .

RUN go mod init go-client \
    && go get github.com/gorilla/websocket@v1.5.3 \
    && go build -o client

ENTRYPOINT ["./client"]