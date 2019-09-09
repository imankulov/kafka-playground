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

It will also start two Kafka instances. They listen for the port 0.0.0.0:9092,
none of them is exposed outside.

Also it will start a "client" host with some pre-installed libraries.


Wrappers
--------

There are wrappers for most command-line Kafka-related utilities. They are
stored in a "wrappers" directory and what they do is they simply run the
binary with the same name either on the "kafka1" host or on the "client" host.

One example. That's how you can see the list of Kafka topics

```
./wrappers/kafka-topics.sh --zookeeper=zoo1:2181/kafka --list
```

Kafka brokers and Zookeeper
---------------------------

Run zookeeper shell with `./wrappers/zk-shell zoo1`. Move to
directory "kafka" and look around.

Get the list of active brokers.

```
(CONNECTED [zoo1]) /kafka> tree brokers
.
├── ids
│   ├── 1
│   ├── 2
├── topics
├── seqid

(CONNECTED [zoo1]) /kafka> get brokers/ids/1
{"listener_security_protocol_map":{"PLAINTEXT":"PLAINTEXT"},"endpoints":["PLAINTEXT://1b9aa4ca7e24:9092"],"jmx_port":-1,"host":"1b9aa4ca7e24","timestamp":"1567061408756","port":9092,"version":4}
```

Each broker creates an ephemeral note `broker/ids/<id>` which will be
automatically removed as soon as Zookeeper loses connection with Kafka server.

See who acts as the controller.

```
(CONNECTED [zoo1]) /kafka> get controller
{"version":1,"brokerid":2,"timestamp":"1567061407902"}

(CONNECTED [zoo1]) /kafka> get controller_epoch
2
```

Stop the Kafka server who is the controller at the moment (in my case it's the
host with ID 2):

```
docker-compose stop kafka2
```

Shortly afterwards broker 2 disappears from the list of brokers:

```
(CONNECTED [zoo1]) /kafka> tree brokers
.
├── ids
│   ├── 1
├── topics
├── seqid
```

Also, a new controller was re-elected. Notice that epoch number has also
been updated. We have a broker with ID 1, and epoch is updated from 2 to three.

```
(CONNECTED [zoo1]) /kafka> get controller
{"version":1,"brokerid":1,"timestamp":"1567061694914"}
(CONNECTED [zoo1]) /kafka> get controller_epoch
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
(CONNECTED [zoo1]) /> tree /kafka/brokers
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
(CONNECTED [zoo1]) /> cd kafka/brokers/topics/playground/partitions
(CONNECTED [zoo1]) /kafka/brokers/topics/playground/partitions> get 0/state
{"controller_epoch":7,"leader":2,"version":1,"leader_epoch":0,"isr":[2,1]}
(CONNECTED [zoo1]) /kafka/brokers/topics/playground/partitions> get 1/state
{"controller_epoch":7,"leader":1,"version":1,"leader_epoch":0,"isr":[1,2]}
(CONNECTED [zoo1]) /kafka/brokers/topics/playground/partitions> get 2/state
{"controller_epoch":7,"leader":2,"version":1,"leader_epoch":0,"isr":[2,1]}
(CONNECTED [zoo1]) /kafka/brokers/topics/playground/partitions> get 3/state
{"controller_epoch":7,"leader":1,"version":1,"leader_epoch":0,"isr":[1,2]}
```

Let's stop one Kafka server

```
docker-compose stop kafka2
```

Looks like a new leader for each partition was assigned. Number of in-sync
replicas has also been updated.

```
(CONNECTED [zoo1]) /kafka/brokers/topics/playground/partitions> get 0/state
{"controller_epoch":8,"leader":1,"version":1,"leader_epoch":2,"isr":[1]}
(CONNECTED [zoo1]) /kafka/brokers/topics/playground/partitions> get 1/state
{"controller_epoch":8,"leader":1,"version":1,"leader_epoch":1,"isr":[1]}
(CONNECTED [zoo1]) /kafka/brokers/topics/playground/partitions> get 2/state
{"controller_epoch":8,"leader":1,"version":1,"leader_epoch":2,"isr":[1]}
(CONNECTED [zoo1]) /kafka/brokers/topics/playground/partitions> get 3/state
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

Kafka and Python
----------------

Exposing Kafka from Docker instances to the main host is a non-trivial task,
because they register themselves in Zookeepers under their canonical name,
which are only available from inside containers. In principle, looks like
it's doable, but requires careful configuration of "listeners" and
"advertised.listeners" broker options, and it's boring and non-intuitive.

So that's why there's another host "client" where we install everything.
You can open IPython console to run Python producer and consumer

```
$ ./wrappers/ipython

In [1]: from playground import *

In [2]: send_timestamps(producer, 'tiny')
Message delivered to tiny [0]
Message delivered to tiny [0]
...
```

And to read the messages

```
$ ./wrappers/ipython

In [1]: from playground import *

