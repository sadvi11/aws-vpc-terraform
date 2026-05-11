# AWS VPC Network Architecture — Terraform
### 5G Packet Core Architecture Applied to AWS Cloud Infrastructure

[![Terraform](https://img.shields.io/badge/Terraform-1.3%2B-7B42BC)](https://www.terraform.io)
[![AWS](https://img.shields.io/badge/AWS-ca--central--1-FF9900)](https://aws.amazon.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## Overview

This project provisions a production-grade AWS VPC network infrastructure using Terraform IaC.
The architecture is deliberately modelled on **Nokia 5G Packet Core network segmentation principles** —
the same distributed systems thinking used to manage millions of concurrent mobile subscribers,
applied to cloud infrastructure design.

---

## Architecture — 5G Packet Core → AWS Mapping

The 5G Packet Core separates network functions into distinct planes with strict access control
between them. The same principle applies directly to cloud VPC design.

```
5G Packet Core                    AWS VPC Equivalent
─────────────────────────────────────────────────────────────
N6 Interface (external/UPF)   →   Internet Gateway + Public Subnet
AMF (Access & Mobility)        →   NAT Gateway (manages outbound sessions)
SMF (Session Management)       →   Route Tables (defines traffic paths)
UPF (User Plane Function)      →   Private Subnet (processes internal traffic)
Network Function Isolation     →   Security Groups + NACLs (per-tier access)
Transport Security Policy      →   NACL Rules (stateless boundary enforcement)
Network Function Access        →   IAM Roles (least-privilege per function)
CDR (Charging Data Records)    →   VPC Flow Logs (full traffic audit trail)
```

---

## Infrastructure Diagram

```
                        INTERNET
                            │
                    ┌───────▼───────┐
                    │ Internet      │
                    │ Gateway (IGW) │
                    └───────┬───────┘
                            │
         ┌──────────────────▼──────────────────┐
         │            VPC 10.0.0.0/16           │
         │                                      │
         │  ┌─────────────────────────────────┐ │
         │  │   PUBLIC SUBNETS (Web Tier)     │ │
         │  │   AZ1: 10.0.1.0/24             │ │
         │  │   AZ2: 10.0.2.0/24             │ │
         │  │   ┌──────────┐ ┌─────────────┐ │ │
         │  │   │  Bastion │ │ NAT Gateway │ │ │
         │  │   │   Host   │ │ (EIP)       │ │ │
         │  │   └──────────┘ └──────┬──────┘ │ │
         │  │   Security Group: Web SG        │ │
         │  │   NACL: Public NACL             │ │
         │  └─────────────────────────────────┘ │
         │                  │                   │
         │  ┌───────────────▼─────────────────┐ │
         │  │   PRIVATE SUBNETS (App + DB)    │ │
         │  │   AZ1: 10.0.10.0/24            │ │
         │  │   AZ2: 10.0.11.0/24            │ │
         │  │   ┌──────────┐ ┌─────────────┐ │ │
         │  │   │ App EC2  │ │  RDS / DB   │ │ │
         │  │   │(App SG)  │ │  (DB SG)    │ │ │
         │  │   └──────────┘ └─────────────┘ │ │
         │  │   IAM Instance Profile attached  │ │
         │  │   NACL: Private NACL             │ │
         │  └─────────────────────────────────┘ │
         └──────────────────────────────────────┘
```

---

## Resources Deployed

| Resource | Count | Description |
|---|---|---|
| VPC | 1 | Main network boundary |
| Internet Gateway | 1 | Public internet access |
| Public Subnets | 2 | One per Availability Zone |
| Private Subnets | 2 | One per Availability Zone |
| NAT Gateway | 1 | Outbound internet for private tier |
| Elastic IP | 1 | Static IP for NAT Gateway |
| Route Tables | 2 | Public + Private routing rules |
| Security Groups | 3 | Web, App, DB tiers |
| Network ACLs | 2 | Public + Private subnet boundaries |
| IAM Role | 1 | EC2 least-privilege app role |
| IAM Instance Profile | 1 | Attaches role to EC2 instances |
| VPC Flow Logs | Optional | Network audit trail to CloudWatch |

---

## Security Design

### Defence in Depth (Two Layers)

**Layer 1 — Security Groups (stateful)**
- Web SG: allows inbound 80/443 from internet, 22 from allowed CIDR only
- App SG: accepts traffic from Web SG only — no direct internet access
- DB SG: accepts traffic from App SG only — isolated from everything else

**Layer 2 — NACLs (stateless)**
- Public NACL: allows 80/443 + ephemeral ports inbound, all outbound
- Private NACL: allows VPC-internal traffic + return traffic only

**IAM Least Privilege**
- EC2 instances use instance profiles — no hardcoded credentials
- SSM access enabled — no SSH keys required for management
- S3 access scoped to project-specific bucket only

---

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.3.0
- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate credentials
- AWS account with permissions to create VPC resources

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/sadvi11/aws-vpc-terraform.git
cd aws-vpc-terraform

# 2. Initialise Terraform — downloads AWS provider
terraform init

# 3. Preview what will be created (no changes made)
terraform plan

# 4. Deploy the infrastructure
terraform apply

# 5. View outputs (VPC ID, subnet IDs, etc.)
terraform output

# 6. Destroy all resources when done (avoids AWS costs)
terraform destroy
```

---

## Configuration

Edit `terraform.tfvars` to customise:

```hcl
aws_region   = "ca-central-1"    # Change to your preferred region
project_name = "5g-core-vpc"     # Used as prefix for all resource names
environment  = "dev"              # dev | staging | prod

# Restrict SSH to your IP for security
# Find your IP: curl ifconfig.me
allowed_ssh_cidr = "YOUR_IP/32"

# Enable VPC Flow Logs for audit trail
enable_flow_logs = true
```

---

## Key Design Decisions

**Why two AZs?**
High availability — if one AZ goes down, the other handles traffic. This mirrors Nokia's
redundant node deployment across geographic locations to prevent single points of failure.

**Why NAT in public subnet only?**
Cost and architecture. A single NAT Gateway in AZ1 handles all outbound traffic from private
subnets. For production, add a second NAT in AZ2 for cross-AZ redundancy.

**Why stateful SGs AND stateless NACLs?**
Security in depth. SGs are your first line — stateful, easy to manage. NACLs are your
second line — stateless, subnet-level. Mirrors Nokia's layered transport security.

**Why IAM instance profiles instead of access keys?**
Never hardcode AWS credentials. Instance profiles rotate automatically. This is the
same principle Nokia applies to inter-NF authentication using certificates.

---

## Interview Talking Points

This project was built to demonstrate cloud networking knowledge for cloud engineer and
DevOps engineer roles in Canada. Key concepts demonstrated:

- VPC design with public/private subnet segregation
- NAT Gateway for private subnet internet access without public exposure
- Security Groups vs NACLs — when to use each
- IAM least-privilege design without hardcoded credentials
- Terraform IaC with reusable variable-driven configuration
- Multi-AZ deployment for high availability

The architecture maps directly to Nokia 5G Packet Core segmentation — AMF/SMF/UPF function
isolation mirrors web/app/db tier isolation. Same distributed systems thinking, different tools.

---

## Author

**Sadhvi Sharma** — Cloud & AI Engineer  
Nokia India (5G Packet Core) → Cloud Engineering  
Calgary, AB, Canada  

[LinkedIn](https://linkedin.com/in/sadhvi-sharma-5789a6249) | [GitHub](https://github.com/sadvi11)
