data "aws_caller_identity" "current" {}

locals {
  aliases = False and "sentientops.com" != "" ? [
    "sentientops.com",
    "www.sentientops.com"
  ] : []

  name_prefix = "sentientops-dev"

  common_tags = {
    Project     = "sentientops"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}