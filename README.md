My Kafka playground
===================

Start it up
-----------

To start all the services, run:

```
docker-compose up -d
```

This will start three zookeeper instances, and the first zookeeper instance
will expose its port as 127.0.0.1:2181.

It will also start two Kafka instances. First instance will expose
its port as 127.0.0.1:9092 and the second one will expose it as
127.0.0.1:9093.

Wrappers
--------

There are wrappers for most command-line Kafka-related utilities. They are
stored in a "wrappers" directory and what they do is they simply run the
binary with the same name on the kafka1 host.

You can add them to your session PATH

```
PATH=$PATH:$PWD/wrappers
```

One example. That's how you can see the list of Kafka topics

```
kafka-topics.sh --zookeeper=zoo1:2181 --list
```


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

Kafka and Zookeeper
-------------------

Run zookeeper shell with `pipenv run zk-shell 127.0.0.1:2181`. Move to
directory "kafka" and look around.

Get the list of active brokers.

```
(CONNECTED [127.0.0.1:2181]) /kafka> tree brokers
.
├── ids
│   ├── 1
│   ├── 2
├── topics
├── seqid

(CONNECTED [127.0.0.1:2181]) /kafka> get brokers/ids/1
{"listener_security_protocol_map":{"PLAINTEXT":"PLAINTEXT"},"endpoints":["PLAINTEXT://1b9aa4ca7e24:9092"],"jmx_port":-1,"host":"1b9aa4ca7e24","timestamp":"1567061408756","port":9092,"version":4}
```

Each broker creates an ephemeral note `broker/ids/<id>` which will be
automatically removed as soon as Zookeeper loses connection with Kafka server.

See who acts as the controller.

```
(CONNECTED [127.0.0.1:2181]) /kafka> get controller
{"version":1,"brokerid":2,"timestamp":"1567061407902"}

(CONNECTED [127.0.0.1:2181]) /kafka> get controller_epoch
2
```

Stop the Kafka server who is the controller at the moment (in my case it's the
host with ID 2):

```
docker-compose stop kafka2
```

Shortly afterwards broker 2 disappears from the list of brokers:

```
(CONNECTED [127.0.0.1:2181]) /kafka> tree brokers
.
├── ids
│   ├── 1
├── topics
├── seqid
```

Also, a new controller was re-elected. Notice that epoch number has also
been updated. We have a broker with ID 1, and epoch is updated from 2 to three.

```
(CONNECTED [127.0.0.1:2181]) /kafka> get controller
{"version":1,"brokerid":1,"timestamp":"1567061694914"}
(CONNECTED [127.0.0.1:2181]) /kafka> get controller_epoch
3
```

Restarting kafka2 doesn't update the controller.

```
docker-compose up -d kafka2
```
