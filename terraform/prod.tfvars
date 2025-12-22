project_name             = "twin"
environment              = "prod"
bedrock_model_id         = "arn:aws:bedrock:us-east-2:472730590621:inference-profile/global.amazon.nova-2-lite-v1:0"
lambda_timeout           = 60
api_throttle_burst_limit = 10
api_throttle_rate_limit  = 10
use_custom_domain        = true
root_domain              = "darindigitaltwin.com"