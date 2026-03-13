"""
Tests for Spec 6: WebSocket SnapStart Completion

Validates that ConnectFunction and DisconnectFunction have SnapStart enabled
in the SAM template, with correct alias integration URIs and permissions.

Properties tested:
- Property 1: SnapStart configuration completeness
- Property 2: Integration URI uses alias ARN
- Property 3: Alias permissions exist with correct route scoping
- Property 4: Existing permissions preserved
- Property 5: Handler behavior unchanged
- Property 6: IAM policies retained
"""

import json
import os
import sys
import pytest
import yaml

# Resolve paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "backend", "calledit-backend", "template.yaml")
HANDLERS_PATH = os.path.join(PROJECT_ROOT, "backend", "calledit-backend", "handlers", "websocket")

# Add handlers to path for import
sys.path.insert(0, HANDLERS_PATH)


class CFNLoader(yaml.SafeLoader):
    """YAML loader that handles CloudFormation intrinsic functions."""
    pass


# Register constructors for all CFN intrinsic function tags
def _cfn_tag_constructor(loader, tag_suffix, node):
    """Generic constructor that preserves CFN tags as tagged strings/dicts."""
    if isinstance(node, yaml.ScalarNode):
        return {"Fn::Tag": tag_suffix, "Value": loader.construct_scalar(node)}
    elif isinstance(node, yaml.SequenceNode):
        return {"Fn::Tag": tag_suffix, "Value": loader.construct_sequence(node)}
    elif isinstance(node, yaml.MappingNode):
        return {"Fn::Tag": tag_suffix, "Value": loader.construct_mapping(node)}


for tag in ["!Sub", "!Ref", "!GetAtt", "!Join", "!Select", "!Split",
            "!If", "!Not", "!Equals", "!And", "!Or", "!FindInMap",
            "!ImportValue", "!Condition", "!Transform"]:
    CFNLoader.add_constructor(
        tag, lambda loader, node, t=tag: _cfn_tag_constructor(loader, t, node)
    )


@pytest.fixture(scope="module")
def template():
    """Load and parse the SAM template with CFN intrinsic function support."""
    with open(TEMPLATE_PATH, "r") as f:
        return yaml.load(f, Loader=CFNLoader)


@pytest.fixture(scope="module")
def resources(template):
    """Extract Resources section from template."""
    return template["Resources"]


# --- Property 1: SnapStart configuration completeness ---

# Feature: websocket-snapstart, Property 1: SnapStart configuration completeness
@pytest.mark.parametrize("function_name", ["ConnectFunction", "DisconnectFunction"])
def test_snapstart_enabled(resources, function_name):
    """For any target function, SnapStart SHALL be configured with ApplyOn: PublishedVersions."""
    func = resources[function_name]
    props = func["Properties"]
    assert "SnapStart" in props, f"{function_name} missing SnapStart property"
    assert props["SnapStart"]["ApplyOn"] == "PublishedVersions"


# Feature: websocket-snapstart, Property 1: SnapStart configuration completeness
@pytest.mark.parametrize("function_name", ["ConnectFunction", "DisconnectFunction"])
def test_auto_publish_alias(resources, function_name):
    """For any target function, AutoPublishAlias SHALL be set to 'live'."""
    func = resources[function_name]
    props = func["Properties"]
    assert props.get("AutoPublishAlias") == "live", f"{function_name} missing AutoPublishAlias: live"


# --- Property 2: Integration URI uses alias ARN ---

INTEGRATION_MAP = {
    "ConnectIntegration": "ConnectFunction",
    "DisconnectIntegration": "DisconnectFunction",
}


# Feature: websocket-snapstart, Property 2: Integration URI uses alias ARN
@pytest.mark.parametrize("integration_name,function_name", INTEGRATION_MAP.items())
def test_integration_uri_uses_alias(resources, integration_name, function_name):
    """For any target integration, IntegrationUri SHALL contain :live/invocations."""
    integration = resources[integration_name]
    uri = integration["Properties"]["IntegrationUri"]
    # The URI uses !Sub, which PyYAML resolves to a dict or string depending on format
    uri_str = str(uri)
    assert ":live/invocations" in uri_str, (
        f"{integration_name} IntegrationUri should reference :live alias, got: {uri_str}"
    )


# --- Property 3: Alias permissions exist with correct route scoping ---

