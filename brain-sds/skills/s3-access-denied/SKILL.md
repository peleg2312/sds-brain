---
name: s3-access-denied
description: Investigate an S3 403 / AccessDenied on Ceph RGW or StorageGRID without changing permissions - find which layer denies. Use for "AccessDenied", "403 on S3", "permission denied on bucket", "cannot read object", "bucket policy not working".
---
# S3 access denied

Read-only (rule 1). Scope: backend (RGW or StorageGRID), cluster / grid, principal, bucket, operation, UTC interval,
product and SDK / CLI versions. Get the original HTTP status, provider error code and request ID before any retry.
Credentials stay in the user's profile: never ask anyone to paste a secret key (rule 4).

AWS documents many 403 layers (bucket / IAM policy, ownership, encryption, endpoint, organization policy):
investigate only the layers that exist on this backend. StorageGRID has its own error set
(`search_docs("error responses", product="storagegrid-119")`, or the installed version).

## 1. Metadata-only probes (user runs them, with their profile; one approved bucket and a non-sensitive object)
```bash
aws --profile <profile> --endpoint-url <endpoint> --region <region> --cli-connect-timeout 5 --cli-read-timeout 10 \
  s3api head-bucket --bucket <bucket>
aws --profile <profile> --endpoint-url <endpoint> --region <region> --cli-connect-timeout 5 --cli-read-timeout 10 \
  s3api head-object --bucket <bucket> --key <key> --query '{Length:ContentLength,Modified:LastModified,Version:VersionId}'
```
Both HEAD calls return generic errors. A missing object can answer 403 when the caller lacks list permission: a 403
does not prove the object exists, nor that encryption is at fault.

## 2. Policy evidence
Read only the statements that match the action and resource (a redacted excerpt from the user is fine). An explicit
deny overrides an allow. On RGW also: is the user suspended, who owns the bucket / object, ACLs
(`rgw-request-triage` step 3 shows the user without its keys). On StorageGRID: tenant group policy and bucket policy,
and the tenant's permissions (`knowledge/notes/storagegrid-versions-apis.md`).

Encryption: establish how this backend encrypts before talking about key permissions; AWS KMS rules are not
inherited by RGW or StorageGRID.

## Not here
Attaching admin policies, making a bucket public, rotating keys, bypassing TLS, changing retention as a "test".

## Result
The failing action / resource / principal, the evidence for the denying layer, what is still uncertain. Propose the
narrowest correction only once the cause is identified, for the user to apply.
