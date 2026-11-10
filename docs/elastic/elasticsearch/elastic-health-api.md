# Elasticsearch cluster health API

Show more

Use

to navigate results,
ENTER
to select one,
ESC
to close

Type in any word to easily find the endpoint, property or group of operations you are looking for.

## Get the cluster health status Generally available; Added in 1.3.0

Ask AI

- View as Markdown

- Copy as Markdown

GET

/_cluster/health/{index}

Api key auth

Basic auth

Bearer auth

All methods and paths for this operation:

GET
/_cluster/health

GET
/_cluster/health/{index}

You can also use the API to get the health status of only specified data streams and indices.
For data streams, the API retrieves the health status of the stream’s backing indices.

The cluster health status is: green, yellow or red.
On the shard level, a red status indicates that the specific shard is not allocated in the cluster. Yellow means that the primary shard is allocated but replicas are not. Green means that all shards are allocated.
The index level status is controlled by the worst shard status.

One of the main benefits of the API is the ability to wait until the cluster reaches a certain high watermark health level.
The cluster status is controlled by the worst index status.

### Required authorization

- Cluster privileges: monitor,manage

#### Path parameters

- index

string | array[string]
Required

A comma-separated list of data streams, indices, and index aliases that limit the request.
Wildcard expressions (*) are supported.
To target all data streams and indices in a cluster, omit this parameter or use _all or *.

#### Query parameters

- expand_wildcards

Expand wildcard expression to concrete indices that are open, closed or both.

Supported values include:

- all: Match any data stream or index, including hidden ones.

- open: Match open, non-hidden indices. Also matches any non-hidden data stream.

- closed: Match closed, non-hidden indices. Also matches any non-hidden data stream. Data streams cannot be closed.

- hidden: Match hidden data streams and hidden indices. Must be combined with open, closed, or both.

- none: Wildcard expressions are not accepted.

Default value is all.

- level

string

Return health information at a specific level of detail.

Default value is cluster.

- local

boolean

If true, retrieve information from the local node only.
If false, retrieve information from the master node.

Default value is false.

- master_timeout

string

The period to wait for a connection to the master node.
If no response is received before the timeout expires, the request fails and returns an error.

Default value is 30s.

- timeout

string

The period to wait for a response.
If no response is received before the timeout expires, the request fails and returns an error.

Default value is 30s.

- wait_for_active_shards

Wait for the specified number of active shards.
Use all to wait for all shards in the cluster to be active.
Use 0 to not wait.

Default value is 0.

- wait_for_events

string

Wait until all currently queued events with the given priority are processed.

Values are immediate, urgent, high, normal, low, or languid.

- wait_for_nodes

string | number

Wait until the specified number (N) of nodes is available.
It also accepts >=N, <=N, >N and <N.
Alternatively, use the notations ge(N), le(N), gt(N), and lt(N).

- wait_for_no_initializing_shards

boolean

Wait (until the timeout expires) for the cluster to have no shard initializations.
If false, the request does not wait for initializing shards.

Default value is false.

- wait_for_no_relocating_shards

boolean

Wait (until the timeout expires) for the cluster to have no shard relocations.
If false, the request not wait for relocating shards.

Default value is false.

- wait_for_status

string

Wait (until the timeout expires) for the cluster to reach a specific health status (or a better status).
A green status is better than yellow and yellow is better than red.
By default, the request does not wait for a particular status.

Supported values include:

- green (or GREEN): All shards are assigned.

- yellow (or YELLOW): All primary shards are assigned, but one or more replica shards are unassigned. If a node in the cluster fails, some data could be unavailable until that node is repaired.

- red (or RED): One or more primary shards are unassigned, so some data is unavailable. This can occur briefly during cluster startup as primary shards are assigned.

- unknown

- unavailable

Values are green, GREEN, yellow, YELLOW, red, RED, unknown, or unavailable.

### Responses

- 200

application/json

Hide response attributes
Show response attributes
object

- active_primary_shards

number
Required

The number of active primary shards.

- active_shards

number
Required

The total number of active primary and replica shards.

- active_shards_percent

string

The ratio of active shards in the cluster expressed as a string formatted percentage.

- active_shards_percent_as_number

