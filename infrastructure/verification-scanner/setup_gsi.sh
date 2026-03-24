#!/bin/bash
# V4-5b: Add status-verification_date GSI to calledit-db
#
# Run once to create the GSI. The table is not CloudFormation-managed,
# so the GSI is added via CLI. Idempotent — fails gracefully if GSI exists.
#
# Usage: bash infrastructure/verification-scanner/setup_gsi.sh

set -euo pipefail

TABLE_NAME="${1:-calledit-db}"
INDEX_NAME="status-verification_date-index"

echo "Adding GSI '$INDEX_NAME' to table '$TABLE_NAME'..."

aws dynamodb update-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
    AttributeName=status,AttributeType=S \
    AttributeName=verification_date,AttributeType=S \
  --global-secondary-index-updates "[{
    \"Create\": {
      \"IndexName\": \"$INDEX_NAME\",
      \"KeySchema\": [
        {\"AttributeName\": \"status\", \"KeyType\": \"HASH\"},
        {\"AttributeName\": \"verification_date\", \"KeyType\": \"RANGE\"}
      ],
      \"Projection\": {
        \"ProjectionType\": \"INCLUDE\",
        \"NonKeyAttributes\": [\"prediction_id\"]
      }
    }
  }]" \
  --billing-mode PAY_PER_REQUEST

echo "GSI creation initiated. Waiting for it to become ACTIVE..."

aws dynamodb wait table-exists --table-name "$TABLE_NAME"

# Poll until GSI is ACTIVE (wait command only checks table, not GSI)
while true; do
  GSI_STATUS=$(aws dynamodb describe-table \
    --table-name "$TABLE_NAME" \
    --query "Table.GlobalSecondaryIndexes[?IndexName=='$INDEX_NAME'].IndexStatus" \
    --output text 2>/dev/null)

  if [ "$GSI_STATUS" = "ACTIVE" ]; then
    echo "GSI '$INDEX_NAME' is ACTIVE."
    break
  elif [ -z "$GSI_STATUS" ]; then
    echo "ERROR: GSI '$INDEX_NAME' not found on table '$TABLE_NAME'."
    exit 1
  else
    echo "GSI status: $GSI_STATUS — waiting 10s..."
    sleep 10
  fi
done
