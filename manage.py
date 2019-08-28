#!/usr/bin/env python
import os
import click


@click.group()
def cli():
    pass


@cli.command()
def zkcli():
    _exec("docker-compose exec zoo1 ./bin/zkCli.sh")


def _exec(string):
    chunks = string.split()
    os.execlp(chunks[0], *chunks)


if __name__ == "__main__":
    cli()
