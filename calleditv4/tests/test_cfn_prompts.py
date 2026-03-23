"""CloudFormation template validation tests for V4 creation prompts.

Parses infrastructure/prompt-management/template.yaml directly — no AWS calls.
Validates Requirements 2.1–2.7.
"""

import os
import yaml
import pytest

TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "infrastructure",
    "prompt-management",
    "template.yaml",
)


def _cfn_tag_constructor(loader, tag_suffix, node):
    """Handle CloudFormation intrinsic functions (!GetAtt, !Ref, !Sub, etc.)."""
    if isinstance(node, yaml.ScalarNode):
        return {f"Fn::{tag_suffix}": loader.construct_scalar(node)}
    if isinstance(node, yaml.SequenceNode):
        return {f"Fn::{tag_suffix}": loader.construct_sequence(node)}
    if isinstance(node, yaml.MappingNode):
        return {f"Fn::{tag_suffix}": loader.construct_mapping(node)}
    return None


class _CfnLoader(yaml.SafeLoader):
    """YAML loader that handles CloudFormation intrinsic function tags."""
    pass


# Register all common CFN intrinsic functions
for _tag in ("GetAtt", "Ref", "Sub", "Join", "Select", "Split",
             "If", "Equals", "And", "Or", "Not", "FindInMap",
             "GetAZs", "ImportValue", "Base64", "Cidr"):
    _CfnLoader.add_multi_constructor(
        f"!{_tag}", lambda loader, suffix, node, t=_tag: _cfn_tag_constructor(loader, t, node)
    )

# Also handle !Ref as a single-tag constructor (most common)
_CfnLoader.add_constructor(
    "!Ref", lambda loader, node: {"Ref": loader.construct_scalar(node)}
)
_CfnLoader.add_constructor(
    "!GetAtt", lambda loader, node: {"Fn::GetAtt": loader.construct_scalar(node)}
)
_CfnLoader.add_constructor(
    "!Sub", lambda loader, node: {"Fn::Sub": loader.construct_scalar(node)}
)


@pytest.fixture(scope="module")
def template():
    """Load and parse the CloudFormation template."""
    with open(TEMPLATE_PATH, "r") as f:
        return yaml.load(f, Loader=_CfnLoader)


@pytest.fixture(scope="module")
def resources(template):
    return template["Resources"]


@pytest.fixture(scope="module")
def outputs(template):
    return template["Outputs"]


# =========================================================================
# Req 2.1 — calledit-prediction-parser resource with {{current_date}}
# =========================================================================
class TestPredictionParserPrompt:
    def test_resource_exists(self, resources):
        assert "PredictionParserPrompt" in resources

    def test_resource_type(self, resources):
        assert resources["PredictionParserPrompt"]["Type"] == "AWS::Bedrock::Prompt"

    def test_name(self, resources):
        props = resources["PredictionParserPrompt"]["Properties"]
        assert props["Name"] == "calledit-prediction-parser"

    def test_current_date_variable(self, resources):
        props = resources["PredictionParserPrompt"]["Properties"]
        variant = props["Variants"][0]
        text = variant["TemplateConfiguration"]["Text"]["Text"]
        assert "{{current_date}}" in text

    def test_input_variables_declared(self, resources):
        props = resources["PredictionParserPrompt"]["Properties"]
        variant = props["Variants"][0]
        input_vars = variant["TemplateConfiguration"]["Text"]["InputVariables"]
        var_names = [v["Name"] for v in input_vars]
        assert "current_date" in var_names


# =========================================================================
# Req 2.2 — calledit-verification-planner resource with {{tool_manifest}}
# =========================================================================
class TestVerificationPlannerPrompt:
    def test_resource_exists(self, resources):
        assert "VerificationPlannerPrompt" in resources

    def test_resource_type(self, resources):
        assert resources["VerificationPlannerPrompt"]["Type"] == "AWS::Bedrock::Prompt"

    def test_name(self, resources):
        props = resources["VerificationPlannerPrompt"]["Properties"]
        assert props["Name"] == "calledit-verification-planner"

    def test_tool_manifest_variable(self, resources):
        props = resources["VerificationPlannerPrompt"]["Properties"]
        variant = props["Variants"][0]
        text = variant["TemplateConfiguration"]["Text"]["Text"]
        assert "{{tool_manifest}}" in text

    def test_input_variables_declared(self, resources):
        props = resources["VerificationPlannerPrompt"]["Properties"]
        variant = props["Variants"][0]
        input_vars = variant["TemplateConfiguration"]["Text"]["InputVariables"]
        var_names = [v["Name"] for v in input_vars]
        assert "tool_manifest" in var_names


