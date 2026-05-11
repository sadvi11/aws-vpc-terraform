aws_region   = "ca-central-1"
project_name = "5g-core-vpc"
environment  = "dev"

vpc_cidr             = "10.0.0.0/16"
public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24"]
availability_zones   = ["ca-central-1a", "ca-central-1b"]

# Replace YOUR_IP with: curl ifconfig.me
allowed_ssh_cidr = "YOUR_IP/32"

enable_flow_logs = false
