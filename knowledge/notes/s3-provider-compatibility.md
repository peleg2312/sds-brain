# AWS S3, Ceph RGW and StorageGRID: where they differ

AWS is the protocol reference. Every answer names the real backend: an AWS page cannot establish support in RGW or
StorageGRID.

| Concern | AWS reference | StorageGRID | Ceph RGW |
|---|---|---|---|
| Consistency | Strong read-after-write and list consistency | 11.8 / 11.9 default "read-after-new-write" treats overwrites, metadata updates and deletes differently | Check the installed release and the local / multisite context |
| Checksums | Depends on API, algorithm, SDK version, headers | 11.9 adds pre-calculated SHA-256 for selected operations | Not every algorithm or trailer format is implemented |
| STS / session policy | AWS IAM / STS services | 12.0 adds AssumeRole and session policies | Verify RGW STS and identity configuration separately |
| API coverage | Includes AWS-only features | The versioned supported-operations table and its caveats | The matching RHCS / IBM / upstream RGW documentation |
| Encryption | SSE-KMS involves AWS KMS | Verify the grid's encryption options | Verify the actual key-management integration |

## How to answer a compatibility question
Record the full tuple: product build, operation, request headers, SDK / CLI version, signature method, endpoint
style, encryption mode, bucket and object settings. Classify the answer as documented, observed here, or unverified.
A successful basic upload proves nothing about multipart checksums, retention, lifecycle, policy conditions or
conditional writes. Tests that write belong in an approved test bucket, run by the user.

## Ownership
StorageGRID 11.9: objects in a bucket are owned by the bucket owner
(https://docs.netapp.com/us-en/storagegrid-119/s3/operations-on-objects.html). Do not bring an AWS cross-account
ownership explanation into a StorageGRID incident.

Unknown support is stated precisely ("CRC32C trailer validation on this StorageGRID build is not verified"), never as
"S3 compatible, therefore supported".

Sources: AWS consistency model; StorageGRID consistency (storagegrid-118 / -119: s3/consistency-controls); StorageGRID S3
changes per release (s3/index); StorageGRID operation reference (s3/quick-reference-support-for-aws-apis).
