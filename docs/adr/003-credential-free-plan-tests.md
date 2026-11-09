# ADR 003: Verify security properties from a plan, with no AWS account

Status: accepted

## Context
`terraform fmt` and `terraform validate` accept any syntactically valid
configuration, including an unsafe one. A public portfolio repo should not need
AWS credentials in CI.

## Options considered
1. fmt and validate only.
2. Plan against a real account (needs credentials in CI).
3. **Plan with a provider configured to skip credential checks**, export the
   plan as JSON, and assert on it with pytest (chosen). `tests/plan/` symlinks
   the root `.tf` files and adds a provider override.
4. Policy-as-code tools (OPA/Conftest, Checkov) on the plan JSON.

## Decision
Option 3, plus `tests/verify_controls_fail.py`, which deliberately breaks each
control and checks that a test fails, so the assertions are shown to be able to
fail. tflint and a Trivy configuration scan were added alongside as extra
credential-free signals.

## Consequences
- The plan cannot see values that are only known after apply, and it does not
  prove anything about a running environment.
- Because `tests/plan/` symlinks the root files, the tests always plan the real
  configuration rather than a copy that could drift.
- Option 4 is a natural next step if rules need to be shared across repos.