ALIAS_PERMISSION_MAP = {
    "ConnectFunctionAliasPermission": ("ConnectFunction", "$connect"),
    "DisconnectFunctionAliasPermission": ("DisconnectFunction", "$disconnect"),
}


# Feature: websocket-snapstart, Property 3: Alias permissions with correct route scoping
@pytest.mark.parametrize(
    "permission_name,expected",
    ALIAS_PERMISSION_MAP.items(),
)
def test_alias_permission_exists(resources, permission_name, expected):
    """For any target function, an alias-specific Lambda permission SHALL exist."""
    function_name, route = expected
    assert permission_name in resources, f"Missing {permission_name} resource"
    perm = resources[permission_name]
    assert perm["Type"] == "AWS::Lambda::Permission"
    props = perm["Properties"]

    # FunctionName should reference :live alias (rendered as CFN !Sub dict)
    fn_name = str(props["FunctionName"])
    assert ":live" in fn_name, f"{permission_name} FunctionName should reference :live alias"

    # Principal should be apigateway
    assert props["Principal"] == "apigateway.amazonaws.com"

    # SourceArn should be scoped to the correct route (rendered as CFN !Sub dict)
    source_arn = str(props["SourceArn"])
    assert route in source_arn, (
        f"{permission_name} SourceArn should be scoped to {route}, got: {source_arn}"
    )


# --- Property 4: Existing permissions preserved ---

ORIGINAL_PERMISSION_MAP = {
    "ConnectFunctionPermission": "ConnectFunction",
    "DisconnectFunctionPermission": "DisconnectFunction",
}


# Feature: websocket-snapstart, Property 4: Existing permissions preserved
@pytest.mark.parametrize("permission_name,function_name", ORIGINAL_PERMISSION_MAP.items())
def test_original_permissions_preserved(resources, permission_name, function_name):
    """Original unqualified permissions SHALL remain present and unmodified."""
    assert permission_name in resources, f"Missing original {permission_name}"
    perm = resources[permission_name]
    props = perm["Properties"]

    # FunctionName should use !Ref (unqualified) — no :live suffix
    fn_name = props["FunctionName"]
    # With CFNLoader, !Ref becomes a dict like {"Fn::Tag": "!Ref", "Value": "ConnectFunction"}
    fn_str = str(fn_name)
    assert ":live" not in fn_str, (
        f"Original {permission_name} should use unqualified FunctionName, got: {fn_str}"
    )
    # Verify it's a !Ref (not !Sub with alias)
    if isinstance(fn_name, dict):
        assert fn_name.get("Fn::Tag") == "!Ref", (
            f"Original {permission_name} should use !Ref, got tag: {fn_name.get('Fn::Tag')}"
        )
    assert props["Principal"] == "apigateway.amazonaws.com"


# --- Property 5: Handler behavior unchanged ---

# Feature: websocket-snapstart, Property 5: Handler behavior unchanged
def test_connect_handler_returns_200():
    """ConnectFunction handler SHALL return statusCode 200 with correct body."""
    from connect import lambda_handler

    event = {"requestContext": {"routeKey": "$connect", "connectionId": "test-conn-id"}}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["message"] == "Connected"


# Feature: websocket-snapstart, Property 5: Handler behavior unchanged
def test_disconnect_handler_returns_200():
    """DisconnectFunction handler SHALL return statusCode 200 with correct body."""
    from disconnect import lambda_handler

    event = {"requestContext": {"routeKey": "$disconnect", "connectionId": "test-conn-id"}}
    result = lambda_handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["message"] == "Disconnected"


# --- Property 6: IAM policies retained ---

# Feature: websocket-snapstart, Property 6: IAM policies retained
@pytest.mark.parametrize("function_name", ["ConnectFunction", "DisconnectFunction"])
def test_iam_policies_retained(resources, function_name):
    """For any target function, execute-api:ManageConnections policy SHALL be present."""
    func = resources[function_name]
    policies = func["Properties"]["Policies"]

    # Find the statement-based policy with ManageConnections
    found = False
    for policy in policies:
        if "Statement" in policy:
            for stmt in policy["Statement"]:
                actions = stmt.get("Action", [])
                if "execute-api:ManageConnections" in actions:
                    found = True
                    break
    assert found, f"{function_name} missing execute-api:ManageConnections IAM policy"
