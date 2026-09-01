#!/usr/bin/env python3
"""Break each security control on purpose and confirm a test catches it.

Fifteen passing tests are not evidence until they have been shown to fail. A
test that asserts something already impossible passes forever and protects
nothing, and that failure mode is invisible - the suite is green either way.

Each entry below is a change somebody could plausibly make to unblock
themselves: widen a rule, point a route somewhere convenient, let a subnet
hand out public addresses. The script makes the change, re-plans, runs the
suite, restores the file, and fails if the suite stayed green.

Needs terraform and no AWS account.
"""
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLAN_DIR = ROOT / "tests" / "plan"

FAULTS = [
    ("security.tf",
     '''  ingress {
    description     = "MySQL from app tier"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }''',
     '''  ingress {
    description = "MySQL from app tier"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }''',
     "the database accepts MySQL from the entire internet"),

    ("security.tf",
     '''    description = "SSH from allowed CIDR only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]''',
     '''    description = "SSH from allowed CIDR only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]''',
     "port 22 is open to the world"),

    ("security.tf",
     '''  ingress {
    description     = "PostgreSQL from app tier"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }''',
     '''  ingress {
    description     = "PostgreSQL from web tier"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
  }''',
     "the web tier reaches the database directly, skipping the app tier"),

    ("main.tf",
     '''  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }''',
     '''  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }''',
     "the private subnets route straight to the internet gateway"),

    ("main.tf",
     '''resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.main.id
''',
     '''resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.main.id

  ingress {
    protocol  = "-1"
    from_port = 0
    to_port   = 0
    self      = true
  }
''',
     "the default security group permits traffic again"),
]


def plan():
    """Re-plan and refresh plan.json. Returns True on success."""
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
           "AWS_SHARED_CREDENTIALS_FILE": "/dev/null",
           "AWS_CONFIG_FILE": "/dev/null",
           "AWS_EC2_METADATA_DISABLED": "true"}
    for cmd in (["terraform", "plan", "-refresh=false", "-input=false",
                     "-var-file=plan.tfvars", "-out=tfplan"],):
        if subprocess.run(cmd, cwd=PLAN_DIR, env=env,
                          capture_output=True).returncode != 0:
            return False
    out = subprocess.run(["terraform", "show", "-json", "tfplan"],
                         cwd=PLAN_DIR, env=env, capture_output=True, text=True)
    if out.returncode != 0:
        return False
    (PLAN_DIR / "plan.json").write_text(out.stdout)
    return True


def tests_pass():
    return subprocess.run([sys.executable, "-m", "pytest",
                           str(ROOT / "tests" / "test_vpc_security.py"), "-q"],
                          cwd=ROOT, capture_output=True).returncode == 0


def main():
    if not plan():
        print("::error::baseline plan failed; cannot run fault injection")
        return 1
    if not tests_pass():
        print("::error::the suite is red before any fault was injected")
        return 1
    print(f"baseline: plan clean, suite green\n")

    failures = 0
    for filename, good, bad, description in FAULTS:
        path = ROOT / filename
        original = path.read_text()
        if good not in original:
            print(f"::error::{filename}: anchor not found - the configuration "
                  f"moved, update FAULTS. Looking for:\n{good[:80]}")
            return 1
        path.write_text(original.replace(good, bad, 1))
        try:
            planned = plan()
            caught = not planned or not tests_pass()
        finally:
            path.write_text(original)

        if caught:
            how = "plan rejected it" if not planned else "a test failed"
            print(f"ok    caught ({how}): {description}")
        else:
            print(f"FAIL  nothing caught it: {description}")
            failures += 1

    plan()  # leave plan.json matching the restored configuration
    print()
    if failures:
        print(f"{failures} control(s) can be removed without failing anything.")
        return 1
    print(f"All {len(FAULTS)} controls are load-bearing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
