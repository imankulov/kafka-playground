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
kafka-topics.sh --zookeeper=zoo1:2181/kafka --list
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

Kafka brokers and Zookeeper
---------------------------

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


Kafka topics and Zookeeper
--------------------------

Topics and their configuration created by direct modifying of Zookeeper
keys.

Create a new Kafka topic.

```
kafka-topics.sh --zookeeper zoo1:2181/kafka --create \
    --replication-factor 2 --partitions 4 --topic playground
```

zk-shell will reflect the changes. A new structure topics/playground
will be added to kafka/brokers.

```
(CONNECTED [127.0.0.1:2181]) /> tree /kafka/brokers
.
├── ids
│   ├── 1
│   ├── 2
├── topics
│   ├── playground
│   │   ├── partitions
│   │   │   ├── 0
│   │   │   │   ├── state
│   │   │   ├── 1
│   │   │   │   ├── state
│   │   │   ├── 2
│   │   │   │   ├── state
│   │   │   ├── 3
│   │   │   │   ├── state
├── seqid
```

State of each partition stores the leadership information about the topic.
Here "isr" means "in-sync replicas". Leader is the broker who accepts writes
to a specific partition, and the rest of brokers are used for the replication.

```
(CONNECTED [127.0.0.1:2181]) /> cd kafka/brokers/topics/playground/partitions
(CONNECTED [127.0.0.1:2181]) /kafka/brokers/topics/playground/partitions> get 0/state
{"controller_epoch":7,"leader":2,"version":1,"leader_epoch":0,"isr":[2,1]}
(CONNECTED [127.0.0.1:2181]) /kafka/brokers/topics/playground/partitions> get 1/state
{"controller_epoch":7,"leader":1,"version":1,"leader_epoch":0,"isr":[1,2]}
(CONNECTED [127.0.0.1:2181]) /kafka/brokers/topics/playground/partitions> get 2/state
{"controller_epoch":7,"leader":2,"version":1,"leader_epoch":0,"isr":[2,1]}
(CONNECTED [127.0.0.1:2181]) /kafka/brokers/topics/playground/partitions> get 3/state
{"controller_epoch":7,"leader":1,"version":1,"leader_epoch":0,"isr":[1,2]}
```

Let's stop one Kafka server

```
docker-compose stop kafka2
```

Looks like a new leader for each partition was assigned. Number of in-sync
replicas has also been updated.

```
(CONNECTED [127.0.0.1:2181]) /kafka/brokers/topics/playground/partitions> get 0/state
{"controller_epoch":8,"leader":1,"version":1,"leader_epoch":2,"isr":[1]}
(CONNECTED [127.0.0.1:2181]) /kafka/brokers/topics/playground/partitions> get 1/state
{"controller_epoch":8,"leader":1,"version":1,"leader_epoch":1,"isr":[1]}
(CONNECTED [127.0.0.1:2181]) /kafka/brokers/topics/playground/partitions> get 2/state
{"controller_epoch":8,"leader":1,"version":1,"leader_epoch":2,"isr":[1]}
(CONNECTED [127.0.0.1:2181]) /kafka/brokers/topics/playground/partitions> get 3/state
{"controller_epoch":8,"leader":1,"version":1,"leader_epoch":1,"isr":[1]}
```

Restarting the server `docker-compose up -d kafka2` does not automatically update the
leader immediately, but will updated them after a while.


Kafka topics, partitions and files
----------------------------------

Let's see which files Kafka generated for our topic.

```
$ ls data/kafka1/kafka-logs/playground-*
data/kafka1/kafka-logs/playground-0:
00000000000000000000.index     00000000000000000000.log       00000000000000000000.timeindex leader-epoch-checkpoint

data/kafka1/kafka-logs/playground-1:
00000000000000000000.index     00000000000000000000.log       00000000000000000000.timeindex leader-epoch-checkpoint

data/kafka1/kafka-logs/playground-2:
00000000000000000000.index     00000000000000000000.log       00000000000000000000.timeindex leader-epoch-checkpoint

data/kafka1/kafka-logs/playground-3:
00000000000000000000.index     00000000000000000000.log       00000000000000000000.timeindex leader-epoch-checkpoint
```

As you can see, everything is organized around the hierarchy
"topic -> partitions -> segments". At the moment each partition has one segment,
represented by three files: log, index and timeindex.

Let's create a tiny topic with two partitions. Max segment size equals to
1 minute, and the total lifetime of messages in the topic is 10 minutes.


```
./wrappers/kafka-topics.sh --bootstrap-server kafka1:9092 --create --topic tiny \
    --partitions 2 \
    --replication-factor 2 \
    --config retention.ms=600000 \
    --config segment.ms=60000
```

Following command will start writing there messages, one per second.

```
./wrappers/kafka-verifiable-producer.sh \
    --broker-list 127.0.0.1:9092,kafka2:9092 --topic=tiny --throughput=1
```

From a different side, you can receive these messages with a console client

```
./wrappers/kafka-console-consumer.sh \
    --bootstrap-server 127.0.0.1:9092 --topic=tiny
```

Notice how Kafka creates a new file (segment) every minute, and if you wait
long enough (more than 10 minutes), you'll see how old sections start
disappearing.

```
cd data/kafka1/kafka-logs/tiny-0
ls -l -t *.log | nl
     1  -rw-r--r--  1 roman  staff   923 Aug 31 16:48 00000000000000000391.log
     2  -rw-r--r--  1 roman  staff  2130 Aug 31 16:47 00000000000000000361.log
     3  -rw-r--r--  1 roman  staff  2201 Aug 31 16:46 00000000000000000330.log
     4  -rw-r--r--  1 roman  staff  2130 Aug 31 16:45 00000000000000000300.log
     5  -rw-r--r--  1 roman  staff  2130 Aug 31 16:44 00000000000000000270.log
     6  -rw-r--r--  1 roman  staff  2130 Aug 31 16:43 00000000000000000240.log
     7  -rw-r--r--  1 roman  staff  2130 Aug 31 16:42 00000000000000000210.log
     8  -rw-r--r--  1 roman  staff  2130 Aug 31 16:41 00000000000000000180.log
     9  -rw-r--r--  1 roman  staff  2130 Aug 31 16:40 00000000000000000150.log
    10  -rw-r--r--  1 roman  staff  2130 Aug 31 16:39 00000000000000000120.log
    11  -rw-r--r--  1 roman  staff  2130 Aug 31 16:38 00000000000000000090.log
    12  -rw-r--r--  1 roman  staff  2130 Aug 31 16:37 00000000000000000060.log
```

Kafka consumers
---------------

If you want console consumer to keep reading from the point you stopped before
you need to explicitly assign a group to it.

```
./wrappers/kafka-console-consumer.sh \
    --bootstrap-server 127.0.0.1:9092 --topic=tiny --group=foo
```

Then you can stop the consumer and restart it again, and you'll see that it
"keep counting" from where it stopped before.

Start the second consumer with exactly the same command. If you run two
consumers, they will be automatically rebalanced and each of them
will consume only half of the topic (each will read messages from one partition,
it's called "owning partition").

Start the third consumer. Now, because we have three consumers and only two
partitions, one of the consumers will stay idle.

For the record, notice that as soon as you start consuming events a new topic
`__consumer_offsets` with 50 partitions will be created. It's used to keep
track of consumer last seen message.
