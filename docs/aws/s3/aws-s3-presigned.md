# Download and upload objects with presigned URLs

You can use presigned URLs to grant time-limited access to objects in Amazon S3 without updating
your bucket policy. A presigned URL can be entered in a browser or used by a program to download
an object. The credentials used by the presigned URL are those of the AWS Identity and Access Management (IAM)
principal who generated the URL.

You can also use presigned URLs to allow someone to upload a specific object to your Amazon S3
bucket. This allows an upload without requiring another party to have AWS security
credentials or permissions. If an object with the same key already exists in the bucket as
specified in the presigned URL, Amazon S3 replaces the existing object with the uploaded
object.

You can use the presigned URL multiple times, up to the expiration date and time.

Annotation API operations (PutObjectAnnotation,
GetObjectAnnotation, ListObjectAnnotations, and
DeleteObjectAnnotation) support presigned URLs.

When you create a presigned URL, you must provide your security credentials, and then specify
the following:

- An Amazon S3 bucket

- An object key (if downloading this object will be in your Amazon S3 bucket, if
uploading this is the file name to be uploaded)

- An HTTP method (GET for downloading objects, PUT for
uploading, HEAD for reading object metadata, etc)

- An expiration time interval

When using presigned URLs to upload objects, you can verify object integrity using
checksums. While presigned URLs created with AWS Signature Version 2 only support MD5
checksums, presigned URLs created with AWS Signature Version 4 support additional checksum
algorithms including CRC-64/NVME, CRC32, CRC32C, SHA-1, SHA-256, MD5, XXHash64, XXHash3, XXHash128, and SHA-512.
To use these additional
checksum algorithms, ensure you're using AWS Signature Version 4 and include the appropriate
checksum header in your upload request. For more information about object integrity, see
Checking object integrity in Amazon S3.

###### Topics

- Who can create a presigned URL

- Expiration time for presigned URLs

- Limiting presigned URL capabilities

- Frequently asked questions for presigned URLs

- Sharing objects with presigned URLs

- Uploading objects with presigned URLs

## Who can create a presigned URL

Anyone with valid security credentials can create a presigned URL. But for someone to
successfully access an object, the presigned URL must be created by someone who has
permission to perform the operation that the presigned URL is based upon.

The following are the types of credentials that you can use to create a
presigned URL:

- IAM user – Valid up to 7 days when
you're using AWS Signature Version 4.

To create a presigned URL that's valid for up to 7 days, first delegate IAM user
credentials (the access key and secret key) to the method you're using to create
the presigned URL.

- Temporary security credentials – Can't be valid for longer than the credentials themselves. These credentials include:

- IAM role credentials – The presigned URL expires when the role session expires, even if you specify a longer expiration time.

- IAM role credentials used by Amazon EC2 instances – Valid for the duration of the role credentials (typically 6 hours).

- AWS Security Token Service credentials – Valid only for the duration of the temporary credentials.

###### Note

If you created a presigned URL using a temporary credential, the URL expires when the
credential expires. In general, a presigned URL expires when the credential you used
to create it is revoked, deleted, or deactivated. This is true even if the URL was
created with a later expiration time. For temporary security credentials lifetimes,
see Comparing AWS STS API operations in the IAM User Guide.

## Expiration time for presigned URLs

A presigned URL remains valid for the period of time specified when the URL is generated.
If you create a presigned URL with the Amazon S3 console, the expiration time can be set between
1 minute and 12 hours. If you use the AWS CLI or AWS SDKs, the expiration time can be
set as high as 7 days.

If you created a presigned URL by using a temporary token, then the URL expires when the
token expires. In general, a presigned URL expires when the credential you used to
create it is revoked, deleted, or deactivated. This is true even if the URL was created
with a later expiration time. For more information about how the credentials you use
affect the expiration time, see Who can create a presigned URL.

Amazon S3 checks the expiration date and time of a signed URL at the time of the HTTP
request. For example, if a client begins to download a large file immediately before the
expiration time, the download continues even if the expiration time passes during the
download. However, if the connection drops and the client tries to restart the download
after the expiration time passes, the download fails.

## Limiting presigned URL capabilities

The capabilities of a presigned URL are limited by the permissions of the user who created
it. In essence, presigned URLs are bearer tokens that grant access to those who possess
them. As such, we recommend that you protect them appropriately. The following are some
methods that you can use to restrict the use of your presigned URLs.

###### AWS Signature Version 4 (SigV4)

