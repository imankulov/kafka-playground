import datetime
import time

from confluent_kafka import Producer

# More on different options for producer
# https://kafka.apache.org/documentation/#producerconfigs
PRODUCER_CONFIG = {
    "bootstrap.servers": "kafka1:9092,kafka2:9092",
    "client.id": "playground",
}
producer = Producer(PRODUCER_CONFIG)


def send_timestamps(p: Producer, topic: str, message_count: int = 10, delay: int = 1):
    """
    Send timestamps to client
    """
    for i in range(message_count):
        message = datetime.datetime.utcnow().isoformat().encode("utf-8")

        # Trigger any available delivery report callbacks from previous produce() calls
        p.poll(0)

        # Asynchronously produce a message, the delivery report callback
        # will be triggered from poll() above, or flush() below, when the message has
        # been successfully delivered or failed permanently.
        p.produce(topic, message, callback=delivery_report)
        time.sleep(delay)

    # Wait for any outstanding messages to be delivered and delivery report
    # callbacks to be triggered.
    print("Flushing everything")
    p.flush(1)


def delivery_report(err, msg):
    """
    Called once for each message produced to indicate delivery result.

    Triggered by poll() or flush().
    """
    if err is not None:
        print("Message delivery failed: {}".format(err))
    else:
        print("Message delivered to {} [{}]".format(msg.topic(), msg.partition()))
