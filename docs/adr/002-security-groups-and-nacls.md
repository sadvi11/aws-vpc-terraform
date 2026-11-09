# ADR 002: Tiered security groups as the primary control, NACLs as a coarse backstop

Status: accepted

## Context
The network has web, app and database tiers. Both security groups and network
ACLs can filter traffic, and they behave differently: security groups are
stateful and attach to network interfaces; NACLs are stateless and apply at the
subnet boundary
(https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html).

## Options considered
1. Security groups only.
2. NACLs only.
3. **Both** (chosen): security groups express the real tier-to-tier policy,
   NACLs add subnet-level rules.

## Decision
- App SG accepts 8080 (and SSH) only from the web SG; DB SG accepts 3306/5432
  only from the app SG. Referencing security groups instead of CIDRs means the
  rule follows the tier, not an IP range.
- The default security group is managed with no rules, so anything attached to
  it by accident has no network access.
- NACLs stay coarse. Because they are stateless, return traffic needs an
  ephemeral-port rule (1024-65535), which makes them a weak control by
  themselves; they are not relied on for tier isolation.

## Consequences
- Tier isolation is asserted by `tests/test_vpc_security.py` against the
  planned security groups (for example, the database has no CIDR ingress).
- The ephemeral-port NACL rules are broad on purpose. Tightening them would need
  rules per known return path and is listed under "What I'd change for
  production" in the README.
