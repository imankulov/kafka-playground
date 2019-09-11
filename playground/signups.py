"""
Stream of signups. Demonstrates how to use simple aggregation with tables
"""
import asyncio as aio
import datetime

import faust
from faker import Faker
from faust import Record

app = faust.App(
    "signups",
    broker="kafka://kafka1",
    key_serializer="raw",
    value_serializer="json",
    store="rocksdb://",
)
fake = Faker()


class Profile(Record):
    username: str
    name: str
    sex: str
    address: str
    mail: str
    birthdate: datetime.datetime

    @classmethod
    def random(cls):
        return cls(**fake.simple_profile())


topic_signups = app.topic("signups", retention=3600, internal=True, value_type=Profile)

signups_per_letter = app.Table("signups_per_letter", default=int)
signups_per_10s = app.Table("signups_per_10", default=int).hopping(
    size=10, step=5, expires=300
)


@app.task
async def signups_generator():
    """
    Generate signups partitioning them by username first letter
    """
    while True:
        profile = Profile.random()
        await topic_signups.send(value=profile, key=profile.username[0])
        await aio.sleep(1)


@app.agent(topic_signups)
async def signups_counter(profiles: faust.Stream):
    """
    Count the number of signups by first letter.
    """
    async for profile in profiles:  # type: Profile
        signups_per_letter[profile.username[0]] += 1
        signups_per_10s[profile.username[0]] += 1
