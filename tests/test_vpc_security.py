"""Does the three-tier VPC actually refuse what the README says it refuses?

A three-tier VPC diagram is easy to draw and easy to get wrong, because the
part that matters is invisible: not what the tiers connect to, but what they
cannot reach. Every tier having a security group is not segmentation. The
database being unreachable from the internet is.

So most of these assert negatives - no CIDR ingress on the database tier, no
internet gateway route on the private subnets, port 22 open to nobody. A
negative is the thing that silently stops being true. Somebody widens a rule
to unblock a deployment at 2am, the tier boundary quietly disappears, and
nothing fails until it is found from outside.

The plan comes from tests/plan, which runs this exact configuration through a
provider that skips credential validation, so none of this needs an AWS
account and none of it creates a billable resource.

WHAT THIS DOES NOT DO
---------------------
It does not send packets. Reachability in AWS is the intersection of route
tables, security groups and NACLs, and a plan shows configuration rather than
behaviour. These assert the intent is correct - which is where the design is
expressed and where it actually breaks. A test that claims more than that
would be claiming more than a plan can support.

One structural note. At plan time a security group ID is not yet known, so
`security_groups` on an ingress rule is absent from planned values entirely.
What IS present is `cidr_blocks`. That turns out to be the useful half: the
dangerous change is somebody adding a CIDR to a tier that should only ever
accept traffic from another security group, and an empty cidr_blocks is
exactly the assertion that catches it. Where the reference itself matters, the
tests read the plan's configuration section instead.
"""
import json
import os

import pytest

PLAN = os.path.join(os.path.dirname(__file__), "plan", "plan.json")

WORLD = "0.0.0.0/0"


@pytest.fixture(scope="module")
def plan():
    if not os.path.exists(PLAN):
        pytest.fail(
            f"{PLAN} not found. Generate it first:\n"
            f"  cd tests/plan && terraform init -backend=false && "
            f"terraform plan -refresh=false -out=tfplan && "
            f"terraform show -json tfplan > plan.json")
    with open(PLAN) as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def resources(plan):
    out = []

    def walk(module):
        out.extend(r for r in module.get("resources", []) if "values" in r)
        for child in module.get("child_modules", []):
            walk(child)

    walk(plan["planned_values"]["root_module"])
    return out


@pytest.fixture(scope="module")
def config(plan):
    return plan["configuration"]["root_module"]["resources"]


def by_type(resources, type_, name=None):
    return [r for r in resources
            if r["type"] == type_ and (name is None or r["name"] == name)]


def sg(resources, name):
    found = by_type(resources, "aws_security_group", name)
    assert found, f"security group '{name}' is not in the plan"
    return found[0]["values"]


def cfg_of(config, type_, name):
    found = [c for c in config if c["type"] == type_ and c["name"] == name]
    assert found, f"{type_}.{name} not found in plan configuration"
    return found[0]


# ── The plan itself ──────────────────────────────────────────────────────────

def test_the_plan_was_produced_without_an_aws_account(resources):
    """If this file exists at all, the harness planned with no credentials."""
    assert len(resources) >= 20, "plan looks truncated"


# ── The database tier is the thing worth protecting ──────────────────────────

def test_the_database_accepts_no_traffic_from_any_cidr_block(resources):
    """The tier that holds the data must only ever be reachable from another
    security group. A CIDR here is how a database ends up internet-facing."""
    for rule in sg(resources, "db")["ingress"]:
        assert rule["cidr_blocks"] == [], (
            f"db tier accepts {rule['from_port']} from {rule['cidr_blocks']}; "
            f"it must only accept traffic from the app tier's security group")
        assert rule["ipv6_cidr_blocks"] == []


def _ingress_refs(config, name):
    """Terraform flattens the references from every ingress block of a
    security group into one list, which is exactly the granularity needed
    here: the question is which tiers this tier will accept from at all."""
    return cfg_of(config, "aws_security_group", name)["expressions"]["ingress"]["references"]


def test_the_database_is_reachable_only_from_the_app_tier(config):
    """Not from the web tier. Web straight to database is the shortcut that
    turns a three-tier design back into a two-tier one, and it is the change
    most likely to be made in a hurry."""
    refs = _ingress_refs(config, "db")
    assert any("aws_security_group.app" in r for r in refs), \
        f"db ingress does not reference the app tier: {refs}"
    assert not any("aws_security_group.web" in r for r in refs), \
        "db tier accepts traffic from the web tier, skipping the app tier"


def test_the_app_tier_is_reachable_only_from_the_web_tier(config):
    """The other half of the chain. Traffic enters at web, and each hop is
    one tier deep: web -> app -> db, with no rung skipped in either direction."""
    refs = _ingress_refs(config, "app")
    assert any("aws_security_group.web" in r for r in refs), \
        f"app ingress does not reference the web tier: {refs}"
    assert not any("aws_security_group.db" in r for r in refs), \
        "app tier accepts traffic from the db tier - the chain runs backwards"


def test_the_database_does_not_expose_database_ports_to_the_world(resources):
    for rule in sg(resources, "db")["ingress"]:
        if rule["from_port"] in (3306, 5432):
            assert WORLD not in rule["cidr_blocks"]


# ── SSH ──────────────────────────────────────────────────────────────────────

