My Kafka playground
===================

Start it up
-----------

To start all the services, run:

```
docker-compose up
```

This will start three zookeeper instances, and the first zookeeper instance
will expose its port as 127.0.0.1:2181.

It will also start two Kafka instances. First instance will expose
its port as 127.0.0.1:9092 and the second one will expose it as
127.0.0.1:9093.


Managing it
-----------

There's a command manage.py, sort of our playground-specific Makefile. It
depends on `click` Python library at the moment.

Install all dependencies with pipenv

```
pipenv install
```

Then run a command with `pipenv run ./manage.py [command]`. At the moment
there's only one available command: the command to open command line Zookeeper
client.

```
pipenv run ./manage.py zkcli
```
