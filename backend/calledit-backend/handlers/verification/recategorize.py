#!/usr/bin/env python3
"""
Re-categorization Pipeline

Scans all 'automatable' predictions and re-runs each through the full
prediction graph (Parser → Categorizer → VB → Review). If the category
changes (e.g., to 'auto_verifiable' because a new tool was registered),
updates the DynamoDB record.

Run this after registering a new tool in the tool registry.

Usage:
    python recategorize.py              # dry run
    python recategorize.py --execute    # real run
"""

import argparse
import sys
import os
import json
import logging
import boto3
from decimal import Decimal

# Add strands_make_call to path for prediction graph import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'strands_make_call'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TABLE_NAME = "calledit-db"
REGION = "us-west-2"


def scan_automatable_predictions(table_name=TABLE_NAME):
    """Scan all predictions with verifiable_category = 'automatable'."""
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    predictions = []
    scan_kwargs = {}

    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            pk = item.get("PK", "")
            sk = item.get("SK", "")
            cat = item.get("verifiable_category", "")
            if pk.startswith("USER:") and sk.startswith("PREDICTION#") and cat == "automatable":
                predictions.append(item)
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    logger.info(f"Found {len(predictions)} automatable predictions")
    return predictions


def recategorize_prediction(prediction: dict) -> dict:
    """
    Re-run a single prediction through the full prediction graph.
    Returns the new pipeline output dict.
    """
    from prediction_graph import execute_prediction_graph

    statement = prediction.get("prediction_statement", prediction.get("original_prediction", ""))
    if not statement:
        raise ValueError(f"No prediction statement found in record {prediction.get('SK')}")

    # Build the prompt the same way the Lambda handler does for round 1
    prompt = f"PREDICTION: {statement}"

    result = execute_prediction_graph(prompt)
    return result


def update_prediction_record(prediction: dict, new_data: dict, table_name=TABLE_NAME):
    """Update the DDB prediction record with new pipeline output."""
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    update_fields = {}
    for key in ["verifiable_category", "category_reasoning", "prediction_statement",
                 "verification_date", "date_reasoning", "verification_method"]:
        if key in new_data and new_data[key]:
            update_fields[key] = new_data[key]

    if not update_fields:
        return False

    update_expr_parts = []
    expr_attr_values = {}
    expr_attr_names = {}

    for i, (key, value) in enumerate(update_fields.items()):
        placeholder = f":val{i}"
        name_placeholder = f"#attr{i}"
        update_expr_parts.append(f"{name_placeholder} = {placeholder}")
        expr_attr_values[placeholder] = value
        expr_attr_names[name_placeholder] = key

    update_expr = "SET " + ", ".join(update_expr_parts)

    table.update_item(
        Key={"PK": prediction["PK"], "SK": prediction["SK"]},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_attr_values,
        ExpressionAttributeNames=expr_attr_names
    )
    return True


def run_recategorization(dry_run=True):
    """
    Main entry point. Scans automatable predictions, re-runs through pipeline,
    updates DDB if category changed.
    """
    predictions = scan_automatable_predictions()
    stats = {"scanned": len(predictions), "recategorized": 0, "unchanged": 0, "errors": 0}

    for i, prediction in enumerate(predictions, 1):
        stmt = prediction.get("prediction_statement", "?")[:50]
        old_cat = prediction.get("verifiable_category", "?")
        logger.info(f"[{i}/{len(predictions)}] Re-running: {stmt}...")

        try:
            new_data = recategorize_prediction(prediction)
            new_cat = new_data.get("verifiable_category", old_cat)

            if new_cat != old_cat:
                if dry_run:
                    logger.info(f"  WOULD recategorize: {old_cat} → {new_cat}")
                else:
                    update_prediction_record(prediction, new_data)
                    logger.info(f"  Recategorized: {old_cat} → {new_cat}")
                stats["recategorized"] += 1
            else:
                logger.info(f"  Unchanged: {old_cat}")
                stats["unchanged"] += 1

        except Exception as e:
            logger.error(f"  Error: {e}")
            stats["errors"] += 1

    logger.info(f"\nResults: {json.dumps(stats, indent=2)}")
    assert stats["scanned"] == stats["recategorized"] + stats["unchanged"] + stats["errors"]
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-categorize automatable predictions")
    parser.add_argument("--execute", action="store_true", help="Actually update DDB (default is dry run)")
    args = parser.parse_args()

    run_recategorization(dry_run=not args.execute)