number
Required

The ratio of active shards in the cluster expressed as a percentage.

- cluster_name

string
Required

The name of the cluster.

- delayed_unassigned_shards

number
Required

The number of shards whose allocation has been delayed by the timeout settings.

- indices

object

Hide indices attribute
Show indices attribute
object

- *

object
Additional properties

Hide * attributes
Show * attributes
object

- active_primary_shards

number
Required

- active_shards

number
Required

- initializing_shards

number
Required

- number_of_replicas

number
Required

- number_of_shards

number
Required

- relocating_shards

number
Required

- shards

object

Hide shards attribute
Show shards attribute
object

- *

object
Additional properties

Hide * attributes
Show * attributes
object

- active_shards

number
Required

- initializing_shards

number
Required

- primary_active

boolean
Required

- relocating_shards

number
Required

- status

string
Required

Supported values include:

- green (or GREEN): All shards are assigned.

- yellow (or YELLOW): All primary shards are assigned, but one or more replica shards are unassigned. If a node in the cluster fails, some data could be unavailable until that node is repaired.

- red (or RED): One or more primary shards are unassigned, so some data is unavailable. This can occur briefly during cluster startup as primary shards are assigned.

- unknown

- unavailable

Values are green, GREEN, yellow, YELLOW, red, RED, unknown, or unavailable.

- unassigned_shards

number
Required

- unassigned_primary_shards

number
Required

- status

string
Required

Supported values include:

- green (or GREEN): All shards are assigned.

- yellow (or YELLOW): All primary shards are assigned, but one or more replica shards are unassigned. If a node in the cluster fails, some data could be unavailable until that node is repaired.

- red (or RED): One or more primary shards are unassigned, so some data is unavailable. This can occur briefly during cluster startup as primary shards are assigned.

- unknown

- unavailable

Values are green, GREEN, yellow, YELLOW, red, RED, unknown, or unavailable.

- unassigned_shards

number
Required

- unassigned_primary_shards

number
Required

- initializing_shards

number
Required

The number of shards that are under initialization.

- number_of_data_nodes

number
Required

The number of nodes that are dedicated data nodes.

- number_of_in_flight_fetch

number
Required

The number of unfinished fetches.

- number_of_nodes

number
Required

The number of nodes within the cluster.

- number_of_pending_tasks

number
Required

The number of cluster-level changes that have not yet been executed.

- relocating_shards

number
Required

The number of shards that are under relocation.

- status

string
Required

Supported values include:

- green (or GREEN): All shards are assigned.

- yellow (or YELLOW): All primary shards are assigned, but one or more replica shards are unassigned. If a node in the cluster fails, some data could be unavailable until that node is repaired.

- red (or RED): One or more primary shards are unassigned, so some data is unavailable. This can occur briefly during cluster startup as primary shards are assigned.

- unknown

- unavailable

Values are green, GREEN, yellow, YELLOW, red, RED, unknown, or unavailable.

- task_max_waiting_in_queue

string

The time since the earliest initiated task is waiting for being performed.

External documentation

- task_max_waiting_in_queue_millis

number
Required

The time expressed in milliseconds since the earliest initiated task is waiting for being performed.

- timed_out

boolean
Required

If false the response returned within the period of time that is specified by the timeout parameter (30s by default)

- unassigned_primary_shards

number
Required

The number of primary shards that are not allocated.

- unassigned_shards

number
Required

The number of shards that are not allocated.

- 408

application/json

Hide response attributes
Show response attributes
object

- active_primary_shards

number
Required

The number of active primary shards.

- active_shards

number
Required

The total number of active primary and replica shards.

- active_shards_percent

string

The ratio of active shards in the cluster expressed as a string formatted percentage.

- active_shards_percent_as_number

number
Required

The ratio of active shards in the cluster expressed as a percentage.

- cluster_name

string
Required

The name of the cluster.

- delayed_unassigned_shards

number
Required

The number of shards whose allocation has been delayed by the timeout settings.

- indices

object

Hide indices attribute
Show indices attribute
object

- *

object
Additional properties

Hide * attributes
Show * attributes
object

- active_primary_shards

number
Required

- active_shards

number
Required

