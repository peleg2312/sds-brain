# Ceph Squid S3 API and feature support

This is a landing page or contents index. Linked documents are not part of this individual snapshot.

Report a Documentation Bug

# Ceph Object Gateway S3 API

Ceph supports a RESTful API that is compatible with the basic data access model of the Amazon S3 API.

## API

- Common

- Authentication

- Service Ops

- Bucket Ops

- Object Ops

- C++

- C#

- Java

- Perl

- PHP

- Python

- Ruby AWS::SDK Examples (aws-sdk gem ~>2)

- Ruby AWS::S3 Examples (aws-s3 gem)

## Features Support

The following table describes the support status for current Amazon S3 functional features:

Feature | Status | Remarks

List Buckets | Supported |

Delete Bucket | Supported |

Create Bucket | Supported | Different set of canned ACLs

Bucket Lifecycle | Supported |

Bucket Replication | Partial | Permitted only across zones

Policy (Buckets, Objects) | Supported | ACLs & bucket policies are supported

Bucket Website | Supported |

Bucket ACLs (Get, Put) | Supported | Different set of canned ACLs

Bucket Location | Supported |

Bucket Notification | Supported | See S3 Notification Compatibility

Bucket Object Versions | Supported |

Get Bucket Info (HEAD) | Supported |

Bucket Request Payment | Supported |

Put Object | Supported |

Delete Object | Supported |

Get Object | Supported |

Object ACLs (Get, Put) | Supported |

Get Object Info (HEAD) | Supported |

POST Object | Supported |

Copy Object | Supported |

Multipart Uploads | Supported |

Object Tagging | Supported | See Object Related Operations for Policy verbs

Bucket Tagging | Supported |

Storage Class | Supported | See Storage Classes

## Unsupported Header Fields

The following common request header fields are not supported:

Name | Type

x-amz-id-2 | Response

Brought to you by the Ceph Foundation

The Ceph Documentation is a community resource funded and hosted by the non-profit Ceph Foundation. If you would like to support this and our other efforts, please consider joining now.
