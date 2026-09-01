# Plan-only harness.
#
# The root configuration is symlinked in beside this file, so the tests plan
# exactly the files that would be applied rather than a copy that can drift
# out of step with them.
#
# This is an override file, so its provider block MERGES into the one declared
# in main.tf instead of colliding with it. The only things added are the skip
# flags, which is what lets `terraform plan` run with no AWS account: without
# them the provider calls STS GetCallerIdentity and fails before producing a
# plan.
#
# Named provider_override.tf and not main.tf: main.tf is one of the symlinked
# filenames, and writing to that name here would overwrite the real
# configuration through the symlink.

provider "aws" {
  region                      = "ca-central-1"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  access_key                  = "test"
  secret_key                  = "test"
}
