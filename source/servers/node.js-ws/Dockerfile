FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# 1. DEPENDENCIES
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# 2. NODE IMPLEMENTATION
COPY --from=node:24.13.0-bookworm /usr/local/bin/node /usr/local/bin/node
COPY --from=node:24.13.0-bookworm /usr/local/lib/node_modules /usr/local/lib/node_modules

RUN ln -s /usr/local/bin/node /usr/bin/node \
    && ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

WORKDIR /app
COPY server.js .

RUN npm init -y && npm install ws@8.19.0

EXPOSE 8004
CMD ["node", "server.js", "--port", "8004"]