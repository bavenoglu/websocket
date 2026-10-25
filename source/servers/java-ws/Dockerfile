# --- 1. BUILD
FROM eclipse-temurin:25.0.1_8-jdk-noble AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y wget unzip

RUN wget -q https://services.gradle.org/distributions/gradle-9.3.0-bin.zip \
    && unzip gradle-9.3.0-bin.zip \
    && mv gradle-9.3.0 /opt/gradle \
    && rm gradle-9.3.0-bin.zip

ENV PATH="/opt/gradle/bin:${PATH}"

COPY build.gradle settings.gradle ./
COPY src ./src

RUN gradle build -x test --no-daemon

# --- 2. RUNTIME
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="${JAVA_HOME}/bin:${PATH}"

WORKDIR /app

COPY --from=builder /app/build/libs/*.jar server.jar

EXPOSE 8002
CMD ["java", "-jar", "server.jar", "--port=8002"]