- initializing_shards

number
Required

- number_of_replicas

number
Required

- number_of_shards

number
Required

- relocating_shards

number
Required

- shards

object

Hide shards attribute
Show shards attribute
object

- *

object
Additional properties

Hide * attributes
Show * attributes
object

- active_shards

number
Required

- initializing_shards

number
Required

- primary_active

boolean
Required

- relocating_shards

number
Required

- status

string
Required

Supported values include:

- green (or GREEN): All shards are assigned.

- yellow (or YELLOW): All primary shards are assigned, but one or more replica shards are unassigned. If a node in the cluster fails, some data could be unavailable until that node is repaired.

- red (or RED): One or more primary shards are unassigned, so some data is unavailable. This can occur briefly during cluster startup as primary shards are assigned.

- unknown

- unavailable

Values are green, GREEN, yellow, YELLOW, red, RED, unknown, or unavailable.

- unassigned_shards

number
Required

- unassigned_primary_shards

number
Required

- status

string
Required

Supported values include:

- green (or GREEN): All shards are assigned.

- yellow (or YELLOW): All primary shards are assigned, but one or more replica shards are unassigned. If a node in the cluster fails, some data could be unavailable until that node is repaired.

- red (or RED): One or more primary shards are unassigned, so some data is unavailable. This can occur briefly during cluster startup as primary shards are assigned.

- unknown

- unavailable

Values are green, GREEN, yellow, YELLOW, red, RED, unknown, or unavailable.

- unassigned_shards

number
Required

- unassigned_primary_shards

number
Required

- initializing_shards

number
Required

The number of shards that are under initialization.

- number_of_data_nodes

number
Required

The number of nodes that are dedicated data nodes.

- number_of_in_flight_fetch

number
Required

The number of unfinished fetches.

- number_of_nodes

number
Required

The number of nodes within the cluster.

- number_of_pending_tasks

number
Required

The number of cluster-level changes that have not yet been executed.

- relocating_shards

number
Required

The number of shards that are under relocation.

- status

string
Required

Supported values include:

- green (or GREEN): All shards are assigned.

- yellow (or YELLOW): All primary shards are assigned, but one or more replica shards are unassigned. If a node in the cluster fails, some data could be unavailable until that node is repaired.

- red (or RED): One or more primary shards are unassigned, so some data is unavailable. This can occur briefly during cluster startup as primary shards are assigned.

- unknown

- unavailable

Values are green, GREEN, yellow, YELLOW, red, RED, unknown, or unavailable.

- task_max_waiting_in_queue

string

The time since the earliest initiated task is waiting for being performed.

External documentation

- task_max_waiting_in_queue_millis

number
Required

The time expressed in milliseconds since the earliest initiated task is waiting for being performed.

- timed_out

boolean
Required

If false the response returned within the period of time that is specified by the timeout parameter (30s by default)

- unassigned_primary_shards

number
Required

The number of primary shards that are not allocated.

- unassigned_shards

number
Required

The number of shards that are not allocated.

```
GET _cluster/health
```

```
resp = client.cluster.health()
```

```
const response = await client.cluster.health();
```

```
response = client.cluster.health
```

```
$resp = $client->cluster()->health();
```

```
curl -X GET -H "Authorization: ApiKey $ELASTIC_API_KEY" "$ELASTICSEARCH_URL/_cluster/health"
```

```
var response = await client.Cluster.HealthAsync();
```

```
client.cluster().health(h -> h);
```

A successful response from `GET _cluster/health`. It is the health status of a quiet single node cluster with a single index with one shard and one replica.

```
{
  "cluster_name" : "testcluster",
  "status" : "yellow",
  "timed_out" : false,
  "number_of_nodes" : 1,
  "number_of_data_nodes" : 1,
  "active_primary_shards" : 1,
  "active_shards" : 1,
  "relocating_shards" : 0,
  "initializing_shards" : 0,
  "unassigned_shards" : 1,
  "delayed_unassigned_shards": 0,
  "number_of_pending_tasks" : 0,
  "number_of_in_flight_fetch": 0,
  "task_max_waiting_in_queue_millis": 0,
  "active_shards_percent_as_number": 50.0
}
```
