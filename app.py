#!/usr/bin/env python3
import os
import aws_cdk as cdk

from stacks.vpc_stack import VpcStack
from stacks.security_stack import SecurityStack
from stacks.storage_db_stack import StorageDbStack
from stacks.compute_stack import ComputeStack
from stacks.route53_stack import Route53Stack

app = cdk.App()

# Target AWS Environment (Explicitly locked to ap-south-1)
env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT", os.getenv("AWS_ACCOUNT_ID")),
    region="ap-south-1",
)

# 1. Custom Amazon VPC Stack (10.0.0.0/16 across 2 AZs)
vpc_stack = VpcStack(
    app,
    "NishadInternsip-AvashyaVpcStack",
    env=env,
    description="Custom VPC Stack with 6 subnets across 2 AZs, IGW, 2 NAT Gateways, and S3 VPC Endpoint.",
)

# 2. IAM Roles & Security Groups Stack (Single ALB -> App Tier -> RDS Chaining)
security_stack = SecurityStack(
    app,
    "NishadInternsip-AvashyaSecurityStack",
    vpc=vpc_stack.vpc,
    env=env,
    description="Custom IAM Roles and chained Security Groups for S3 Web + EC2 App Architecture.",
)

# 3. Storage & Database Stack (S3 Upload Bucket + Web Frontend S3 Bucket + Single-AZ RDS)
storage_db_stack = StorageDbStack(
    app,
    "NishadInternsip-AvashyaStorageDbStack",
    vpc=vpc_stack.vpc,
    rds_sg=security_stack.rds_db_sg,
    env=env,
    description="Private S3 Buckets (web frontend & file drop) and Single-AZ RDS PostgreSQL Instance.",
)

# 4. Compute Stack (Single ALB, CloudFront Distribution, App Tier ASG in Private Subnets)
compute_stack = ComputeStack(
    app,
    "NishadInternsip-AvashyaComputeStack",
    vpc=vpc_stack.vpc,
    alb_sg=security_stack.alb_sg,
    app_tier_sg=security_stack.app_tier_sg,
    app_tier_role=security_stack.app_tier_role,
    web_frontend_bucket=storage_db_stack.web_frontend_bucket,
    rds_endpoint=storage_db_stack.db_instance.db_instance_endpoint_address,
    s3_bucket_name=storage_db_stack.s3_bucket.bucket_name,
    env=env,
    description="Single ALB, CloudFront Distribution (S3 + ALB), and App Tier Auto Scaling Group.",
)

# 5. Route 53 Stack (Optional - Points domain to CloudFront Distribution)
domain_name = app.node.try_get_context("domain_name")
if domain_name:
    route53_stack = Route53Stack(
        app,
        "NishadInternsip-AvashyaRoute53Stack",
        distribution=compute_stack.distribution,
        domain_name=domain_name,
        env=env,
        description="AWS Route 53 Hosted Zone and Alias A-Records pointing public domain traffic to CloudFront.",
    )

# Apply global tag Owner:Nishad to all services across all stacks
cdk.Tags.of(app).add("Owner", "Nishad")

app.synth()
