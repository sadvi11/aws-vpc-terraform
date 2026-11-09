# Built-in "terraform" ruleset only: no plugin download, no cloud credentials.
plugin "terraform" {
  enabled = true
  preset  = "recommended"
}