In [2]: consume(consumer, 'tiny')
Received message: 2019-08-31T17:26:13.812724
Received message: 2019-08-31T17:26:14.814812
...
```

Kafka and Faust
---------------

Faust is a stream processing library, porting the ideas from Kafka Streams
to Python. It's asyncio-based, and whenever I need to brush up my asyncio
knowledge, I go to
[Python & Async Simplified](https://www.aeracode.org/2018/02/19/python-async-simplified/)
blog post

[Faust Documentation →](https://faust.readthedocs.io/en/latest/)

On automatic topic creation
---------------------------

It's not quite clear from Faust documentation when topic are created and which
parameters are applied to them.

As I learned, topic are only created explicitly when you mark them as "internal"
with the flag. For example, this way topic will be created with 10 partitions.
All other parameters will be taken from Kafka broker configuration.

```python
topic_foo = app.topic("foo", partitions=10, internal=True)
```

For external topic (internal flag is not set), topic will be created
automatically with the settings, defined in broker configs.

```python
topic_bar = app.topic("bar", partitions=10)
```

For this case the parameter "partitions" will be quite misleadingly ignored,
and topic will be created with as many partitions as defined in `num.partitions`
broker settings.

Single-event processing. Multiplier
-----------------------------------

In the file [multiplier.py](playground/multiplier.py) defined a "multiplier"
application. The application uses two topics, x and 2x. Counter sends
incrementing integers to Kafka topic "x". Multiplier reads them, multiply by
two and writes to the topic "2x". Logger prints them down.

Run Faust worker

```bash
$ ./wrappers/faust -A playground.multiplier:app worker
┌ƒaµS† v1.7.4─┬──────────────────────────────────────────┐
│ id          │ mult                                     │
...
│ appdir      │ /app/mult-data/v1                        │
└─────────────┴──────────────────────────────────────────┘
[2019-09-04 22:39:34,667: WARNING]: b'2'
[2019-09-04 22:39:35,645: WARNING]: b'4'
[2019-09-04 22:39:36,647: WARNING]: b'6'
[2019-09-04 22:39:37,667: WARNING]: b'8'
...
```

To make sure that messages actually appear in Kafka topics, you can also
run a console consumers.

```bash
./wrappers/kafka-console-consumer.sh --bootstrap-server 127.0.0.1:9092 --topic=2x --group=foo
```

If you start two console consumers, you'll see how messages re-distributed between them.


Custom types. Simple aggregation with tables. Table changelog
-------------------------------------------------------------

File `signups.py` shows how structured messages are sent over the channel
and how simple aggregation with tables work. To make sure we can use
aggregation with tables, we need to partition records deterministically.
In our case we partition them by the first letter of the login.

Start the worker.

```bash
./wrappers/faust -A playground.signups:app worker
```

Observe the contents of the topic "signups"

```bash
./wrappers/kafka-console-consumer.sh --bootstrap-server 127.0.0.1:9092 --topic=signups --group=foo
{"username": "kevinross", "name": "Mary Sanders", "sex": "F", "address": "USS Campbell\nFPO AA 64409", "mail": "richard87@gmail.com", "birthdate": "2011-07-10T00:00:00", "__faust": {"ns": "playground.signups.Profile"}}
{"username": "andrew20", "name": "Susan Michael", "sex": "F", "address": "41187 Anderson Brooks Suite 703\nPort Josephmouth, WI 70930", "mail": "sandra25@gmail.com", "birthdate": "1939-07-20T00:00:00", "__faust": {"ns": "playground.signups.Profile"}}
{"username": "janet38", "name": "Dana Yang", "sex": "F", "address": "981 Kimberly Summit Suite 611\nMelissaport, KS 46828", "mail": "meredith80@hotmail.com", "birthdate": "1955-07-31T00:00:00", "__faust": {"ns": "playground.signups.Profile"}}
...
```

We use `--group` to consume all partitions of the topic.

The table will generate a changelog. The name of the changelog is
"<app_name>-<table_name>-changelog", or "signups-signups_per_letter-changelog"
in our case. Observe the contents of the changelog.

```bash
./wrappers/kafka-console-consumer.sh --bootstrap-server 127.0.0.1:9092 --topic=signups-signups_per_letter-changelog --group=foo --property print.key=true
"j"     79
"r"     35
"n"     17
"r"     36
"o"     6
"r"     37
...
```

Note that we use "print.key" property to show the letters (that's how
we aggregate).

We can also observe the content of the tables, stored in the client host.

```bash
./wrapper/bash
```

Tables are created in the filesystem, and partitioned by the same number of
partitions as topics themselves.

```bash
$ ls signups-data/v1/tables/
signups_per_letter-0.db
signups_per_letter-1.db
...
signups_per_letter-7.db
```

We can dump tables contents.

```bash
$ ldb --db=signups-data/v1/tables/signups_per_letter-0.db scan
"k" : 92
"l" : 70
"m" : 125
__faust : 286

$ ldb --db=signups-data/v1/tables/signups_per_letter-1.db scan
"d" : 91
"t" : 75
"v" : 37
__faust : 202
```
