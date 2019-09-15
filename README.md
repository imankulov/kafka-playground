My Kafka playground
===================

Start it up
-----------

To start all the services, run:

```
docker-compose up -d
```

It will start following

- Three zookeeper instances, and the first zookeeper instance
  will expose its port as 127.0.0.1:2181.

- Two Kafka instances. They listen for the port 0.0.0.0:9092,
  none of them is exposed outside.

- One Kafka Connect instance exposing port 8083 to the main host.

- One MySQL instance to play with Debezium connector. You can get access
  to it with MySQL client as "mysql -h 127.0.0.1 -u root" without
  entering password (the password is empty).

- A "client" host with some pre-installed libraries.


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


Windowing
---------

[More about Windowing Faust](https://faust.readthedocs.io/en/latest/userguide/tables.html#windowing)

Everything is pretty much the same, except that the aggregation goes for two
parameters: key and time. In our case there is a table
"signups_per_10s" which aggregates signups for overlapping interval of
10 seconds.

Representation of data in the table.

```bash
$ ldb --db=signups-data/v1/tables/signups_per_10-0.db scan  | head

["k", [1568235160.0, 1568235169.9]] : 1
["k", [1568235165.0, 1568235174.9]] : 1
["k", [1568235170.0, 1568235179.9]] : 1
```

Representation of data in the stream

```bash
./wrappers/kafka-console-consumer.sh --bootstrap-server 127.0.0.1:9092 \
    --topic=signups-signups_per_10-changelog \
    --group=foo \
    --property print.key=true

["e", [1568235680.0, 1568235689.9]]     1
["e", [1568235685.0, 1568235694.9]]     1
["w", [1568235680.0, 1568235689.9]]     1
["w", [1568235685.0, 1568235694.9]]     1
["c", [1568235685.0, 1568235694.9]]     1
["c", [1568235690.0, 1568235699.9]]     1
["p", [1568235690.0, 1568235699.9]]     1
["p", [1568235695.0, 1568235704.9]]     1
["c", [1568235690.0, 1568235699.9]]     2
...
```

Note how each value is written twice, once per each overlapping key.


Kafka Connect
-------------

Start Kafka Connect with

```bash
docker-compose up connect
```

Perform queries to the service with Curl or Postman. You should see zero
connectors and following list of connector plugins

```json
[
    {
        "class": "io.debezium.connector.mysql.MySqlConnector",
        "type": "source",
        "version": "0.9.5.Final"
    },
    {
        "class": "org.apache.kafka.connect.file.FileStreamSinkConnector",
        "type": "sink",
        "version": "2.3.0"
    },
    {
        "class": "org.apache.kafka.connect.file.FileStreamSourceConnector",
        "type": "source",
        "version": "2.3.0"
    }
]
```

You can also see that once connect started, it created three new topics:

```bash
$ ./wrappers/kafka-topics.sh --bootstrap-server kafka1:9092 --describe --topic connect-configs
Topic:connect-configs   PartitionCount:1        ReplicationFactor:1     Configs:cleanup.policy=compact,segment.bytes=1073741824
```

```bash
$ ./wrappers/kafka-topics.sh --bootstrap-server kafka1:9092 --describe --topic connect-offsets
Topic:connect-offsets   PartitionCount:25       ReplicationFactor:1     Configs:cleanup.policy=compact,segment.bytes=1073741824
        Topic: connect-offsets  Partition: 0    Leader: 1       Replicas: 1     Isr: 1
        Topic: connect-offsets  Partition: 1    Leader: 2       Replicas: 2     Isr: 2
...
```

```bash
$ ./wrappers/kafka-topics.sh --bootstrap-server kafka1:9092 --describe --topic connect-status
Topic:connect-status    PartitionCount:5        ReplicationFactor:1     Configs:cleanup.policy=compact,segment.bytes=1073741824
        Topic: connect-status   Partition: 0    Leader: 2       Replicas: 2     Isr: 2
        Topic: connect-status   Partition: 1    Leader: 1       Replicas: 1     Isr: 1
...
```

Kafka Connect. MySQL connector
------------------------------


Make sure that you have binlogs enabled on the MySQL side. It should be
enabled here by default though.

```mysql
mysql> show variables like "%log_bin%";
+---------------------------------+-----------------------------+
| Variable_name                   | Value                       |
+---------------------------------+-----------------------------+
| log_bin                         | ON                          |
| log_bin_basename                | /var/lib/mysql/binlog       |
| log_bin_index                   | /var/lib/mysql/binlog.index |
| log_bin_trust_function_creators | OFF                         |
| log_bin_use_v1_row_events       | OFF                         |
| sql_log_bin                     | ON                          |
+---------------------------------+-----------------------------+
6 rows in set (0.00 sec)
```


```mysql
mysql> show variables like "%binlog%";
+------------------------------------------------+----------------------+
| Variable_name                                  | Value                |
+------------------------------------------------+----------------------+
...
| binlog_format                                  | ROW                  |
...
+------------------------------------------------+----------------------+
27 rows in set (0.01 sec)
```

Create a new user to connect to MySQL.

```bash
mysql -h 127.0.0.1 -u root
```

```mysql
CREATE USER 'debezium'@'%' IDENTIFIED WITH mysql_native_password BY 'password';
GRANT SELECT, RELOAD, SHOW DATABASES, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'debezium'@'%';
```

At the moment with MySQL 8.x you cannot use existing users and creating a new
user with "mysql_native_password" is essential. See the discussion in
https://github.com/shyiko/mysql-binlog-connector-java/issues/240.

Create a new database "playground"

```mysql
CREATE DATABASE playground DEFAULT CHARSET utf8mb4;
```

Run the MySQL signups script. The script will connect as root to MySQL server,
create there a new table "profiles" if necessary, and start adding record
to the table, one by one.

```bash
$ ./wrappers/mysql_signups.py
Profile(username=peggy06, email=ygreen@gmail.com)
Profile(username=brettrichards, email=sarahthompson@yahoo.com)
Profile(username=joseph29, email=hopkinsholly@yahoo.com)
```

It's time to create a new connector. You can use Postman requests
from https://documenter.getpostman.com/view/4176727/SVmsUf7n.

Get the list of connector plugins. You should get the `io.debezium.connector.mysql.MySqlConnector`
among them.

Get the list of connectors. It should be empty initially.

Before creating a connector start collecting logs from the connect instance.
If something goes wrong, you'll see it.

```bash
docker-compose logs -f --tail=0 connect
```

Then create a new connector. The connector should be successfully created. If
any problem occur, fix the issue and restart the connector with "Restart MySQL
connector" Postman command.

Explore the list of topics.

```bash
./wrappers/kafka-topics.sh --bootstrap-server kafka1:9092 --list
__consumer_offsets
connect-configs
connect-offsets
connect-status
dbhistory.playground
playground
playground.playground.profiles
...
```

The latest topic ("playground.playground.profiles") contains the live stream
of events from the database. Go ahead to consume that topic:

```bash
./wrappers/kafka-console-consumer.sh \
    --bootstrap-server 127.0.0.1:9092 \
    --topic=playground.playground.profiles \
    --group=foo \
    --property print.key=true \
    --from-beginning
```

Formatted key looks like this

```json
{
  "schema": {
    "type": "struct",
    "fields": [
      {
        "type": "int32",
        "optional": false,
        "field": "id"
      }
    ],
    "optional": false,
    "name": "playground.playground.profiles.Key"
  },
  "payload": {
    "id": 140
  }
}
```

And the value looks like this

```json
{
  "schema": {
    "type": "struct",
    "fields": [
      {
        "type": "struct",
        "fields": [
          {
            "type": "int32",
            "optional": false,
            "field": "id"
          },
          {
            "type": "int64",
            "optional": true,
            "name": "io.debezium.time.Timestamp",
            "version": 1,
            "default": 0,
            "field": "created"
          },
          {
            "type": "string",
            "optional": true,
            "field": "username"
          },
          {
            "type": "string",
            "optional": true,
            "field": "name"
          },
          {
            "type": "string",
            "optional": true,
            "field": "email"
          },
          {
            "type": "int32",
            "optional": true,
            "name": "io.debezium.time.Date",
            "version": 1,
            "field": "birthdate"
          }
        ],
        "optional": true,
        "name": "playground.playground.profiles.Value",
        "field": "before"
      },
      {
        "type": "struct",
        "fields": [
          {
            "type": "int32",
            "optional": false,
            "field": "id"
          },
          {
            "type": "int64",
            "optional": true,
            "name": "io.debezium.time.Timestamp",
            "version": 1,
            "default": 0,
            "field": "created"
          },
          {
            "type": "string",
            "optional": true,
            "field": "username"
          },
          {
            "type": "string",
            "optional": true,
            "field": "name"
          },
          {
            "type": "string",
            "optional": true,
            "field": "email"
          },
          {
            "type": "int32",
            "optional": true,
            "name": "io.debezium.time.Date",
            "version": 1,
            "field": "birthdate"
          }
        ],
        "optional": true,
        "name": "playground.playground.profiles.Value",
        "field": "after"
      },
      {
        "type": "struct",
        "fields": [
          {
            "type": "string",
            "optional": true,
            "field": "version"
          },
          {
            "type": "string",
            "optional": true,
            "field": "connector"
          },
          {
            "type": "string",
            "optional": false,
            "field": "name"
          },
          {
            "type": "int64",
            "optional": false,
            "field": "server_id"
          },
          {
            "type": "int64",
            "optional": false,
            "field": "ts_sec"
          },
          {
            "type": "string",
            "optional": true,
            "field": "gtid"
          },
          {
            "type": "string",
            "optional": false,
            "field": "file"
          },
          {
            "type": "int64",
            "optional": false,
            "field": "pos"
          },
          {
            "type": "int32",
            "optional": false,
            "field": "row"
          },
          {
            "type": "boolean",
            "optional": true,
            "default": false,
            "field": "snapshot"
          },
          {
            "type": "int64",
            "optional": true,
            "field": "thread"
          },
          {
            "type": "string",
            "optional": true,
            "field": "db"
          },
          {
            "type": "string",
            "optional": true,
            "field": "table"
          },
          {
            "type": "string",
            "optional": true,
            "field": "query"
          }
        ],
        "optional": false,
        "name": "io.debezium.connector.mysql.Source",
        "field": "source"
      },
      {
        "type": "string",
        "optional": false,
        "field": "op"
      },
      {
        "type": "int64",
        "optional": true,
        "field": "ts_ms"
      }
    ],
    "optional": false,
    "name": "playground.playground.profiles.Envelope"
  },
  "payload": {
    "before": null,
    "after": {
      "id": 140,
      "created": 1568540744000,
      "username": "coxanna",
      "name": "John Dixon",
      "email": "sheastephanie@yahoo.com",
      "birthdate": -15790
    },
    "source": {
      "version": "0.9.5.Final",
      "connector": "mysql",
      "name": "playground",
      "server_id": 1,
      "ts_sec": 1568540744,
      "gtid": null,
      "file": "binlog.000002",
      "pos": 54429,
      "row": 0,
      "snapshot": false,
      "thread": 18,
      "db": "playground",
      "table": "profiles",
      "query": null
    },
    "op": "c",
    "ts_ms": 1568540744870
  }
}
```

The output is large, but it's quite easy to understand and safe to parse.
Overall, it contains two top-level keys: payload and schema. The payload
contains three fields: "before", "after" and "source", and the "schema"
contains the schema for all three of them. Including schema in every payload
can be disabled with config options "key.converter.schemas.enable" and
"value.converter.schemas.enable".
