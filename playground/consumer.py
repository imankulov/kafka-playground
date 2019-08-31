from confluent_kafka import Consumer


COMSUMER_CONFIG = {
    "bootstrap.servers": "kafka1:9092,kafka2:9092",
    "group.id": "playground",
    "auto.offset.reset": "earliest",
}
consumer = Consumer(COMSUMER_CONFIG)


def consume(c, *topic_list):
    c.subscribe(list(topic_list))
    while True:
        msg = c.poll(1.0)

        if msg is None:
            continue
        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            continue

        print("Received message: {}".format(msg.value().decode("utf-8")))

    c.close()
