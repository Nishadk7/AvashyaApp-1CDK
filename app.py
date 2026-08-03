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

# 2. IAM Roles & Security Groups Stack (Built From Scratch)
security_stack = SecurityStack(
    app,
    "NishadInternsip-AvashyaSecurityStack",
    vpc=vpc_stack.vpc,
    env=env,
    description="Custom IAM Roles and chained Security Groups for 3-Tier Web Application.",
)

# 3. Storage & Database Stack (S3 + Multi-AZ RDS PostgreSQL)
storage_db_stack = StorageDbStack(
    app,
    "NishadInternsip-AvashyaStorageDbStack",
    vpc=vpc_stack.vpc,
    rds_sg=security_stack.rds_db_sg,
    env=env,
    description="Private S3 Bucket (avashya-drop-uploads-2026) and Multi-AZ RDS PostgreSQL Instance.",
)

# 4. Compute Stack (External ALB, Web ASG, Internal ALB, App ASG)
compute_stack = ComputeStack(
    app,
    "NishadInternsip-AvashyaComputeStack",
    vpc=vpc_stack.vpc,
    external_alb_sg=security_stack.external_alb_sg,
    web_tier_sg=security_stack.web_tier_sg,
    internal_alb_sg=security_stack.internal_alb_sg,
    app_tier_sg=security_stack.app_tier_sg,
    web_tier_role=security_stack.web_tier_role,
    app_tier_role=security_stack.app_tier_role,
    rds_endpoint=storage_db_stack.db_instance.db_instance_endpoint_address,
    s3_bucket_name=storage_db_stack.s3_bucket.bucket_name,
    env=env,
    description="External and Internal Load Balancers, Launch Templates, and Auto Scaling Groups.",
)

# 5. Route 53 Stack (Public Domain DNS -> Public NLB)
domain_name = app.node.try_get_context("domain_name") or "avashyaapp.com"
route53_stack = Route53Stack(
    app,
    "NishadInternsip-AvashyaRoute53Stack",
    target_lb=compute_stack.public_nlb,
    domain_name=domain_name,
    env=env,
    description="AWS Route 53 Hosted Zone and Alias A-Records pointing public domain traffic to Public NLB.",
)

# Apply global tag Owner:Nishad to all services across all stacks
cdk.Tags.of(app).add("Owner", "Nishad")

app.synth()
