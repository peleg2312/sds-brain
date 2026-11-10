# Grafana dashboard sharing and export

Documentation
Grafana documentation
Visualize data
Dashboards
Sharing

Grafana Cloud

Enterprise

Open source

# Share dashboards and panels

Note: Looking for prebuilt Grafana dashboards? Check out our full library of dashboards and more →

Grafana enables you to share dashboards and panels with other users within your organization and in certain situations, publicly on the web. You can share using:

- Direct links with users in and outside of your organization

- Snapshots

- Embeds

- PDFs

- PNG image files

- JSON files

- Reports

- Library panels

You must have an authorized viewer permission to see an image rendered by a direct link. The same permission is also required to view embedded links unless you have anonymous access permission enabled for your Grafana instance.

Note

Anonymous access permission is not available in Grafana Cloud. This feature is only supported for Grafana Enterprise and Grafana Open Source.

## Share dashboards

You can share dashboards in the following ways:

- Internally with a link

- Externally with anyone or specific people

- As a report

- As a snapshot

- As a PDF export

- As a JSON file export

- As an image export

When you share a dashboard externally as a link or by email, those dashboards are included in a list of your shared dashboards. To view the list and manage these dashboards, navigate to Dashboards > Shared dashboards.

Note

If you change a dashboard, ensure that you save the changes before sharing.

### Share an internal link

To share a customized, direct link to your dashboard within your organization, follow these steps:

- Click Dashboards in the main menu.

- Click the dashboard you want to share.

- Click the Share drop-down list in the top-right corner and select Share internally.

- (Optional) In the Share internally drawer that opens, set the following options:

- Lock time range - Change the current relative time range to an absolute time range. This option is enabled by default.

- Shorten link - Shorten the dashboard link. This option is enabled by default.

- Select the theme for the dashboard. Choose from Current, Dark, or Light.

- Click Copy link.

- Send the copied link to a Grafana user with authorization to view the link.

- Click the X at the top-right corner to close the share drawer.

#### Quick-share an internal link

After you’ve customized an internal link, you can share it quickly by following these steps:

- Click Dashboards in the main menu.

- Click the dashboard you want to share.

- Click the Share button, not the drop-down list icon, to copy a shortened link.

This link has any customizations, like time range locking or theme, that you’ve previously set. These are stored in the browser scope.

### Share an external link

Externally shared dashboards allow you to share your Grafana dashboard with anyone. This is useful when you want to make your dashboard available to the world without requiring access to your Grafana organization.

Learn how to configure and manage externally shared dashboards in
Externally shared dashboards.

### Schedule a report

Note

This feature is only available on Grafana Enterprise.

To share your dashboard as a report, follow these steps:

- Click Dashboards in the main menu.

- Click the dashboard you want to share.

- Click the Share drop-down list in the top-right corner and select Schedule a report.

- Configure the report.

- Depending on your schedule settings, you’ll have different options at this step. Click either Schedule send or Send now.

You can also save the report as a draft.

To manage your reports, navigate to Dashboards > Reporting > Reports.

### Share a snapshot

A dashboard snapshot publicly shares a dashboard while removing sensitive data such as queries and panel links, leaving only visible metrics and series names. Anyone with the link can access the snapshot.

You can publish snapshots to your local instance or to snapshots.raintank.io. The latter is a free service provided by Grafana Labs that enables you to publish dashboard snapshots to an external Grafana instance. Anyone with the link can view it. You can set an expiration time if you want the snapshot removed after a certain time period.

Note

The snapshots.raintank.io option is disabled by default in Grafana Cloud. You can update your config file to enable this functionality.

To see the other snapshots shared from your organization, navigate to Dashboards > Snapshots in the main menu.

To share your dashboard with anyone as a snapshot, follow these steps:

- Click Dashboards in the main menu.

- Click the dashboard you want to share.

- Click the Share drop-down list in the top-right corner and select Share snapshot.

- In the Share snapshot drawer that opens, enter a descriptive title for the snapshot in the Snapshot name field.

- Select one of the following expiration options for the snapshot:

- 1 Hour

- 1 Day

- 1 Week

- Never

- Click Publish snapshot or Publish to snapshots.raintank.io.

Grafana generates the link of the snapshot. Note that you can’t publish dashboard snapshots containing custom panels to snapshot.raintank.io.

- Click Copy link, and share it either within your organization or publicly on the web.

- Click the X at the top-right corner to close the share drawer.

#### Delete a dashboard snapshot

To delete dashboard snapshots, follow these steps:

- Navigate to Dashboards > Snapshots in the main menu.

