#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { AgentcorePermissionsStack } from '../lib/agentcore-permissions-stack';

const app = new cdk.App();
new AgentcorePermissionsStack(app, 'agentcore-permissions', {
  env: { account: '894249332178', region: 'us-west-2' },
});
