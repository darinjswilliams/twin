#!/bin/bash

echo "🚨 Scanning and deleting IAM roles with IAM-related permissions in us-east-2..."

AWS_REGION="us-east-2"

# List of IAM actions to match
TARGET_ACTIONS=(
  "iam:CreateRole"
  "iam:DeleteRole"
  "iam:AttachRolePolicy"
  "iam:DetachRolePolicy"
  "iam:PutRolePolicy"
  "iam:DeleteRolePolicy"
  "iam:GetRole"
  "iam:GetRolePolicy"
  "iam:ListRolePolicies"
  "iam:ListAttachedRolePolicies"
  "iam:UpdateAssumeRolePolicy"
  "iam:PassRole"
  "iam:TagRole"
  "iam:UntagRole"
  "iam:ListInstanceProfilesForRole"
  "sts:GetCallerIdentity"
)

# Get all role names
ROLE_NAMES=$(aws iam list-roles --query "Roles[].RoleName" --output text --region "$AWS_REGION")

for ROLE in $ROLE_NAMES; do
  echo "🔍 Checking role: $ROLE"

  # Get inline policies
  INLINE_POLICIES=$(aws iam list-role-policies --role-name "$ROLE" --query "PolicyNames" --output text --region "$AWS_REGION")

  MATCH_FOUND=false

  for POLICY_NAME in $INLINE_POLICIES; do
    POLICY_DOC=$(aws iam get-role-policy --role-name "$ROLE" --policy-name "$POLICY_NAME" --query "PolicyDocument" --output json --region "$AWS_REGION")
    for ACTION in "${TARGET_ACTIONS[@]}"; do
      if echo "$POLICY_DOC" | grep -q "$ACTION"; then
        MATCH_FOUND=true
        break
      fi
    done
  done

  # Check attached managed policies
  ATTACHED_POLICIES=$(aws iam list-attached-role-policies --role-name "$ROLE" --query "AttachedPolicies[].PolicyArn" --output text --region "$AWS_REGION")

  for POLICY_ARN in $ATTACHED_POLICIES; do
    POLICY_VERSION=$(aws iam get-policy --policy-arn "$POLICY_ARN" --query "Policy.DefaultVersionId" --output text --region "$AWS_REGION")
    POLICY_DOC=$(aws iam get-policy-version --policy-arn "$POLICY_ARN" --version-id "$POLICY_VERSION" --query "PolicyVersion.Document" --output json --region "$AWS_REGION")
    for ACTION in "${TARGET_ACTIONS[@]}"; do
      if echo "$POLICY_DOC" | grep -q "$ACTION"; then
        MATCH_FOUND=true
        break
      fi
    done
  done

  if [ "$MATCH_FOUND" = true ]; then
    echo "🧨 Deleting role: $ROLE"
    # Detach managed policies
    for POLICY_ARN in $ATTACHED_POLICIES; do
      aws iam detach-role-policy --role-name "$ROLE" --policy-arn "$POLICY_ARN" --region "$AWS_REGION"
    done
    # Delete inline policies
    for POLICY_NAME in $INLINE_POLICIES; do
      aws iam delete-role-policy --role-name "$ROLE" --policy-name "$POLICY_NAME" --region "$AWS_REGION"
    done
    # Delete the role
    aws iam delete-role --role-name "$ROLE" --region "$AWS_REGION"
  else
    echo "✅ No matching IAM permissions found in role: $ROLE"
  fi
done

echo "🎯 Role cleanup complete."