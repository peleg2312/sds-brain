# Authenticating Requests (AWS Signature Version 4)

###### Topics

- Authentication Methods

- Introduction to Signing Requests

- Authenticating Requests: Using the Authorization Header (AWS Signature Version 4)

- Authenticating Requests: Using Query Parameters (AWS Signature Version 4)

- Examples: Signature Calculations in AWS Signature Version 4

- Authenticating Requests: Browser-Based Uploads Using POST (AWS Signature Version 4)

- Amazon S3 Signature Version 4 Authentication Specific Policy Keys

Every interaction with Amazon S3 is either authenticated or anonymous. This section explains
request authentication with the AWS Signature Version 4 algorithm.

###### Note

If you use the AWS SDKs (see Sample Code and
Libraries) to send your requests, you don't need to read this section
because the SDK clients authenticate your requests by using access keys that you
provide. Unless you have a good reason not to, you should always use the AWS SDKs. In
Regions that support both signature versions, you can request AWS SDKs to use specific
signature version. For more information, see Sending authenticated requests using the AWS SDKs. You need to read this section only if you are
implementing the AWS Signature Version 4 algorithm in your custom client.

Authentication with AWS Signature Version 4 provides some or all of the following, depending
on how you choose to sign your request:

- Verification of the identity of the requester –
Authenticated requests require a signature that you create by using your access
keys (access key ID, secret access key). For information about getting access
keys, see Understanding and Getting Your
Security Credentials in the AWS General Reference. If
you are using temporary security credentials, the signature calculations also
require a security token. For more information, see Requesting Temporary Security
Credentials in the IAM User Guide.

- In-transit data protection – In order to prevent
tampering with a request while it is in transit, you use some of the request
elements to calculate the request signature. Upon receiving the request, Amazon S3
calculates the signature by using the same request elements. If any request
component received by Amazon S3 does not match the component that was used to
calculate the signature, Amazon S3 will reject the request.

- Protect against reuse of the signed portions of the request
– The signed portions (using AWS Signatures) of requests are valid within 15
minutes of the timestamp in the request. An unauthorized party who has access to a
signed request can modify the unsigned portions of the request without affecting the
request's validity in the 15 minute window. Because of this, we recommend that you
maximize protection by signing request headers and body, making HTTPS requests to
Amazon S3, and by using the s3:x-amz-content-sha256 condition key (see Amazon S3 Signature Version 4 Authentication Specific Policy Keys) in AWS policies to require
users to sign Amazon S3 request bodies.

###### Note

Amazon S3 supports Signature Version 4, a protocol for authenticating inbound API requests to AWS
services, in all AWS Regions. At this time, AWS Regions created before January 30, 2014
will continue to support the previous protocol, Signature Version 2. Any new Regions
after January 30, 2014 will support only Signature Version 4 and therefore all requests
to those Regions must be made with Signature Version 4.
For
more information about AWS Signature Version 2, see Signing and Authenticating REST
Requests in the Amazon Simple Storage Service User Guide.

## Authentication Methods

You can express authentication information by using one of the following
methods:

- HTTP Authorization header – Using the HTTP
Authorization header is the most common method of
authenticating an Amazon S3 request. All of the Amazon S3 REST operations (except for
browser-based uploads using POST requests) require this header. For more
information about the Authorization header value, and how to calculate signature
and related options, see Authenticating Requests: Using the Authorization Header (AWS Signature Version 4).

- Query string parameters – You can use
a query string to express a request entirely in a URL. In this case, you use
query parameters to provide request information, including the
authentication information. Because the request signature is part of the
URL, this type of URL is often referred to as a presigned URL. You can use
presigned URLs to embed clickable links, which can be valid for up to seven
days, in HTML. For more information, see Authenticating Requests: Using Query Parameters (AWS Signature Version 4).

Amazon S3 also supports browser-based uploads that use HTTP POST requests. With an HTTP POST
request, you can upload content to Amazon S3 directly from the browser. For information about
authenticating POST requests, see Browser-Based Uploads Using POST (AWS Signature Version 4).

## Introduction to Signing Requests

Authentication information that you send in a request must include a signature. To
calculate a signature, you first concatenate select request elements to form a string,
referred to as the string to sign. You then use a signing key to
calculate the hash-based message authentication code (HMAC) of the string to sign.

In AWS Signature Version 4, you don't use your secret access key to sign the request.
Instead, you first use your secret access key to derive a signing key.

The derived signing key is specific to the date, service, and Region. For more information about how to derive a signing key in different programming languages, see Examples of how to derive a signing key for Signature Version 4.

The following diagram illustrates the general process of computing a signature.

The string to sign depends on the request type. For example, when you use the HTTP
Authorization header or the query parameters for authentication, you use a varying
combination of request elements to create the string to sign. For an HTTP POST request,
the POST policy in the request is the string you sign. For more information about
computing string to sign, follow links provided at the end of this section.

For signing key, the diagram shows series of calculations, where result of each step you
feed into the next step. The final step is the signing key.

Upon receiving an authenticated request, Amazon S3 servers re-create the signature by using
the authentication information that is contained in the request. If the signatures
match, Amazon S3 processes your request; otherwise, the request is rejected.

For more information about authenticating requests, see the following topics:

- Authenticating Requests: Using the Authorization Header (AWS Signature Version 4)

- Authenticating Requests: Using Query Parameters (AWS Signature Version 4)

- Browser-Based Uploads Using POST (AWS Signature Version 4)

Javascript is disabled or is unavailable in your browser.

To use the Amazon Web Services Documentation, Javascript must be enabled. Please refer to your browser's Help pages for instructions.

Document Conventions

Create a presigned URL to get an object

Using an Authorization Header
