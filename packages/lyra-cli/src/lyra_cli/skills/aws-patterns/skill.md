---
name: aws-patterns
description: AWS architecture patterns and best practices
origin: ECC
tags: [aws, cloud, infrastructure, devops]
triggers: [aws, lambda, s3, ec2, cloudformation]
---

# AWS Patterns

## Overview

AWS architecture patterns for scalable, reliable cloud applications.

## Compute Patterns

### Lambda Function

```python
import json

def lambda_handler(event, context):
    body = json.loads(event['body'])
    result = process(body)
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
```

### Auto Scaling

```yaml
Resources:
  AutoScalingGroup:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      MinSize: 2
      MaxSize: 10
      DesiredCapacity: 3
      TargetGroupARNs:
        - !Ref TargetGroup
```

## Storage Patterns

### S3 Lifecycle

```json
{
  "Rules": [{
    "Status": "Enabled",
    "Transitions": [{
      "Days": 30,
      "StorageClass": "STANDARD_IA"
    }, {
      "Days": 90,
      "StorageClass": "GLACIER"
    }]
  }]
}
```

### DynamoDB

```python
table.put_item(
    Item={
        'id': '123',
        'data': 'value'
    },
    ConditionExpression='attribute_not_exists(id)'
)
```

## Security Patterns

### IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject"],
    "Resource": "arn:aws:s3:::bucket/*"
  }]
}
```

### Secrets Manager

```python
import boto3

client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='db-password')
secret = json.loads(response['SecretString'])
```

## Best Practices

1. **Use IAM roles** not access keys
2. **Enable CloudTrail** for auditing
3. **Use VPC** for network isolation
4. **Tag all resources** for cost tracking
5. **Enable encryption** at rest and in transit
6. **Use CloudFormation** for infrastructure as code
7. **Implement auto-scaling** for resilience
8. **Monitor with CloudWatch** metrics and alarms