To enforce specific behavior when presigned URL requests are authenticated by using
AWS Signature Version 4 (SigV4), you can use condition keys in bucket policies and
access point policies. For example, the following bucket policy uses the
s3:signatureAge condition to deny any Amazon S3 presigned URL request on
objects in the amzn-s3-demo-bucket bucket if the signature is more than 10 minutes
old. To use this example, replace the user input
placeholders with your own information.

For more information about policy keys related AWS Signature Version 4, see AWS Signature
Version 4 Authentication in the Amazon Simple Storage Service API Reference.

###### Network path restriction

If you want to restrict the use of presigned URLs and all Amazon S3 access to particular
network paths, you can write AWS Identity and Access Management (IAM) policies. You can set these policies
on the IAM principal that makes the call, the Amazon S3 bucket, or both.

A network-path restriction on the IAM principal requires the user of those
credentials to make requests from the specified network. A restriction on the bucket or
access point requires that all requests to that resource originate from the specified
network. These restrictions also apply outside of the presigned URL scenario.

The IAM global condition key that you use depends on the type of endpoint. If you're
using the public endpoint for Amazon S3, use aws:SourceIp. If you're using a
virtual private cloud (VPC) endpoint to Amazon S3, use aws:SourceVpc or
aws:SourceVpce.

The following IAM policy statement requires the principal to access AWS only from
the specified network range. With this policy statement, all access must originate from
that range. This includes the case of someone who's using a presigned URL for Amazon S3. To use
this example, replace the user input
placeholders with your own information.

```
{
    "Sid": "NetworkRestrictionForIAMPrincipal",
    "Effect": "Deny",
    "Action": "*",
    "Resource": "*",
    "Condition": {
        "NotIpAddressIfExists": {"aws:SourceIp": "IP-address-range"},
        "BoolIfExists": {"aws:ViaAWSService": "false"}
    }
}
```

## Frequently asked questions for presigned URLs

###### Q: Why do my presigned URLs expire earlier than the configured expiration time?

Presigned URLs remain valid only while their underlying credentials are valid. A presigned URL expires at either its configured expiration time or when its associated credentials expire, whichever occurs first. For Amazon Elastic Container Service tasks or containers, role credentials typically rotate every 1-6 hours. When using AWS Security Token Service (AWS STS) AssumeRole, the presigned URL expires when the role session ends, which by default is 1 hour. For Amazon EC2 instance profiles, metadata credentials rotate periodically with a maximum validity period of approximately 6 hours.

###### Q: Why am I getting a 403 Forbidden error when accessing a presigned URL?

Before generating a presigned URL, verify that you have the correct permissions configured. The IAM user or role generating the URL must have the required permissions, such as s3:GetObject, for the specific operation. Additionally, check that the Amazon S3 bucket policy doesn't explicitly deny access to the object.

###### Q: Why am I getting an AccessDenied error with HeadersNotSigned: if-range?

When Range is included in X-Amz-SignedHeaders, Amazon S3
requires that If-Range also be signed if present in the request. Add
If-Range to X-Amz-SignedHeaders when you generate the
presigned URL.

###### Q: I'm getting SignatureDoesNotMatch errors. How do I fix this?

If you encounter SignatureDoesNotMatch errors when using Amazon S3 presigned URLs, consider several common causes. First, ensure that your system clock is synchronized with a Network Time Protocol (NTP) server, as even small time drifts can invalidate signatures. Next, be aware that some corporate proxies might modify headers or query strings, potentially causing signature mismatches. To troubleshoot, try testing without the proxy. Finally, verify that all request parameters—including the HTTP method, headers, and query string—match exactly between URL generation and usage. Addressing these issues can often resolve SignatureDoesNotMatch errors.

###### Q: I'm getting ExpiredToken errors. What should I do?

When you receive ExpiredToken errors while using presigned URLs, it indicates that the AWS credentials used to generate the URL are no longer valid. To resolve this issue, refresh your AWS credentials before generating new presigned URLs. For long-running applications, we recommend implementing credential refresh logic to maintain continuous access. Where appropriate, you can use longer-lived credentials or implement token refresh mechanisms. If you're using AWS Security Token Service (AWS STS) AssumeRole, verify that your configured session duration meets your use case requirements. Remember that presigned URLs remain valid only for the duration of their underlying credentials, so implementing proper credential management is essential.

Javascript is disabled or is unavailable in your browser.

To use the Amazon Web Services Documentation, Javascript must be enabled. Please refer to your browser's Help pages for instructions.

Document Conventions

Viewing object properties

Sharing objects with presigned URLs
