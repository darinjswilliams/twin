#!/bin/bash

echo "🚨 Starting AWS IAM cleanup for GitHub OIDC roles..."

# IAM Role Name
ROLE_NAME="github-actions-twin-deploy"


# Delete policy attachments
POLICIES=(
  "AWSLambda_FullAccess"
  "AmazonS3FullAccess"
  "AmazonAPIGatewayAdministrator"
  "CloudFrontFullAccess"
  "IAMReadOnlyAccess"
  "AmazonBedrockFullAccess"
  "AmazonDynamoDBFullAccess"
  "AWSCertificateManagerFullAccess"
  "AmazonRoute53FullAccess"
)

for POLICY in "${POLICIES[@]}"; do
  echo "🔸 Detaching $POLICY from $ROLE_NAME..."
  aws iam detach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/$POLICY"
 
done

# Delete inline policy
echo "🔸 Deleting inline policy github-actions-additional..."
aws iam delete-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "github-actions-additional"


# Delete IAM role
echo "🧨 Deleting IAM role $ROLE_NAME..."
aws iam delete-role \
  --role-name "$ROLE_NAME" \
  

# Delete OIDC provider
echo "🧨 Deleting GitHub OIDC provider..."
aws iam delete-open-id-connect-provider \
  --open-id-connect-provider-arn arn:aws:iam::472730590621:oidc-provider/token.actions.githubusercontent.com

echo "✅ IAM cleanup complete. You can now rerun your targeted terraform apply."
