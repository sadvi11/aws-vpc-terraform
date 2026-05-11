# ─────────────────────────────────────────────
#  terraform.tfvars
#  Customise these values before deploying.
#  This file is gitignored if it contains
#  secrets — but these values are safe to commit
# ─────────────────────────────────────────────

aws_region   = "ca-central-1"
project_name = "5g-core-vpc"
environment  = "dev"

# VPC and subnet CIDRs
vpc_cidr             = "10.0.0.0/16"
public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24"]
availability_zones   = ["ca-central-1a", "ca-central-1b"]

# Restrict SSH to your IP — replace with your actual IP
# Find your IP: curl ifconfig.me
allowed_ssh_cidr = "0.0.0.0/0"

# Set to true to enable VPC Flow Logs to CloudWatch
enable_flow_logs = false
