# S3 incidents: the evidence to collect first

Before diagnosing a request, fix the scope: cluster or grid, backend (RGW or StorageGRID), release, tenant / account,
and a UTC time interval.

| Field | Why it matters |
|---|---|
| Operation, HTTP status, provider error code | Separates transport, authentication, authorization and service failure |
| Request / correlation ID and UTC timestamp | Joins client, load balancer, backend and monitoring evidence |
| Endpoint, SDK and version, addressing style | The path actually used |
| Object size and multipart stage | Request latency versus transfer / workload effects |
| Retry count and elapsed time | One slow operation versus repeated failed attempts |
| Principal and tenant | The authorization boundary |
| Version ID, when relevant | Current versus historical object state |

Keep the provider's error code: StorageGRID returns S3 errors plus its own responses, and the HTTP status alone is
incomplete (https://docs.netapp.com/us-en/storagegrid-119/s3/error-responses.html).

## Metadata-first probes
Use one approved bucket / object. `HeadObject` returns metadata without the body, but its error is generic and
depends on permissions; `HeadBucket` too. Neither proves existence, key validity or policy correctness. These are
AWS-documented behaviours: check the provider's implementation.

## Keep out of answers and notes
Object names, user metadata, tenant names, presigned URLs and signed headers can be sensitive. Return only the fields
the diagnosis needs. No unrestricted CLI debug output, no object payloads, no listing of every bucket or every user
as a default step.

For StorageGRID, take a bounded interval from the endpoint or audit logs; its log families separate management
requests, S3 endpoints and other services
(https://docs.netapp.com/us-en/storagegrid-119/monitor/logs-files-reference.html).

Missing permission or telemetry is a gap to report, not evidence that the service is healthy.