- To confirm which snapshot you’re about to delete, click View on the snapshot row.

The URLs for panel and dashboard snapshots from the same dashboard look similar and viewing them first can help you distinguish them.

- Click the red x next to the snapshot that you want to delete.

The snapshot is immediately deleted. You might need to clear your browser cache or use a private or incognito browser to confirm this.

## Export dashboards

In addition to sharing dashboards as links, reports, and snapshots, you can export them as PDFs or JSON files.

### Export a dashboard as PDF

Note

This feature is only available on Grafana Enterprise.

To export a dashboard in its current state as a PDF, follow these steps:

- Click Dashboards in the main menu.

- Open the dashboard you want to export.

- Click the Export drop-down in the toolbar and select Export as PDF.

- In the Export dashboard PDF drawer that opens, select either Landscape or Portrait for the PDF orientation.

- Select either Grid or Simple for the PDF layout.

- Set the Zoom level; zoom in to enlarge text, or zoom out to see more data (like table columns) per panel.

- Click Generate PDF.

The PDF opens in another tab where you can download it.

- Click the X at the top-right corner to close the share drawer.

### Export a dashboard as code

Export a Grafana JSON file that contains everything you need, including layout, variables, styles, data sources, queries, and so on, so that you can later import the dashboard.
To export a JSON file, follow these steps:

- Click Dashboards in the main menu.

- Open the dashboard you want to export.

- In the toolbar, click the Export icon and select Export as code.

The Export dashboard drawer opens.

- (Optional) Click Advanced options to expand the section, and then make the following selections:

- Model: Choose from Classic or V2 Resource

- Format: For the V2 Resource only, choose from JSON or YAML

- (Optional) Toggle the Share dashboard with another instance switch to remove details specific to your Grafana instance.

- Click Download file or Copy to clipboard.

- Paste the JSON in another location.

- Click the X at the top-right corner to close the share drawer.

Note

To publish a dashboard to the Grafana community catalog, you must export it using the Classic model.
For steps on how to add dashboards to the Grafana community catalog, refer to the Publish a community dashboard.

### Export a dashboard as an image

Note

You must have the
Grafana Image Renderer service configured to export a dashboard as an image.

To export a dashboard in its current state as a PNG image file, follow these steps:

- Click Dashboards in the main menu.

- Open the dashboard you want to export.

- Click the Export drop-down list in the toolbar and select Export as image.

The Export as image drawer opens.

- Click Generate image.

The image preview is displayed.

- Click Download image.

- Click the X at the top-right corner to close the share drawer.

The generated image reflects how the dashboard appears in your browser.
To change it, make changes to the dashboard or browser, like zooming in or out or resizing.

## Publish a community dashboard

You can share dashboards publicly by publishing them to the Grafana community catalog.
Published dashboards are available for anyone to discover and import.

To publish a dashboard to the community catalog, follow these steps:

- Export your dashboard using the Classic model.

- Go to Grafana and sign in to your Grafana Cloud account.

- Navigate to My dashboards and click Upload dashboard.

- Upload the Classic JSON file you exported from Grafana.

- Fill in the required metadata fields, then click Save and Publish.

Note

After you select Save and Publish, it might take several hours for the public dashboard page to become available.
During this time, the dashboard link might generate a 404 error.
If the dashboard is still unavailable the following day, contact Grafana Support.

### Metadata updates for published dashboards

After you’ve published a dashboard, the catalog shows a Submit button instead of Save and Publish.
Clicking Submit saves and publishes your metadata changes, including screenshots, a logo, and the README content.

## Share panels

You can share a panels in the following ways:

- Internally with a link

- As an embed

- As a snapshot

Note

If you change a panel, ensure that you save the changes before sharing.

### Share an internal link

To share a personalized, direct link to your panel within your organization, follow these steps:

- Hover over any part of the panel you want to share to display the actions menu on the top right corner.

- Click the menu and select Share link.

- (Optional) In the Link settings drawer that opens, set the following options:

- Lock time range - Change the current relative time range to an absolute time range. This option is enabled by default.

- Shorten link - Shorten the panel link. This option is disabled by default.

- Select the theme for the dashboard. Choose from Current, Dark, or Light.

- Click Copy link.

- Send the copied link to a Grafana user with authorization to view it.

- (Optional) To
generate an image of the panel as a PNG file, customize the image settings:

- Width - In pixels. The default and minimum is 1000.

- Height - In pixels. The default and minimum is 500.

- Scale factor - The default is 1.

There are minimums and maximums for width, height, and scale factor in the image renderer
configuration options that you can customize if needed.

- (Optional) Click Generate image to see a preview of the panel image.

