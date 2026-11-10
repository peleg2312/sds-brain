# S3: versioning, lifecycle and retention are separate things

| Dimension | Evidence to collect | Do not infer |
|---|---|---|
| Versioning | Bucket state and the exact object version | that the current-key view shows every historical version |
| Lifecycle | Existing rules, filters, ages, status | that a policy denial prevents lifecycle actions |
| Object retention | Retention mode and retain-until date of that version | that the same setting prevents new versions |
| Legal hold | Hold status of that version | that an expiry date removes a legal hold |

- **Versioning**: a normal delete in a versioned bucket can add a delete marker instead of removing the old version.
  Check version ID and delete-marker state before reporting object loss or reclaimed capacity.
- **Lifecycle**: rules can transition or expire existing objects too, and a bucket policy does not stop lifecycle
  deletions or transitions. A policy change is not proof that lifecycle is off.
- **Object Lock**: protects object versions through retention and legal holds. A legal hold stays until removed and
  is separate from a retention period. Protected versions coexist with newer versions and delete markers.
- **StorageGRID** has its own Object Lock and ILM requirements: read the version-specific pages
  (https://docs.netapp.com/us-en/storagegrid-119/ilm/managing-objects-with-s3-object-lock.html).

Capacity pressure never authorizes removing retention. Report the evidence to the data owner; deleting a version,
removing a hold, suspending versioning or editing lifecycle rules is theirs to decide and run.

Sources (library: aws/s3): Versioning, Object lifecycle management, Object Lock.
