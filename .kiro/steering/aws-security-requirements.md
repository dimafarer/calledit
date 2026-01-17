---
inclusion: always
---

# AWS Security Requirements

This steering document defines mandatory AWS security requirements for all code in this project. These requirements are enforced at the organizational level and violations will trigger security alarms.

## Critical Security Rules

### 1. S3 Bucket Access - MANDATORY

**RULE**: Never create or configure public S3 buckets

**Requirement**: All S3 buckets MUST be private with public access blocked

**Correct Pattern** (CloudFront + Private S3):
```python
# ✅ CORRECT: Private bucket with CloudFront distribution
import boto3

s3_client = boto3.client('s3')

# Create private bucket
s3_client.create_bucket(
    Bucket='my-private-bucket',
    ACL='private'  # Always private
)

# Block all public access
s3_client.put_public_access_block(
    Bucket='my-private-bucket',
    PublicAccessBlockConfiguration={
        'BlockPublicAcls': True,
        'IgnorePublicAcls': True,
        'BlockPublicPolicy': True,
        'RestrictPublicBuckets': True
    }
)

# Use CloudFront for public access
cloudfront_client = boto3.client('cloudfront')
# Configure CloudFront distribution with OAI/OAC to access private bucket
```

**Incorrect Pattern** (Public S3):
```python
# ❌ WRONG: Public bucket - WILL TRIGGER ALARMS
s3_client.create_bucket(
    Bucket='my-bucket',
    ACL='public-read'  # NEVER DO THIS
)

# ❌ WRONG: Public access enabled
s3_client.put_public_access_block(
    Bucket='my-bucket',
    PublicAccessBlockConfiguration={
        'BlockPublicAcls': False,  # NEVER DO THIS
        'IgnorePublicAcls': False,
        'BlockPublicPolicy': False,
        'RestrictPublicBuckets': False
    }
)
```

### 2. CloudFront Distribution Pattern

**When serving static content publicly**:

```python
# Create CloudFront Origin Access Identity (OAI) or Origin Access Control (OAC)
cloudfront_client = boto3.client('cloudfront')

# OAC (recommended for S3)
oac_response = cloudfront_client.create_origin_access_control(
    OriginAccessControlConfig={
        'Name': 'my-oac',
        'Description': 'OAC for private S3 bucket',
        'SigningProtocol': 'sigv4',
        'SigningBehavior': 'always',
        'OriginAccessControlOriginType': 's3'
    }
)

# Create CloudFront distribution
distribution = cloudfront_client.create_distribution(
    DistributionConfig={
        'Origins': {
            'Items': [{
                'Id': 'S3-my-private-bucket',
                'DomainName': 'my-private-bucket.s3.amazonaws.com',
                'S3OriginConfig': {
                    'OriginAccessIdentity': ''  # Empty for OAC
                },
                'OriginAccessControlId': oac_response['OriginAccessControl']['Id']
            }]
        },
        'DefaultCacheBehavior': {
            'TargetOriginId': 'S3-my-private-bucket',
            'ViewerProtocolPolicy': 'redirect-to-https',
            # ... other settings
        },
        'Enabled': True
    }
)

# Update S3 bucket policy to allow CloudFront OAC access
bucket_policy = {
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "AllowCloudFrontServicePrincipal",
        "Effect": "Allow",
        "Principal": {
            "Service": "cloudfront.amazonaws.com"
        },
        "Action": "s3:GetObject",
        "Resource": f"arn:aws:s3:::my-private-bucket/*",
        "Condition": {
            "StringEquals": {
                "AWS:SourceArn": f"arn:aws:cloudfront::{account_id}:distribution/{distribution_id}"
            }
        }
    }]
}

s3_client.put_bucket_policy(
    Bucket='my-private-bucket',
    Policy=json.dumps(bucket_policy)
)
```

### 3. SAM/CloudFormation Templates

