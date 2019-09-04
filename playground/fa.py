"""
Faust playground.
"""
import faust
import asyncio as aio

mult = faust.App(
    "mult", broker="kafka://kafka1", value_serializer="raw", store="rocksdb://"
)

topic_x = mult.topic("x", partitions=10, replicas=2, retention=3600, internal=True)
topic_2x = mult.topic("2x", partitions=10, replicas=2, retention=3600, internal=True)


@mult.task
async def counter():
    value = 0
    while True:
        value += 1
        await aio.gather(topic_x.send(value=str(value)), aio.sleep(1))


@mult.agent(topic_x, sink=[topic_2x])
async def multiplier(messages: faust.Stream):
    async for message in messages:
        yield str(int(message) * 2)


@mult.agent(topic_2x)
async def logger(messages: faust.Stream):
    async for message in messages:
        print(message)