def test_no_security_group_opens_ssh_to_the_internet(resources):
    """The regression this exists for: allowed_ssh_cidr used to default to
    0.0.0.0/0, so a plan that omitted the variable opened port 22 to everyone
    while the README described the rule as restricted."""
    for group in by_type(resources, "aws_security_group"):
        for rule in group["values"]["ingress"]:
            if rule["from_port"] <= 22 <= rule["to_port"]:
                assert WORLD not in rule["cidr_blocks"], (
                    f"{group['name']} tier opens SSH to the world")


def test_only_the_web_tier_accepts_traffic_from_the_internet(resources):
    """Public ingress belongs at the edge and nowhere behind it."""
    for name in ("app", "db"):
        for rule in sg(resources, name)["ingress"]:
            assert WORLD not in rule["cidr_blocks"], (
                f"{name} tier is directly internet-facing")


def test_the_web_tier_accepts_only_http_https_and_ssh(resources):
    ports = sorted(r["from_port"] for r in sg(resources, "web")["ingress"])
    assert ports == [22, 80, 443], f"unexpected web tier ports: {ports}"


# ── The default security group ───────────────────────────────────────────────

def test_the_default_security_group_allows_nothing(resources):
    """AWS creates a default security group permitting all traffic between
    anything attached to it. It cannot be deleted, so the only way to make it
    safe is to strip every rule - which is what declaring it with no ingress
    or egress does. Anything launched without an explicit group lands here."""
    default = by_type(resources, "aws_default_security_group")
    assert default, "the default security group is not managed by Terraform"
    values = default[0]["values"]
    assert not values.get("ingress"), "default security group has ingress rules"
    assert not values.get("egress"), "default security group has egress rules"


# ── Routing ──────────────────────────────────────────────────────────────────

def test_private_subnets_have_no_route_to_the_internet_gateway(config):
    """Private subnets egress through NAT. A route to the internet gateway
    makes them public, whatever they are named."""
    refs = cfg_of(config, "aws_route_table", "private")["expressions"]["route"]["references"]
    assert any("aws_nat_gateway" in r for r in refs), \
        f"private route table does not route through NAT: {refs}"
    assert not any("aws_internet_gateway" in r for r in refs), \
        "private subnets route to the internet gateway - they are not private"


def test_public_subnets_route_through_the_internet_gateway(config):
    refs = cfg_of(config, "aws_route_table", "public")["expressions"]["route"]["references"]
    assert any("aws_internet_gateway" in r for r in refs)


def test_private_subnets_do_not_assign_public_addresses(resources):
    for subnet in by_type(resources, "aws_subnet", "private"):
        assert subnet["values"]["map_public_ip_on_launch"] is False, \
            "a private subnet auto-assigns public IPs"


# ── Availability ─────────────────────────────────────────────────────────────

def test_both_tiers_span_at_least_two_availability_zones(resources):
    """A single-AZ subnet layout is a single point of failure that a diagram
    will not show."""
    for name in ("public", "private"):
        zones = {s["values"]["availability_zone"]
                 for s in by_type(resources, "aws_subnet", name)}
        assert len(zones) >= 2, f"{name} subnets occupy only {zones}"


def test_every_subnet_is_associated_with_a_route_table(resources):
    subnets = len(by_type(resources, "aws_subnet"))
    assocs = len(by_type(resources, "aws_route_table_association"))
    assert subnets == assocs, (
        f"{subnets} subnets but {assocs} route table associations; a subnet "
        f"with no association silently falls back to the main route table")


# ── Data residency ───────────────────────────────────────────────────────────

def test_everything_is_planned_in_a_canadian_region(resources):
    """PIPEDA makes leaving the region a deliberate decision, not a default."""
    for subnet in by_type(resources, "aws_subnet"):
        assert subnet["values"]["availability_zone"].startswith("ca-central-1")


# ── The configuration refuses to accept an unsafe value ──────────────────────

def test_terraform_itself_refuses_ssh_open_to_the_world():
    """The strongest version of a control is one that cannot be configured
    wrongly in the first place. Asserting the plan is safe catches a mistake;
    refusing to produce an unsafe plan prevents it.

    Skipped when terraform is not on PATH, so the rest of the suite still runs
    anywhere.
    """
    import shutil
    import subprocess
    if not shutil.which("terraform"):
        pytest.skip("terraform not installed")

    plan_dir = os.path.join(os.path.dirname(__file__), "plan")
    if not os.path.isdir(os.path.join(plan_dir, ".terraform")):
        pytest.skip("plan harness not initialised")

    result = subprocess.run(
        ["terraform", "plan", "-refresh=false", "-input=false",
         "-var-file=plan.tfvars",
         "-var", f"allowed_ssh_cidr={WORLD}", "-out=/dev/null"],
        cwd=plan_dir, capture_output=True, text=True,
        env={**os.environ,
             "AWS_SHARED_CREDENTIALS_FILE": "/dev/null",
             "AWS_CONFIG_FILE": "/dev/null",
             "AWS_EC2_METADATA_DISABLED": "true"})

    assert result.returncode != 0, \
        "terraform accepted allowed_ssh_cidr=0.0.0.0/0; the validation is gone"
    assert "must not be 0.0.0.0/0" in (result.stderr + result.stdout)
