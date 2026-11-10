---
name: s3-signature-tls
description: Diagnose S3 SignatureDoesNotMatch, clock or region mismatches, presigned URL problems and TLS / certificate failures in front of RGW or StorageGRID. Use for "SignatureDoesNotMatch", "signature mismatch", "certificate verify failed", "TLS handshake", "presigned URL does not work", "RequestTimeTooSkewed".
---
# S3 signature mismatch and TLS failures

Read-only (rule 1). Scope: backend, endpoint, TLS hostname, port, SDK version, addressing style, request method, UTC
time. First decide the layer: a request that never completes TLS has not reached signature validation; an S3 error
response proves it got further.

Never collect a full signed URL, secret key, Authorization header, session token or an unrestricted debug trace
(rule 4). A signature case needs header names, canonicalization choices, timestamps and endpoint settings, not
credential values.

## Signature
1. **Scope and clock**: signing region / service and request timestamp against the real endpoint. SigV4 derives its
   key from the credential, date, region and service; clocks: `chronyc tracking` on client and gateways.
2. **Canonical request**: method, host, port handling, path-style versus virtual-host, URL encoding, query
   parameters, the signed header names. A proxy that rewrites host, path or headers breaks the signature. Compare
   with a supported SDK using the same settings; do not hand-build a signature first.
3. **Credential kind**: static or session-based; is a session token sent when needed (do not print it). On RGW /
   StorageGRID check that the release and identity configuration support the method used.
4. **Presigned URL**: method, expiry, generation time, issuing principal. It works with the issuer's permissions, and
   the credential's lifetime can cut validity short. Never paste or replay the whole URL.

## TLS and proxy
Presented certificate: subject / SAN, validity, issuer chain, and the client's trust store. On StorageGRID the client
connection has a hostname, an endpoint port and a certificate
(`search_docs("configuring client connections", product="storagegrid-119")`). A connection that works by IP with
verification switched off says nothing about the intended hostname path.

After an SDK upgrade: check the exact algorithm, checksum, chunking and trailer behaviour against the provider's
release-specific API reference; "S3 compatible" proves none of them (skill `s3-multipart-checksums`).

## Result
Separate, with evidence: TLS, clock / scope, canonicalization, credential lifecycle, compatibility. Suggest one
controlled comparison with an approved metadata request. Key rotation and proxy / TLS changes are the user's.
