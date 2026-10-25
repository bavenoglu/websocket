FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# 1. DEPENDENCIES
RUN apt-get update && apt-get install -y \
    wget build-essential \
    libssl-dev zlib1g-dev \
    libncurses5-dev libnss3-dev \
    libreadline-dev libffi-dev libsqlite3-dev libbz2-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

# 2. PYTHON VERSION
ENV PYTHON_VERSION=3.12.3

# 3. PYTHON BUILD
RUN wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz \
    && tar -xf Python-${PYTHON_VERSION}.tgz \
    && cd Python-${PYTHON_VERSION} \
    && ./configure --with-ensurepip=install \
    && make -j$(nproc) \
    && make install \
    && cd .. && rm -rf Python-${PYTHON_VERSION}*

WORKDIR /app
COPY server.py .

# 4. PACKAGE INSTALL
RUN pip3 install websockets==16.0 --break-system-packages

EXPOSE 8006
CMD ["python3", "server.py"]