# =========================================================================
# Req 2.3 — calledit-plan-reviewer resource
# =========================================================================
class TestPlanReviewerPrompt:
    def test_resource_exists(self, resources):
        assert "PlanReviewerPrompt" in resources

    def test_resource_type(self, resources):
        assert resources["PlanReviewerPrompt"]["Type"] == "AWS::Bedrock::Prompt"

    def test_name(self, resources):
        props = resources["PlanReviewerPrompt"]["Properties"]
        assert props["Name"] == "calledit-plan-reviewer"

    def test_scoring_dimensions_in_prompt(self, resources):
        """Verify the 5 scoring dimensions are present in the prompt text."""
        props = resources["PlanReviewerPrompt"]["Properties"]
        variant = props["Variants"][0]
        text = variant["TemplateConfiguration"]["Text"]["Text"]
        assert "Criteria Specificity" in text
        assert "Source Availability" in text
        assert "Temporal Clarity" in text
        assert "Outcome Objectivity" in text
        assert "Tool Coverage" in text

    def test_scoring_weights_in_prompt(self, resources):
        """Verify the 5 scoring dimension weights are present."""
        props = resources["PlanReviewerPrompt"]["Properties"]
        variant = props["Variants"][0]
        text = variant["TemplateConfiguration"]["Text"]["Text"]
        assert "30%" in text
        assert "25%" in text
        assert "20%" in text
        assert "15%" in text
        assert "10%" in text


# =========================================================================
# Req 2.4 — Each new prompt has a PromptVersion resource
# =========================================================================
class TestPromptVersions:
    def test_prediction_parser_version_exists(self, resources):
        assert "PredictionParserPromptVersion" in resources

    def test_prediction_parser_version_type(self, resources):
        r = resources["PredictionParserPromptVersion"]
        assert r["Type"] == "AWS::Bedrock::PromptVersion"

    def test_verification_planner_version_exists(self, resources):
        assert "VerificationPlannerPromptVersion" in resources

    def test_verification_planner_version_type(self, resources):
        r = resources["VerificationPlannerPromptVersion"]
        assert r["Type"] == "AWS::Bedrock::PromptVersion"

    def test_plan_reviewer_version_exists(self, resources):
        assert "PlanReviewerPromptVersion" in resources

    def test_plan_reviewer_version_type(self, resources):
        r = resources["PlanReviewerPromptVersion"]
        assert r["Type"] == "AWS::Bedrock::PromptVersion"


# =========================================================================
# Req 2.5 — Each new prompt has Project: calledit and Agent: creation tags
# =========================================================================
class TestPromptTags:
    @pytest.mark.parametrize("resource_name", [
        "PredictionParserPrompt",
        "VerificationPlannerPrompt",
        "PlanReviewerPrompt",
    ])
    def test_project_tag(self, resources, resource_name):
        tags = resources[resource_name]["Properties"]["Tags"]
        assert tags["Project"] == "calledit"

    @pytest.mark.parametrize("resource_name", [
        "PredictionParserPrompt",
        "VerificationPlannerPrompt",
        "PlanReviewerPrompt",
    ])
    def test_agent_tag(self, resources, resource_name):
        tags = resources[resource_name]["Properties"]["Tags"]
        assert tags["Agent"] == "creation"


# =========================================================================
# Req 2.6 — Template outputs include new prompt IDs and ARNs
# =========================================================================
class TestNewOutputs:
    @pytest.mark.parametrize("output_key", [
        "PredictionParserPromptId",
        "PredictionParserPromptArn",
        "VerificationPlannerPromptId",
        "VerificationPlannerPromptArn",
        "PlanReviewerPromptId",
        "PlanReviewerPromptArn",
    ])
    def test_output_exists(self, outputs, output_key):
        assert output_key in outputs


# =========================================================================
# Req 2.7 — Existing v3 prompts still present and unchanged
# =========================================================================
class TestV3PromptsUnchanged:
    V3_PROMPT_RESOURCES = [
        "ParserPrompt",
        "CategorizerPrompt",
        "VBPrompt",
        "ReviewPrompt",
    ]

    V3_VERSION_RESOURCES = [
        "ParserPromptVersion",
        "CategorizerPromptVersion",
        "VBPromptVersion",
        "ReviewPromptVersion",
    ]

    V3_OUTPUTS = [
        "ParserPromptId",
        "ParserPromptArn",
        "CategorizerPromptId",
        "CategorizerPromptArn",
        "VBPromptId",
        "VBPromptArn",
        "ReviewPromptId",
        "ReviewPromptArn",
    ]

    @pytest.mark.parametrize("resource_name", V3_PROMPT_RESOURCES)
    def test_v3_prompt_resource_exists(self, resources, resource_name):
        assert resource_name in resources

    @pytest.mark.parametrize("resource_name", V3_PROMPT_RESOURCES)
    def test_v3_prompt_type(self, resources, resource_name):
        assert resources[resource_name]["Type"] == "AWS::Bedrock::Prompt"

    @pytest.mark.parametrize("resource_name", V3_VERSION_RESOURCES)
    def test_v3_version_resource_exists(self, resources, resource_name):
        assert resource_name in resources

    @pytest.mark.parametrize("output_key", V3_OUTPUTS)
    def test_v3_output_exists(self, outputs, output_key):
        assert output_key in outputs

    def test_v3_parser_name_unchanged(self, resources):
        assert resources["ParserPrompt"]["Properties"]["Name"] == "calledit-parser"

    def test_v3_categorizer_name_unchanged(self, resources):
        assert resources["CategorizerPrompt"]["Properties"]["Name"] == "calledit-categorizer"

    def test_v3_vb_name_unchanged(self, resources):
        assert resources["VBPrompt"]["Properties"]["Name"] == "calledit-vb"

    def test_v3_review_name_unchanged(self, resources):
        assert resources["ReviewPrompt"]["Properties"]["Name"] == "calledit-review"