**S3 Bucket Resource** (always private):
```yaml
# ✅ CORRECT: Private S3 bucket in SAM template
Resources:
  MyPrivateBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: my-private-bucket
      AccessControl: Private
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256

  # CloudFront distribution for public access
  MyCloudFrontDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Origins:
          - Id: S3Origin
            DomainName: !GetAtt MyPrivateBucket.RegionalDomainName
            S3OriginConfig:
              OriginAccessIdentity: !Sub 'origin-access-identity/cloudfront/${CloudFrontOAI}'
        DefaultCacheBehavior:
          TargetOriginId: S3Origin
          ViewerProtocolPolicy: redirect-to-https
          AllowedMethods:
            - GET
            - HEAD
          CachedMethods:
            - GET
            - HEAD
          ForwardedValues:
            QueryString: false
        Enabled: true

  CloudFrontOAI:
    Type: AWS::CloudFront::CloudFrontOriginAccessIdentity
    Properties:
      CloudFrontOriginAccessIdentityConfig:
        Comment: OAI for private S3 bucket
```

**NEVER do this**:
```yaml
# ❌ WRONG: Public S3 bucket - WILL TRIGGER ALARMS
Resources:
  MyPublicBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: my-public-bucket
      AccessControl: PublicRead  # NEVER DO THIS
      PublicAccessBlockConfiguration:
        BlockPublicAcls: false  # NEVER DO THIS
```

### 4. Verification Checklist

Before deploying any code that touches S3:

- [ ] All S3 buckets have `AccessControl: Private`
- [ ] All S3 buckets have `PublicAccessBlockConfiguration` with all values set to `true`
- [ ] Public access is provided through CloudFront, not direct S3
- [ ] CloudFront uses OAI or OAC to access private S3 buckets
- [ ] S3 bucket policies only allow CloudFront access, not public access
- [ ] No bucket ACLs grant public permissions
- [ ] No bucket policies grant public permissions

### 5. Code Review Requirements

**When reviewing S3-related code**:

1. Search for `public` in S3 configurations
2. Verify `PublicAccessBlockConfiguration` is present and correct
3. Confirm CloudFront is used for public access
4. Check bucket policies don't grant public access
5. Verify no `AllUsers` or `AuthenticatedUsers` principals

**Red Flags** (reject immediately):
- `ACL='public-read'`
- `ACL='public-read-write'`
- `BlockPublicAcls: false`
- `BlockPublicPolicy: false`
- `Principal: "*"` in bucket policy without proper conditions
- `AllUsers` or `AuthenticatedUsers` in ACLs

## Additional Security Best Practices

### 1. Encryption

Always enable encryption for S3 buckets:
```python
s3_client.put_bucket_encryption(
    Bucket='my-bucket',
    ServerSideEncryptionConfiguration={
        'Rules': [{
            'ApplyServerSideEncryptionByDefault': {
                'SSEAlgorithm': 'AES256'
            }
        }]
    }
)
```

### 2. Versioning

Enable versioning for important buckets:
```python
s3_client.put_bucket_versioning(
    Bucket='my-bucket',
    VersioningConfiguration={'Status': 'Enabled'}
)
```

### 3. Logging

Enable access logging:
```python
s3_client.put_bucket_logging(
    Bucket='my-bucket',
    BucketLoggingStatus={
        'LoggingEnabled': {
            'TargetBucket': 'my-logs-bucket',
            'TargetPrefix': 'my-bucket-logs/'
        }
    }
)
```

## Consequences of Violations

**What happens if you create a public S3 bucket**:
1. ⚠️ Security alarms will trigger immediately
2. 🚨 Security team will be notified
3. 🔒 Bucket may be automatically locked down
4. 📧 Incident report will be filed
5. ⏱️ Deployment may be rolled back

**Always use CloudFront + Private S3** - no exceptions!

## Questions?

If you're unsure whether your S3 configuration is secure:
1. Check this document first
2. Verify all public access is blocked
3. Confirm CloudFront is used for public access
4. Ask the user if still uncertain

**When in doubt, keep it private!**
