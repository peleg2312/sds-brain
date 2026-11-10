---
name: sg-connectivity
description: Diagnose StorageGRID S3 connectivity - DNS, load balancer endpoint, HA group, certificate, the path from client to storage service. Use for "cannot connect to StorageGRID", "S3 endpoint unreachable", "load balancer endpoint", "HA group failover", "connection refused or timed out on the grid", "gateway node".
---
# StorageGRID S3 connectivity and load-balancer path

Read-only (rule 1). Scope: grid, application path, UTC interval; the exact FQDN, port, TLS hostname, endpoint type and
release from `knowledge/environment.md`. No scanning of grid addresses.

## Trace the path
1. Write the real route: client resolver -> VIP / load balancer -> StorageGRID endpoint -> storage service (an
   external proxy only if the inventory has one). Compare the application's hostname / port / trust with the intended
   client connection values.
2. Endpoint settings: protocol, port, binding mode, tenant restrictions, certificate name and expiry, HA group.
   Reaching an Admin Node does not show that the S3 endpoint is reachable.
3. HA group: current roles; correlate a role transition with the failure interval. The backup member of an
   active-backup group carries no normal traffic. Compare request distribution across the active load-balancing
   nodes on the existing charts.
4. Network observations for that path: DNS answer, route / interface, connection establishment, certificate
   validation, loss / retransmissions (host side: skill `linux-network-path`). The management network is not the
   application path.

Library (use the installed version's product): "configuring client connections", "configuring load balancer
endpoints", "monitoring load balancing operations", "summary: IP addresses and ports for client connections".

## Do not bypass the path
Load-balancer connections and direct connections to storage nodes are documented separately; the direct ports are not
a recommended workaround. A direct-node comparison changes the failure domain: only as an approved diagnostic plan
the user runs.

For one approved metadata-only request, match the client's timestamp and status with the endpoint access log; keep the
source node and request ID. A TLS failure happens before S3 authorization (skill `s3-signature-tls`).

## Not here
DNS, certificates, routes, HA priority, endpoint bindings, firewall rules.

## Result
The last layer confirmed working and the first one failing or unconfirmed; which of DNS, transport, TLS, endpoint
binding, HA, request distribution or backend service the evidence points to; the exact next read.
