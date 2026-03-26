/**
 * DynamoDB client for the eval dashboard.
 *
 * Dev mode: uses VITE_AWS_ACCESS_KEY_ID + VITE_AWS_SECRET_ACCESS_KEY from .env
 * Production: will use API Gateway + Lambda (future — separate CF template)
 */

import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb';

const REGION = import.meta.env.VITE_AWS_REGION || 'us-west-2';

const credentials = import.meta.env.VITE_AWS_ACCESS_KEY_ID
  ? {
      accessKeyId: import.meta.env.VITE_AWS_ACCESS_KEY_ID,
      secretAccessKey: import.meta.env.VITE_AWS_SECRET_ACCESS_KEY,
      sessionToken: import.meta.env.VITE_AWS_SESSION_TOKEN || undefined,
    }
  : undefined;

const rawClient = new DynamoDBClient({
  region: REGION,
  ...(credentials ? { credentials } : {}),
});

export const ddbDocClient = DynamoDBDocumentClient.from(rawClient, {
  marshallOptions: { removeUndefinedValues: true },
});

export const REPORTS_TABLE = import.meta.env.VITE_EVAL_REPORTS_TABLE || 'calledit-v4-eval-reports';