- (Optional) Click Download image.

- Send the copied image to a Grafana user with authorization to view it.

- Click the X at the top-right corner to close the share drawer.

#### Query string parameters for server-side rendered images

When you click Generate image in the panel link settings, Grafana generates a PNG image of the panel with the following default parameters:

Parameter | Description

width | Width in pixels. Default and minimum is 1000.

height | Height in pixels. Default and minimum is 500.

tz | Timezone in the format UTC%2BHH%3AMM where HH and MM are offset in hours and minutes after UTC.

timeout | Number of seconds. The timeout can be increased if the query for the panel needs more than the default 30 seconds.

scale | Numeric value to configure device scale factor. Default is 1. Use a higher value to produce more detailed images (higher DPI).

Note

The image renderer enforces minimum dimensions of 1000px for width and 500px for height. You can customize these minimums in self-managed Grafana installations through the
image renderer configuration. In Grafana Cloud, the configuration is managed by Grafana and can’t be modified. If you encounter size-related errors when rendering images using the API, ensure your dimensions meet the minimum requirements.

You can also update these parameters in the
image rendering configuration.

The following example shows a link to a server-side rendered PNG:

Bash

```
https://play.grafana.org/render/d-solo/ktMs4D6Mk?from=2024-09-03T11:55:44.442Z&to=2024-09-03T17:55:44.442Z&panelId=panel-13&width=1000&height=500&tz=UTC
```

### Share an embed

You can share a panel by embedding it on another website using an iframe. Users must be signed into Grafana to view the panel unless you have anonymous access permission enabled for your Grafana instance.

Note

Panel embedding and anonymous access permissions are not available in Grafana Cloud, even for panels in
externally shared dashboards. These capabilities are only supported in Grafana Enterprise and Grafana Open Source.

To create a panel that can be embedded, follow these steps:

- Hover over any part of the panel you want to share to display the actions menu on the top-right corner.

- Click the menu and select Share embed.

The Share embed drawer opens.

- (Optional) Toggle the Lock time range switch to set whether the panel uses the current relative time range or an absolute time range. This option is enabled by default.

- Select the theme for the dashboard. Choose from Current, Dark, or Light.

- (Optional) Make any changes to the HTML that you need.

- Click Copy to clipboard.

- Paste the HTML code into your website code.

- Click the X at the top-right corner to close the share drawer.

Here’s an example of what the HTML code might look like:

HTML

```
<iframe
  src="https://snapshots.raintank.io/dashboard-solo/snapshot/y7zwi2bZ7FcoTlB93WN7yWO4aMiz3pZb?from=1493369923321&to=1493377123321&panelId=4"
  width="650"
  height="300"
  frameborder="0"
></iframe>
```

The result is an interactive Grafana visualization embedded in an iframe.

### Share a snapshot

A panel snapshot shares an interactive panel publicly while removing sensitive data such as queries and panel links, leaving only visible metrics and series names. Anyone with the link can access the snapshot.

You can publish snapshots to your local instance or to snapshots.raintank.io. The latter is a free service provided by Grafana Labs that enables you to publish dashboard snapshots to an external Grafana instance. Anyone with the link can view it. You can set an expiration time if you want the snapshot removed after a certain time period.

Note

The snapshots.raintank.io option is disabled by default in Grafana Cloud. You can update your config file to enable this functionality.

To see the other snapshots shared from your organization, navigate to Dashboards > Snapshots in the main menu.

To share your panel with anyone as a snapshot, follow these steps:

- Hover over any part of the panel you want to share to display the actions menu on the top-right corner.

- Click the menu and select Share snapshot.

- In the Share snapshot drawer that opens, enter a descriptive title for the snapshot in the Snapshot name field.

- Select one of the following expiration options for the snapshot:

- 1 Hour

- 1 Day

- 1 Week

- Never

- Click Publish snapshot or Publish to snapshots.raintank.io.

Grafana generates the link of the snapshot. Note that you can’t publish snapshots that include custom panels to snapshot.raintank.io.

- Click Copy link, and share it either within your organization or publicly on the web.

- Click the X at the top-right corner to close the share drawer.

#### Delete a panel snapshot

To delete panel snapshots, follow these steps:

- Navigate to Dashboards > Snapshots in the main menu.

- To confirm which snapshot you’re about to delete, click View on the snapshot row.

The URLs for panel and dashboard snapshots from the same dashboard look similar and viewing them first can help you distinguish them.

- Click the red x next to the snapshot URL that you want to delete.

The snapshot is immediately deleted. You may need to clear your browser cache or use a private or incognito browser to confirm this.

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
