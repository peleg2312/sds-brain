# Grafana Elasticsearch data source

Documentation
Grafana documentation
Data sources
Elasticsearch

Grafana Cloud

Enterprise

Open source

Last reviewed: August 10, 2026

# Elasticsearch data source

Elasticsearch is a search and analytics engine used for a variety of use cases. Grafana ships with the Elasticsearch data source preinstalled, so you can query and visualize logs or metrics stored in Elasticsearch, and annotate graphs with log events, without installing a plugin. The data source is packaged as a standalone plugin that you can update independently of Grafana releases. Refer to Plugin updates for details.

Note

If you use Amazon OpenSearch Service (the successor to Amazon Elasticsearch Service), use the OpenSearch data source instead.

## Key capabilities

The Elasticsearch data source supports:

- Metrics queries: Aggregate and visualize numeric data using bucket and metric aggregations.

- Log queries: Search, filter, and explore log data with Lucene query syntax.

- Raw DSL queries: Write native Elasticsearch Query DSL in Code mode.

- ES|QL queries: Query data using Elasticsearch’s pipe-based query language.

- Annotations: Overlay Elasticsearch events on your dashboard graphs.

- Alerting: Create alerts based on Elasticsearch query results.

## Before you begin

Before you configure the Elasticsearch data source, you need:

- An Elasticsearch instance (v7.17+, v8.x, or v9.x)

- Network access from Grafana to your Elasticsearch server

- Appropriate user credentials or API keys with read access

## Supported Elasticsearch versions

This data source supports these versions of Elasticsearch:

- ≥ v7.17

- v8.x

- v9.x

- Elastic Cloud Serverless

The Grafana maintenance policy for the Elasticsearch data source aligns with Elastic Product End of Life Dates. Grafana ensures proper functionality for supported versions only. If you use an EOL version of Elasticsearch, you can still run queries, but the query builder displays a warning. Grafana doesn’t guarantee functionality or provide fixes for EOL versions.

## Get started

The following documentation helps you set up and use the Elasticsearch data source:

- Configure the data source

- Query editor

- Template variables

- Annotations

- Alerting

- Troubleshooting

## Plugin updates

Starting with Grafana v13.0, the Elasticsearch data source is a standalone plugin, preinstalled in both Grafana OSS and Enterprise. This enables more frequent updates independent of Grafana releases. Grafana automatically checks the plugin catalog and installs the latest version on each server restart.

Note

Plugins are automatically updated in Grafana Cloud.

To adjust this behavior:

- Opt out of auto-updates: Set preinstall_auto_update to false in your
configuration file.

- Update manually: Update at any time from Plugins and data > Plugins without restarting Grafana.

The standalone plugin requires Grafana 12.2.0 or later. The Elasticsearch data source bundled with Grafana 12.1 and earlier continues to work as before. These versions are unaffected by the externalization.

Users running Grafana 12.2.x through 12.4.x can install the standalone plugin from the plugin catalog if they want the latest features before upgrading to Grafana 13.0. To use the standalone plugin with Grafana 12.2.x through 12.4.x, add the following to your
configuration file:

ini

```
[plugin.elasticsearch]
as_external = true

[plugins]
; Install the latest version on startup:
preinstall_sync = elasticsearch
; Or install a specific version:
; preinstall_sync = elasticsearch@<version>
```

## Additional resources

After you have configured the Elasticsearch data source, you can:

- Use
Explore to run user-written queries against your Elasticsearch data.

- Configure and use
template variables for dynamic dashboards.

- Add
Transformations to process query results.

- Build dashboards to visualize your Elasticsearch data.

## Query with the Grafana CLI

You can query this data source from the command line and from AI coding agents using the Grafana CLI, gcx. gcx gives you and your agent structured, terminal-based access to your Grafana data sources, which is useful for automation and agent-driven investigations.

gcx supports Grafana Cloud and Grafana OSS or Enterprise v12 and later. Before you query, install and authenticate gcx. Refer to the
gcx CLI documentation for installation, configuration, and the full command reference.

For example, to explore and query your Elasticsearch data source, use the gcx datasources elasticsearch commands:

sh

```
# List the indices and fields available to the data source
gcx datasources elasticsearch list-indices -d <DATASOURCE_UID>
gcx datasources elasticsearch list-fields -d <DATASOURCE_UID> --index grafana-logs

# Search documents with a Lucene query
gcx datasources elasticsearch query -d <DATASOURCE_UID> 'app:frontend AND level:error' --since 1h

# Aggregate documents over time, split into series by a field
gcx datasources elasticsearch metrics -d <DATASOURCE_UID> 'level:error' --group-by app.keyword --since 6h
```

Replace <DATASOURCE_UID> with the UID of your Elasticsearch data source. You can omit the -d flag when datasources.elasticsearch is configured in your gcx context. The query command searches documents with Lucene syntax (add --mode logs for a newest-first logs view), metrics runs a time-bucketed aggregation (--agg, --field, --group-by), and list-indices and list-fields help you discover index patterns and field names.

## Related data sources

- OpenSearch - For Amazon OpenSearch Service.

- Loki - The Grafana log aggregation system.

## Was this page helpful?

Suggest an edit in GitHub

Create a GitHub issue

Email docs@grafana.com

Help and support

Community

## Related resources from Grafana Labs

Additional helpful documentation, links, and articles:

Video

Getting started with managing your metrics, logs, and traces using Grafana

In this webinar, we’ll demo how to get started using the LGTM Stack: Loki for logs, Grafana for visualization, Tempo for traces, and Mimir for metrics.

Video

Getting started with Grafana dashboard design

In this webinar, you'll learn how to design stylish and easily accessible Grafana dashboards that tell a story.

Video

Building advanced Grafana dashboards

In this webinar, we’ll demo how to build and format Grafana dashboards.

Read this in Grafana Cloud

Is this page helpful?

On this page

Scroll for more
