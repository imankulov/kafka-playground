FROM python:3

# Install required packages
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends \
    libsnappy-dev \
    liblz4-dev \
    librocksdb-dev; \
    rm -rf /var/lib/apt/lists/*;

# Add a user with an explicit UID/GID
RUN set -eux; \
    groupadd client --gid=1000; \
    useradd -m -g client --uid=1000 client; \
    mkdir -p /app/playground; \
    chown -R client:client /app;

# Act as user from the /app directory
USER client
WORKDIR /app

# Install packages with pip into a virtual environment
COPY requirements.txt /tmp/requirements.txt
RUN set -eux; \
    python -m venv ./env; \
    ./env/bin/pip install -r /tmp/requirements.txt

# Prepare environment
ENV PATH=/app/env/bin:/usr/local/bin:/usr/bin:/bin

# - /app/playground will be mapped to ./playground
# - /home/client will be mapped to ./client-home
# We will start working from /app and will import everything as
# "from playground import something", and client-home will be used mostly to
# keep bash and IPython history
VOLUME ["/home/client", "/app/playground"]
CMD tail -f /dev/null
