# AWS CDK v2 Production-Ready 3-Tier Web Application Infrastructure

This repository contains production-ready Infrastructure-as-Code (IaC) written in **AWS CDK v2 (Python)** to provision a highly available, decoupled 3-Tier Web Application architecture across 2 Availability Zones (`ap-south-1a`, `ap-south-1b`) inside a custom Amazon VPC (`10.0.0.0/16`).

---

## 🏗️ Architecture Topology

```
                          +------------------------------------+
                          |     AWS Route 53 Hosted Zone       |
                          |     (A-Record Alias to ALB)        |
                          +------------------------------------+
                                           |
                                           v
                        +---------------------------------------+
                        |   External Internet-Facing ALB (80)   |
                        |         [External-ALB-SG]             |
                        +---------------------------------------+
                                           |
                                           v (Public Subnets: 10.0.1.0/24, 10.0.2.0/24)
                        +---------------------------------------+
                        |        Web Tier ASG (Port 80/5000)    |
                        |           [Web-Tier-SG]               |
                        |       (Role: Avashya-EC2-Web-Role)    |
                        +---------------------------------------+
                                           |
                                           v (HTTP: 8000 - Internal Traffic)
                        +---------------------------------------+
                        |        Internal App ALB (8000)        |
                        |         [Internal-ALB-SG]             |
                        +---------------------------------------+
                                           |
                                           v (Private App Subnets: 10.0.10.0/24, 10.0.20.0/24)
                        +---------------------------------------+
                        |        App Tier ASG (Port 8000)       |
                        |           [App-Tier-SG]               |
                        |      (Role: Avashya-EC2-App-Role)     |
                        +---------------------------------------+
                            /                               \
                           /                                 \
                          v                                   v (PostgreSQL: 5432)
       +------------------------------------+      +-----------------------------------+
       |     S3 Gateway VPC Endpoint        |      | Amazon RDS PostgreSQL (Multi-AZ)  |
       |  (s3://avashya-drop-uploads-2026)  |      |         [RDS-Database-SG]         |
       +------------------------------------+      | Isolated DB Subnets: 10.0.100/200 |
                                                   +-----------------------------------+
```

---

## 📦 Stack & File Structure Breakdown

| Path | Description |
| :--- | :--- |
| [`app.py`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/app.py) | Main CDK Application entrypoint orchestrating stack deployment |
| [`stacks/vpc_stack.py`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/stacks/vpc_stack.py) | Custom VPC `10.0.0.0/16` across 2 AZs (6 subnets, IGW, 2 NAT Gateways, S3 VPC Endpoint) |
| [`stacks/security_stack.py`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/stacks/security_stack.py) | Custom IAM Roles (`Avashya-EC2-App-Role`, `Avashya-EC2-Web-Role`) & 5 chained Security Groups |
| [`stacks/storage_db_stack.py`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/stacks/storage_db_stack.py) | Private S3 Bucket (`avashya-drop-uploads-2026`) & Multi-AZ RDS PostgreSQL with IAM Auth |
| [`stacks/compute_stack.py`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/stacks/compute_stack.py) | External ALB, Internal ALB, Launch Templates (`avashya-web-lt`, `avashya-app-lt`), and ASGs |
| [`stacks/route53_stack.py`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/stacks/route53_stack.py) | Route 53 Public Hosted Zone and Alias A-Records pointing public domain to External ALB |
| [`scripts/userdata_web.sh`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/scripts/userdata_web.sh) | Web Tier UserData boot script (Nginx reverse proxy, CloudWatch agent, SPA setup) |
| [`scripts/userdata_app.sh`](file:///c:/Users/nishad/Desktop/AvashyaApp%231CDK/scripts/userdata_app.sh) | App Tier UserData boot script (FastAPI setup, CloudWatch agent, RDS & S3 env vars) |

---

## 🔒 Security Group Chaining Matrix

| Security Group | Inbound Source | Port(s) | Description |
| :--- | :--- | :--- | :--- |
| `External-ALB-SG` | `0.0.0.0/0` | `80`, `443` | Allows public internet HTTP/HTTPS traffic |
| `Web-Tier-SG` | `External-ALB-SG` | `80`, `5000` | Allows traffic ONLY from External ALB |
| `Internal-ALB-SG` | `Web-Tier-SG` | `8000` | Allows internal API traffic ONLY from Web Tier |
| `App-Tier-SG` | `Internal-ALB-SG` | `8000` | Allows API service requests ONLY from Internal ALB |
| `RDS-Database-SG` | `App-Tier-SG` | `5432` | Allows PostgreSQL connections ONLY from App Tier |

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
