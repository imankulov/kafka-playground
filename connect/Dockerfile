FROM imankulov/kafka:latest
ENV KAFKA_PLUGIN_PATH=/kafka-connectors

USER root
EXPOSE 8083

# Create Kafka Plugin directory
RUN set -eux; \
    mkdir -p "$KAFKA_PLUGIN_PATH" ; \
    chown kafka:kafka "$KAFKA_PLUGIN_PATH"

USER kafka

# Download Debezium MySQL connector
ARG DEBEZIUM_VERSION=0.9.5.Final
RUN set -eux; \
    wget -q "https://repo1.maven.org/maven2/io/debezium/debezium-connector-mysql/${DEBEZIUM_VERSION}/debezium-connector-mysql-${DEBEZIUM_VERSION}-plugin.tar.gz"; \
    tar -zxf "debezium-connector-mysql-${DEBEZIUM_VERSION}-plugin.tar.gz" -C "${KAFKA_PLUGIN_PATH}"; \
    rm -rf "debezium-connector-mysql-${DEBEZIUM_VERSION}-plugin.tar.gz"

# Copy custom config for Connect
COPY connect-distributed.properties config/connect-distributed.properties
CMD connect-distributed.sh config/connect-distributed.properties
