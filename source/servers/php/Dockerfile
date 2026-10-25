FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# 1. DEPENDENCIES
RUN apt-get update && apt-get install -y \
    wget build-essential \
    pkg-config autoconf bison re2c libxml2-dev \
    libsqlite3-dev libssl-dev zlib1g-dev \
    libffi-dev libonig-dev libzip-dev \
    openssl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

# PHP VERSION
ENV PHP_VERSION=8.3.30

# 2. PHP BUILD
RUN wget https://www.php.net/distributions/php-${PHP_VERSION}.tar.gz \
    && tar -xvf php-${PHP_VERSION}.tar.gz \
    && cd php-${PHP_VERSION} \
    && ./configure \
    --prefix=/usr/local \
    --with-config-file-path=/usr/local/etc/php \
    --enable-mbstring \
    --with-openssl \
    --with-zlib \
    --enable-sockets \
    --enable-pcntl \
    && make -j$(nproc) \
    && make install \
    && mkdir -p /usr/local/etc/php \
    && cp php.ini-production /usr/local/etc/php/php.ini \
    && cd .. && rm -rf php-${PHP_VERSION}*

# 3. SWOOLE BUILD
RUN wget https://github.com/swoole/swoole-src/archive/v6.1.6.tar.gz \
    && tar -zxf v6.1.6.tar.gz \
    && cd swoole-src-6.1.6 \
    && phpize \
    && ./configure \
    --enable-openssl \
    --enable-sockets \
    --enable-http2 \
    && make -j$(nproc) \
    && make install \
    && cd .. && rm -rf swoole-src-6.1.6* v6.1.6.tar.gz \
    && echo "extension=swoole.so" >> /usr/local/etc/php/php.ini

RUN php --ri swoole

WORKDIR /app
COPY server.php .

EXPOSE 8005
CMD ["php", "server.php", "--port=8005"]