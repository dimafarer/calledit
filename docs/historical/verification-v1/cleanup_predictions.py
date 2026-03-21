#!/usr/bin/env python3
"""
Cleanup Predictions — Backup to S3 and delete legacy prediction records.

This script:
1. Scans calledit-db for all prediction records (PK starts with USER:, SK starts with PREDICTION#)
2. Backs them up to S3 (VerificationLogsBucket) as JSON
3. Deletes them from DynamoDB

Safety: dry_run=True by default. Run with --execute to actually delete.

Usage:
    # Dry run (default) — shows what would be deleted
    python cleanup_predictions.py

    # Real delete with backup
    python cleanup_predictions.py --execute
"""

import argparse
import boto3
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REGION = "us-west-2"
TABLE_NAME = "calledit-db"
# Bucket name follows SAM template pattern: ${StackName}-verification-logs-${AccountId}
S3_BUCKET = "calledit-backend-verification-logs-894249332178"


class DecimalEncoder(json.JSONEncoder):
    """Handle DynamoDB Decimal types in JSON serialization."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return super().default(obj)


def scan_prediction_records(table_name=TABLE_NAME):
    """
    Scan for all prediction records in DynamoDB.
    Returns items where PK starts with 'USER:' and SK starts with 'PREDICTION#'.
    Does NOT return TOOL# records, connection records, or any other data.
    """
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    predictions = []
    scan_kwargs = {}

    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            pk = item.get("PK", "")
            sk = item.get("SK", "")
            if pk.startswith("USER:") and sk.startswith("PREDICTION#"):
                predictions.append(item)

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    return predictions


def backup_to_s3(predictions, bucket=S3_BUCKET):
    """
    Upload prediction records to S3 as a JSON backup.
    Key: backups/predictions-backup-{timestamp}.json
    """
    if not predictions:
        logger.info("No predictions to backup.")
        return None

    s3 = boto3.client("s3", region_name=REGION)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"backups/predictions-backup-{timestamp}.json"

    body = json.dumps(predictions, cls=DecimalEncoder, indent=2)
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")

    logger.info(f"Backed up {len(predictions)} predictions to s3://{bucket}/{key}")
    return f"s3://{bucket}/{key}"


def delete_predictions(predictions, table_name=TABLE_NAME):
    """
    Delete prediction records from DynamoDB.
    Returns count of successful deletes and failures.
    """
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    deleted = 0
    failed = 0

    for item in predictions:
        try:
            table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
            deleted += 1
        except Exception as e:
            logger.error(f"Failed to delete {item['PK']}/{item['SK']}: {e}")
            failed += 1

    return deleted, failed


def cleanup_predictions(dry_run=True):
    """
    Main cleanup function. Scans, backs up, and optionally deletes predictions.
    """
    logger.info(f"Scanning {TABLE_NAME} for prediction records...")
    predictions = scan_prediction_records()
    logger.info(f"Found {len(predictions)} prediction records.")

    if not predictions:
        logger.info("Nothing to clean up.")
        return

    # Show sample
    for p in predictions[:5]:
        stmt = p.get("prediction_statement", p.get("original_prediction", "?"))[:60]
        cat = p.get("verifiable_category", "?")
        logger.info(f"  {p['PK']}/{p['SK']} — {cat} — {stmt}...")

    if len(predictions) > 5:
        logger.info(f"  ... and {len(predictions) - 5} more")

    if dry_run:
        logger.info("DRY RUN — no changes made. Use --execute to backup and delete.")
        return

    # Backup first
    backup_path = backup_to_s3(predictions)
    if backup_path:
        logger.info(f"Backup saved to {backup_path}")

    # Delete
    deleted, failed = delete_predictions(predictions)
    logger.info(f"Deleted {deleted} predictions, {failed} failures.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup and cleanup legacy predictions")
    parser.add_argument("--execute", action="store_true", help="Actually delete (default is dry run)")
    args = parser.parse_args()

    cleanup_predictions(dry_run=not args.execute)
