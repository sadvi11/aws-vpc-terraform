# ADR 001: One NAT gateway, in the first public subnet

Status: accepted for this lab; revisit for production

## Context
Private-subnet instances need outbound internet access (patches, package
repositories) without being reachable from the internet. `main.tf` creates one
NAT gateway with one Elastic IP in `aws_subnet.public[0]`, and one private route
table (`0.0.0.0/0` to that gateway) shared by both private subnets.

## Options considered
1. **One NAT gateway** (chosen). Lowest cost; simplest route tables.
2. **One NAT gateway per AZ**, each private subnet routed to the gateway in its
   own AZ. Removes the cross-AZ dependency; roughly doubles the NAT gateway
   hourly charge for two AZs.
3. **NAT instance or no NAT** (VPC endpoints only). More operational work, or
   no general internet egress.

## Decision
Option 1. This project is a networking lab that is deployed, inspected and
destroyed; NAT gateway hourly and data-processing charges are the largest
running cost in it (see https://aws.amazon.com/vpc/pricing/).

## Consequences
- A NAT gateway is created in a single Availability Zone, so if that AZ is
  impaired, private subnets in the other AZ lose outbound access too. The
  README's "two AZs" claim therefore holds for the subnet layout, not for
  outbound egress.
- Traffic from the second AZ crosses AZs to reach the gateway, which can add
  cross-AZ data transfer charges.
- Moving to option 2 means a `count`-based NAT gateway/EIP and one private
  route table per AZ. See https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
