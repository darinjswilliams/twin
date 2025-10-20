#!/bin/bash

echo "🧹 Starting Terraform state cleanup..."

resources=(
  "data.aws_caller_identity.current"
  "aws_apigatewayv2_api.main"
  "aws_apigatewayv2_integration.lambda"
  "aws_apigatewayv2_route.get_health"
  "aws_apigatewayv2_route.get_root"
  "aws_apigatewayv2_route.post_chat"
  "aws_apigatewayv2_stage.default"
  "aws_cloudfront_distribution.main"
  "aws_iam_openid_connect_provider.github"
  "aws_iam_role.github_actions"
  "aws_iam_role.lambda_role"
  "aws_iam_role_policy_attachment.lambda_basic"
  "aws_iam_role_policy_attachment.lambda_bedrock"
  "aws_iam_role_policy_attachment.lambda_s3"
  "aws_lambda_function.api"
  "aws_lambda_permission.api_gw"
  "aws_s3_bucket.frontend"
  "aws_s3_bucket.memory"
  "aws_s3_bucket_ownership_controls.memory"
  "aws_s3_bucket_policy.frontend"
  "aws_s3_bucket_public_access_block.frontend"
  "aws_s3_bucket_public_access_block.memory"
  "aws_s3_bucket_website_configuration.frontend"
)

for resource in "${resources[@]}"; do
  echo "🔸 Removing $resource from state..."
  terraform state rm "$resource"
done

echo "✅ Terraform state cleanup complete."
