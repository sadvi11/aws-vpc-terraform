# Inputs for the plan-only harness.
#
# Deliberately NOT named terraform.tfvars: that filename is in .gitignore, so
# a symlink to the root one would be silently uncommitted and the plan would
# fail in CI on a variable that has no default. The harness declares its own
# inputs instead, and passes them with -var-file.

aws_region   = "ca-central-1"
project_name = "5g-core-vpc"
environment  = "dev" # the configuration validates this against dev/staging/prod

vpc_cidr             = "10.0.0.0/16"
public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24"]
availability_zones   = ["ca-central-1a", "ca-central-1b"]

# RFC 5737 reserves 203.0.113.0/24 for documentation, so this cannot resolve
# to anybody's real network.
allowed_ssh_cidr = "203.0.113.4/32"

enable_flow_logs = false
