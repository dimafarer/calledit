/**
 * Vite dev server middleware — proxies eval dashboard DDB calls.
 * Runs server-side (Node.js) so it can use ~/.aws/credentials.
 * Only active during `npm run dev`, not in production builds.
 *
 * Endpoints:
 *   GET /api/eval/reports?agent=creation     → list reports (metadata only)
 *   GET /api/eval/report?agent=creation&ts=X → get full report
 */

import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, QueryCommand, GetCommand } from '@aws-sdk/lib-dynamodb';
import type { Plugin } from 'vite';

const REGION = process.env.VITE_AWS_REGION || 'us-west-2';
const TABLE = process.env.VITE_EVAL_REPORTS_TABLE || 'calledit-v4-eval-reports';

// Node.js SDK picks up ~/.aws/credentials automatically
const rawClient = new DynamoDBClient({ region: REGION });
const ddb = DynamoDBDocumentClient.from(rawClient);

export function evalApiPlugin(): Plugin {
  return {
    name: 'eval-api',
    configureServer(server) {
      // List reports for an agent type
      server.middlewares.use('/api/eval/reports', async (req, res) => {
        try {
          const url = new URL(req.url!, `http://${req.headers.host}`);
          const agent = url.searchParams.get('agent');
          if (!agent) {
            res.statusCode = 400;
            res.end(JSON.stringify({ error: 'agent param required' }));
            return;
          }

          const result = await ddb.send(new QueryCommand({
            TableName: TABLE,
            KeyConditionExpression: 'PK = :pk',
            ExpressionAttributeValues: { ':pk': `AGENT#${agent}` },
            ProjectionExpression: 'PK, SK, run_metadata, aggregate_scores',
            ScanIndexForward: false,
          }));

          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify(result.Items ?? []));
        } catch (e: any) {
          console.error('eval-api list error:', e.message);
          res.statusCode = 500;
          res.end(JSON.stringify({ error: e.message }));
        }
      });

      // Get full report
      server.middlewares.use('/api/eval/report', async (req, res) => {
        try {
          const url = new URL(req.url!, `http://${req.headers.host}`);
          const agent = url.searchParams.get('agent');
          const ts = url.searchParams.get('ts');
          if (!agent || !ts) {
            res.statusCode = 400;
            res.end(JSON.stringify({ error: 'agent and ts params required' }));
            return;
          }

          const pk = `AGENT#${agent}`;
          const result = await ddb.send(new GetCommand({
            TableName: TABLE,
            Key: { PK: pk, SK: ts },
          }));

          if (!result.Item) {
            res.statusCode = 404;
            res.end(JSON.stringify({ error: 'not found' }));
            return;
          }

          const report = result.Item;

          // Reassemble split case_results
          if (report.case_results_split) {
            const casesResult = await ddb.send(new GetCommand({
              TableName: TABLE,
              Key: { PK: pk, SK: `${ts}#CASES` },
            }));
            report.case_results = casesResult.Item?.case_results ?? [];
            delete report.case_results_split;
          }

          // Remove DDB keys
          delete report.PK;
          delete report.SK;

          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify(report));
        } catch (e: any) {
          console.error('eval-api get error:', e.message);
          res.statusCode = 500;
          res.end(JSON.stringify({ error: e.message }));
        }
      });
    },
  };
}
