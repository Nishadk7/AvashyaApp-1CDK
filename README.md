# AWS CDK v2 Production-Ready 3-Tier Web Application Infrastructure

This repository contains production-ready Infrastructure-as-Code (IaC) written in **AWS CDK v2 (Python)** to provision a highly available, decoupled 3-Tier Web Application architecture across 2 Availability Zones (`ap-south-1a`, `ap-south-1b`) inside a custom Amazon VPC (`10.0.0.0/16`).

---

## 🏗️ Architecture Topology

```
                          +------------------------------------+
                          |     AWS Route 53 Hosted Zone       |
                          |    (A-Record Alias to CloudFront)  |
                          +------------------------------------+
                                           |
                                           v
                         +-----------------------------------+
                         |   Amazon CloudFront CDN (HTTPS)   |
                         +─────────────────┬─────────────────+
                          /* (Default)     │ /api/* (API Traffic)
                          v                v
        +────────────────────────────+   +─────────────────────────────────────+
        | Amazon S3 Web Bucket (OAC) |   | CloudFront VPC Origin Service SG    |
        | (avashya-web-frontend-v2)  |   | (sg-03f5ad1e3483e05a4)              |
        +────────────────────────────+   +──────────────────┬──────────────────+
                                                            │
                                                            v (Private Subnets: 10.0.10.0/24, 10.0.11.0/24)
                                         +─────────────────────────────────────+
                                         | Private Application Load Balancer   |
                                         |         [NishadInternsip-ALB-SG]    |
                                         +──────────────────┬──────────────────+
                                                            │
                                                            v (HTTP: Port 8000)
                                         +─────────────────────────────────────+
                                         | App Tier Auto Scaling Group (EC2)   |
                                         |    [NishadInternsip-App-Tier-SG]    |
                                         |     (Role: Avashya-EC2-App-Role)    |
                                         +──────────────────┬──────────────────+
                                           /                │
                                          /                 v (PostgreSQL: Port 5432)
       +───────────────────────────────────+   +─────────────────────────────────────+
       |     S3 Gateway VPC Endpoint       |   | Amazon RDS PostgreSQL (Single-AZ)   |
       |  (avashya-drop-uploads-2026-v2)   |   |   [NishadInternsip-RDS-Database-SG] |
       +───────────────────────────────────+   | Isolated DB Subnets: 10.0.20.0/24  |
                                               +─────────────────────────────────────+
```

---

## 📦 Stack & File Structure Breakdown

| Path | Description |
| :--- | :--- |
| [`app.py`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/app.py) | Main CDK Application entrypoint orchestrating stack deployment |
| [`stacks/vpc_stack.py`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/stacks/vpc_stack.py) | Custom VPC `10.0.0.0/16` across 2 AZs (6 subnets, IGW, Regional NAT Gateway, S3 VPC Endpoint) |
| [`stacks/security_stack.py`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/stacks/security_stack.py) | Custom IAM Roles (`Avashya-EC2-App-Role`) & 3 chained Security Groups |
| [`stacks/storage_db_stack.py`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/stacks/storage_db_stack.py) | S3 Frontend Bucket, S3 Uploads Bucket (`v2`) & RDS PostgreSQL Database |
| [`stacks/compute_stack.py`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/stacks/compute_stack.py) | CloudFront Distribution (OAC & VPC Origin), Private ALB, Launch Template & App ASG |
| [`stacks/route53_stack.py`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/stacks/route53_stack.py) | Route 53 Public Hosted Zone and Alias A-Records pointing public domain to CloudFront |
| [`scripts/userdata_app.sh`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/scripts/userdata_app.sh) | App Tier UserData boot script (FastAPI setup, CloudWatch agent, RDS & S3 env vars) |

---

## 🔒 Security Group Chaining Matrix

| Security Group | Inbound Source | Port(s) | Description |
| :--- | :--- | :--- | :--- |
| `CloudFront-VPCOrigins-Service-SG` | CloudFront Edge Network | `80`, `443` | AWS-managed security group for CloudFront VPC Origin ENIs |
| `NishadInternsip-ALB-SG` | `CloudFront-VPCOrigins-Service-SG` / VPC CIDR | `80` | Allows HTTP 80 traffic ONLY from CloudFront VPC Origin |
| `NishadInternsip-App-Tier-SG` | `NishadInternsip-ALB-SG` | `8000` | Allows API service requests ONLY from Private ALB |
| `NishadInternsip-RDS-Database-SG` | `NishadInternsip-App-Tier-SG` | `5432` | Allows PostgreSQL connections ONLY from App Tier EC2 instances |

---

## 🚀 Step-by-Step CLI Deployment Guide

### Prerequisites
1. **AWS CLI v2** configured with credentials (`aws configure`).
2. **Node.js 18+** & **AWS CDK CLI** (`npm install -g aws-cdk`).
3. **Python 3.9+** & `pip`.

---

### Step 1: Open Terminal & Navigate to the CDK Directory
```bash
cd c:\Users\nishad\Desktop\AvashyaApp#1CDK
```

---

### Step 2: Set Up & Activate Python Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate virtual environment (Command Prompt / Linux / macOS)
# .\.venv\Scripts\activate.bat
# source .venv/bin/activate

# Upgrade pip & install CDK dependencies into the virtual environment
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 3: AWS CDK Bootstrap (First Time Setup)
Bootstrap your target AWS account & region to provision CDK staging buckets:
```bash
cdk bootstrap aws://YOUR_ACCOUNT_ID/ap-south-1
```

---

### Step 4: Synthesize CloudFormation Templates
Verify code correctness and generate CloudFormation templates:
```bash
cdk synth
```

---

### Step 5: Deploy the Infrastructure Stack
Deploy all 5 interconnected stacks in dependent sequence:
```bash
cdk deploy --all --require-approval never
```

> **Optional Context Parameters**:
> To specify a custom domain name for Route 53:
> ```bash
> cdk deploy --all -c domain_name="mycustomdomain.com"
> ```

---

## 🧪 Post-Deployment Verification

1. **Verify VPC & Subnet Topology**:
   ```bash
   aws ec2 describe-vpcs --filters "Name=tag:Name,Values=*AvashyaVpc*"
   ```
2. **Verify Load Balancer Endpoints**:
   ```bash
   aws elbv2 describe-load-balancers --query "LoadBalancers[*].[LoadBalancerName,DNSName,Scheme]" --output table
   ```
3. **Verify Route 53 Record**:
   ```bash
   aws route53 list-resource-record-sets --hosted-zone-id YOUR_HOSTED_ZONE_ID
   ```
4. **Test External ALB HTTP Endpoint**:
   ```bash
   curl -I http://<EXTERNAL_ALB_DNS_NAME>
   ```

---

## 🧹 Infrastructure Cleanup / Teardown

To tear down all created resources and avoid ongoing AWS charges:
```bash
cdk destroy --all
```
