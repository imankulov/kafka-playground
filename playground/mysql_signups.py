#!/usr/bin/env python
import itertools
import time

import click
import sqlalchemy as sa
from faker import Faker
from sqlalchemy import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

fake = Faker()
engine = sa.create_engine("mysql+pymysql://root@mysql/playground?charset=utf8mb4")

Session = sessionmaker(bind=engine)
Base = declarative_base(bind=engine)


class Profile(Base):
    __tablename__ = "profiles"
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, index=True, server_default=func.now())
    username = sa.Column(sa.String(length=500), index=True)
    name = sa.Column(sa.String(length=500))
    email = sa.Column(sa.String(length=500), index=True)
    birthdate = sa.Column(sa.Date, index=True)

    def __repr__(self):
        return f"Profile(username={self.username}, email={self.email})"

    @classmethod
    def random(cls):
        profile = fake.simple_profile()
        return Profile(
            username=profile["username"],
            name=profile["name"],
            email=profile["mail"],
            birthdate=profile["birthdate"],
        )


def create_random_profiles(max=None, delay=1):
    Profile.metadata.create_all()
    sess = Session()
    for i in itertools.count():
        if max is not None and i >= max:
            break
        profile = Profile.random()
        sess.add(profile)
        sess.commit()
        print(profile)
        time.sleep(delay)
    sess.close()


if __name__ == "__main__":

    @click.command()
    @click.option("-m", "--max", type=int, default=None)
    @click.option("-d", "--delay", type=float, default=1.0)
    def command(max, delay):
        create_random_profiles(max, delay)

    command()
