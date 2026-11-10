# Grafana Prometheus data source

Documentation
Grafana documentation
Data sources
Prometheus

Grafana Cloud

Enterprise

Open source

Last reviewed: August 4, 2026

# Prometheus data source

Prometheus is an open source monitoring system and time series database that scrapes and stores metrics used for monitoring and alerting.

The Prometheus data source is preinstalled in Grafana, so you don’t need to install it manually. Write queries using PromQL in the query editor, or use
Metrics Drilldown to explore metrics without writing queries. The Prometheus data source also works with other projects that implement the Prometheus querying API, including Grafana Mimir and Thanos.

## Supported features

Feature | Supported

Metrics | Yes

Alerting | Yes

Annotations | Yes

Recording rules | Yes

Exemplars | Yes

## Get started

The following documents help you set up and use the Prometheus data source:

- Configure the Prometheus data source

- Prometheus query editor

- Template variables

- Annotations

- Alerting

- Troubleshooting

## Additional features

After you configure the Prometheus data source, you can:

- Use
Metrics Drilldown to browse and explore your Prometheus metrics without writing PromQL

- Use
Explore to query data without building a dashboard

- Add
transformations to manipulate query results

- Create
recorded queries for pre-aggregated data

- Save and reuse PromQL queries across dashboards, Explore, and annotations with
saved queries (available in Grafana Enterprise and Grafana Cloud)

- Build a wide variety of
visualizations

To see the Prometheus data source in action, explore this demo dashboard on Grafana Play:

Give it a try using Grafana Play

With Grafana Play, you can explore and see how it works, learning from practical examples to accelerate your development.
This feature can be seen on The Four Golden Signals.

Try it

## Cloud-managed Prometheus services

Note

In Grafana 13, the core Prometheus data source no longer supports SigV4 (AWS) or Azure AD authentication. These authentication methods have been migrated to dedicated plugins:

- Amazon Managed Service for Prometheus: Use the Amazon Managed Service for Prometheus data source. For migration details, refer to
AWS authentication (deprecated).

- Azure Monitor Managed Service for Prometheus: Use the Azure Monitor Managed Service for Prometheus data source. For migration details, refer to
Azure authentication (deprecated).

Existing data sources using these methods are automatically migrated on startup.

## Plugin updates

Grafana still ships with the Prometheus data source out of the box. It’s preinstalled in both Grafana OSS and Grafana Enterprise, so there’s nothing for you to install. Starting with Grafana v13.2, it’s packaged as a standalone plugin rather than built into the Grafana codebase, which means you can update the plugin as needed without waiting for a Grafana release. By default, Grafana checks the plugin catalog and installs the latest version on each server restart.

To adjust this behavior:

- Opt out of auto-updates: Set preinstall_auto_update to false in your
configuration file.

- Update manually: Update at any time from the Administration > Plugins page without restarting Grafana.

The standalone plugin requires Grafana 12.3.0 or later. The Prometheus data source bundled with Grafana 13.1 and earlier continues to work as before, and those versions aren’t affected by this change.

Users running Grafana 12.3.x through 13.1.x can install the standalone plugin from the plugin catalog if they want the latest features before upgrading to Grafana 13.2. To use the standalone plugin with Grafana 12.3.x through 13.1.x, add the following to your
configuration file:

ini

```
[plugin.prometheus]
as_external = true

[plugins]
; Install the latest version on startup:
preinstall_sync = prometheus
; Or install a specific version:
; preinstall_sync = prometheus@<version>
```

## Query with the Grafana CLI

You can query this data source from the command line and from AI coding agents using the Grafana CLI, gcx. gcx gives you and your agent structured, terminal-based access to your Grafana data sources, which is useful for automation and agent-driven investigations.

gcx supports Grafana Cloud and Grafana OSS or Enterprise v12 and later. Before you query, install and authenticate gcx. Refer to the
gcx CLI documentation for installation, configuration, and the full command reference.

For example, to query your Prometheus data source, use the gcx datasources prometheus commands:

sh

```
# Run an instant PromQL query using an explicit data source UID
gcx datasources prometheus query -d <DATASOURCE_UID> 'up{job="grafana"}'

# Run a range query over the last hour
gcx datasources prometheus query -d <DATASOURCE_UID> 'rate(http_requests_total[5m])' --since 1h --step 1m

# List all labels, or the values for a single label
gcx datasources prometheus labels -d <DATASOURCE_UID>
gcx datasources prometheus labels -d <DATASOURCE_UID> --label job

# Get metadata, including the type and help text, for a metric
gcx datasources prometheus metadata -d <DATASOURCE_UID> --metric http_requests_total
```

Replace <DATASOURCE_UID> with the UID of your Prometheus data source. You can omit the -d flag when datasources.prometheus is configured in your gcx context. The same commands work with Prometheus-compatible data sources that gcx maps to this resolver, including Amazon Managed Service for Prometheus and other grafana-*prometheus-datasource flavors.

## Related resources

- What is Prometheus?

- Prometheus data model

- Getting started with Prometheus

- Grafana community forum

## Was this page helpful?

Suggest an edit in GitHub

Create a GitHub issue

Email docs@grafana.com

Help and support

Community

## Related resources from Grafana Labs

Additional helpful documentation, links, and articles:

Video

Intro to metrics with Grafana: Prometheus, Grafana Mimir, and beyond

In this webinar, we’ll go over challenges when scaling metrics systems, with a particular focus on Prometheus and Grafana Mimir.

Video

Scaling and securing your Prometheus metrics in Grafana Cloud

Learn how Grafana Cloud Metrics, powered by Grafana Mimir, overcomes Prometheus limitations with a fully managed, scalable service. Optimize cardinality, reduce costs, and scale seamlessly—no maintenance required.

Video

Grafana Cloud Adaptive Metrics: Reduce Prometheus high cardinality metrics

Learn how Grafana Cloud Adaptive Metrics helps you control metrics growth and reduce costs by identifying unused metrics.

Read this in Grafana Cloud

Is this page helpful?

On this page

Scroll for more
