# CalledIt MakeCallStreamFunction — Docker Lambda Image
# Python 3.12 + Node.js LTS for MCP server subprocess execution (npx)
#
# SnapStart is NOT supported for container image Lambdas (Decision 66).
# Cold starts will be ~2-5s slower for agent creation. Acceptable because:
#   - MCP subprocess startup (Spec A2) would invalidate SnapStart anyway
#   - AgentCore migration is planned (Decision 68)
#   - Provisioned concurrency can mitigate if needed

FROM public.ecr.aws/lambda/python:3.12

# Install tar and xz (not included in AL2023 minimal base image)
# then install Node.js LTS (v20.x) for npx MCP server execution
RUN dnf install -y tar xz \
    && dnf clean all \
    && curl -fsSL https://nodejs.org/dist/v20.18.1/node-v20.18.1-linux-x64.tar.xz \
    | tar -xJ -C /usr/local --strip-components=1 \
    && node --version && npm --version

# Install Python dependencies
COPY handlers/strands_make_call/requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy handler source code
COPY handlers/strands_make_call/ ${LAMBDA_TASK_ROOT}/

# Set the Lambda handler
CMD ["strands_make_call_graph.lambda_handler"]
