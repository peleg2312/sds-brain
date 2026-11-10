---
name: linux-network-path
description: Triage the network path of a RHEL storage host - interfaces, routes, bonds, NIC errors, DNS, time sync, MTU - for S3, RGW-to-RADOS, inter-OSD or management traffic. Use for "network problem between hosts", "packet loss", "retransmits", "MTU", "bond", "clock skew", "DNS resolves differently", "timeout from one host only".
---
# RHEL storage network and endpoint path

Read-only (rule 1). Scope: cluster, host, destination, direction, protocol, port, failure interval. Which path: S3
client, RGW-to-RADOS, inter-OSD, or management / monitoring? Is the endpoint a load balancer, a daemon address or a
DNS alias? A request that works from a workstation proves nothing about the affected host.

## Local state (on the affected host)
```bash
ip -brief address; ip route show; ip -s link
nmcli device status; nmcli connection show --active
ss -s
chronyc tracking; chronyc sources -v
ethtool -i <iface>; ethtool -S <iface>
```
`<iface>` is an interface seen on this host. Lifetime error counters do not show errors now: take two bounded samples
and compare. Hardware counters need the NIC / driver documentation. Bonds: the bond's own status, and its members
against switch-side evidence. These outputs show internal topology: keep them out of shared notes.

## Follow the evidence
| Pattern | Next read-only question |
|---|---|
| A name resolves differently across clients | which resolver, search path and answer did each use? |
| Timeout from one source only | which route, interface, firewall and load-balancer path applies there? |
| TLS handshake failure | which chain, SNI hostname and protocol policy were presented? (`s3-signature-tls`) |
| Bursts of retransmits or errors | do host and switch counters move in the same UTC interval? |
| Signature errors or monitor clock warnings | is time synchronized on the hosts involved? |
| Large transfers fail, small requests work | MTU / path limits, proxy limits, or simply different operations? |

Clusters do not all share ports, VLANs, MTUs or NICs: compare this cluster's design with what is observed.

## Active checks
DNS queries, TCP / TLS handshakes and HTTP HEAD still create traffic: one endpoint, bounded, only on an authorized
path. No subnet scans, broad packet captures, endless polling or skipping certificate verification.

## Not here
Bouncing a bond, restarting NetworkManager, flushing rules, changing MTU / offloads / addressing / DNS.

## Result
The failing path, where it was observed, timestamps, the unresolved layer. Switch-side questions go to the network
owner with a precise path and time window.
