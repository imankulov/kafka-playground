FROM openjdk:8-jre-slim

ENV KAFKA_BROKER_ID=0 \
    KAFKA_DEFAULT_REPLICATION_FACTOR=2 \
    KAFKA_NUM_PARTITIONS=4 \
    KAFKA_ALLOW_AUTO_CREATE_TOPICS=true \
    KAFKA_ZOOKEEPER_CONNECT=zoo1:2181,zoo2:2181,zoo3:2181/kafka \
    KAFKA_LOG_DIRS=/kafka-logs

# Add a user with an explicit UID/GID and create necessary directories
RUN set -eux; \
    groupadd -r kafka --gid=1000; \
    useradd -r -g kafka --uid=1000 kafka; \
    mkdir -p "$KAFKA_LOG_DIRS"; \
    chown kafka:kafka "$KAFKA_LOG_DIRS"

# Install required packges
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    gosu \
    netcat \
    wget; \
    rm -rf /var/lib/apt/lists/*


ARG SHORT_DISTRO_NAME=2.3.0
ARG DISTRO_NAME=kafka_2.12-2.3.0

# Download Apache Kafka, untar and clean up
RUN set -eux; \
    wget -q "http://mirrors.up.pt/pub/apache/kafka/${SHORT_DISTRO_NAME}/${DISTRO_NAME}.tgz"; \
    tar -zxf "$DISTRO_NAME.tgz"; \
    rm -rf "$DISTRO_NAME.tgz"; \
    chown -R kafka:kafka "/$DISTRO_NAME"

WORKDIR $DISTRO_NAME
VOLUME ["$KAFKA_LOG_DIRS"]

EXPOSE 9092

ENV PATH=$PATH:/$DISTRO_NAME/bin

USER kafka
CMD kafka-server-start.sh config/server.properties \
    --override broker.id=${KAFKA_BROKER_ID} \
    --override default.replication.factor=${KAFKA_DEFAULT_REPLICATION_FACTOR} \
    --override num.partitions=${KAFKA_NUM_PARTITIONS} \
    --override allow.auto.create.topics=${KAFKA_ALLOW_AUTO_CREATE_TOPICS} \
    --override log.dirs=${KAFKA_LOG_DIRS} \
    --override zookeeper.connect=${KAFKA_ZOOKEEPER_CONNECT}
