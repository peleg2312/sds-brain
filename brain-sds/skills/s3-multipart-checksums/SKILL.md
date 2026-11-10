---
name: s3-multipart-checksums
description: Diagnose multipart upload completion failures and checksum errors on RGW or StorageGRID - which stage failed, which algorithm, what the backend supports. Use for "InvalidPart", "BadDigest", "multipart upload fails", "CompleteMultipartUpload error", "checksum mismatch", "XAmzContentSHA256Mismatch", "unfinished uploads".
---
# Multipart completion and checksum errors

Read-only (rule 1): listing unfinished uploads is a read; aborting or completing one is a write for the user.

## 1. The failed stage
Backend, cluster / grid, bucket, object, UTC interval. Where did it fail: initiation, a part upload, part listing,
completion? SDK / CLI version, part size and count, retries, checksum algorithm, the relevant header names. Object
bodies, signed headers, encryption keys and full upload IDs stay out of notes.

An initiated upload stays until completed or aborted.

## 2. Bounded inventory (user runs it, with their profile and a narrow prefix)
```bash
aws --profile <profile> --endpoint-url <endpoint> --region <region> --cli-connect-timeout 5 --cli-read-timeout 10 \
  s3api list-multipart-uploads --bucket <bucket> --prefix <prefix> --max-uploads 20 --no-paginate \
  --query '{Truncated:IsTruncated,Uploads:Uploads[].{Key:Key,Started:Initiated}}'
```
One page only: `Truncated: true` means a sample. Object keys are customer data.

## 3. Match the implementation
- StorageGRID 11.9 added pre-calculated SHA-256 for selected object and multipart operations: read the exact
  operation's supported headers for the installed version (`search_docs("checksum multipart",
  product="storagegrid-119")`, and the "quick reference: supported S3 API requests" page). Not every AWS algorithm
  or streaming / trailer variant is supported.
- RGW: the S3 feature table of the matching release (`product="squid"` or `"reef"`), then the RHCS release notes.
- From the client's part list and completion manifest: missing or repeated parts, a different upload ID, an
  algorithm mismatch.
- An ETag is an opaque identifier unless the provider documents otherwise; it is not always a whole-object MD5.
- `InvalidPart`, `BadDigest` and other codes: read the provider's error reference, keep the failed stage.

## Result
The compatibility or client-state hypothesis the evidence supports, and the smallest next read. No abort,
completion, deletion, lifecycle edit or new upload from here.
