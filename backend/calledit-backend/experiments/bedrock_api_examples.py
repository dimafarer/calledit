#!/usr/bin/env python3
"""
AWS Bedrock API Examples

This script demonstrates various operations using the AWS Bedrock API (not bedrock-runtime).
The Bedrock API is used for management operations like:
- Listing available foundation models
- Managing model access
- Creating and managing custom models
- Working with model evaluation jobs
- Managing inference profiles

For new developers learning AWS Bedrock.

Prerequisites:
- AWS CLI configured with appropriate permissions
- boto3 library installed
- AWS Bedrock access

Usage:
    python bedrock_api_examples.py
"""

import boto3
import json
import time
from botocore.exceptions import ClientError
from pprint import pprint

# Initialize Bedrock client (not bedrock-runtime)
bedrock = boto3.client('bedrock')

def print_section(title):
    """Print a section title with formatting."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

def list_foundation_models():
    """
    List all available foundation models in AWS Bedrock.
    
    This shows all models that exist in Bedrock, regardless of whether
    you have access to them or not.
    """
    print_section("Listing Foundation Models")
    
    try:
        # Get all foundation models
        response = bedrock.list_foundation_models()
        
        # Print the total number of models
        print(f"Total models available: {len(response['modelSummaries'])}\n")
        
        # Print details for each model
        for i, model in enumerate(response['modelSummaries'], 1):
            print(f"{i}. {model['modelId']}")
            print(f"   Provider: {model['providerName']}")
            print(f"   Model Name: {model['modelName']}")
            
            # Print input modalities
            if 'inputModalities' in model:
                print(f"   Input Modalities: {', '.join(model['inputModalities'])}")
            
            # Print output modalities
            if 'outputModalities' in model:
                print(f"   Output Modalities: {', '.join(model['outputModalities'])}")
            
            # Print inference types
            if 'inferenceTypesSupported' in model:
                print(f"   Inference Types: {', '.join(model['inferenceTypesSupported'])}")
            
            # Print customization support
            if 'customizationsSupported' in model:
                print(f"   Customizations: {', '.join(model['customizationsSupported'])}")
            
            print()
        
        return response['modelSummaries']
    
    except ClientError as e:
        print(f"Error listing foundation models: {e}")
        return []

def get_foundation_model(model_id):
    """
    Get detailed information about a specific foundation model.
    
    Args:
        model_id (str): The ID of the model to get information about
    """
    print_section(f"Getting Details for Model: {model_id}")
    
    try:
        response = bedrock.get_foundation_model(modelIdentifier=model_id)
        model = response['modelDetails']
        
        print(f"Model ID: {model['modelId']}")
        print(f"Provider: {model['providerName']}")
        print(f"Model Name: {model['modelName']}")
        
        # Print input modalities
        if 'inputModalities' in model:
            print(f"Input Modalities: {', '.join(model['inputModalities'])}")
        
        # Print output modalities
        if 'outputModalities' in model:
            print(f"Output Modalities: {', '.join(model['outputModalities'])}")
        
        # Print inference types
        if 'inferenceTypesSupported' in model:
            print(f"Inference Types: {', '.join(model['inferenceTypesSupported'])}")
        
        # Print customization support
        if 'customizationsSupported' in model:
            print(f"Customizations: {', '.join(model['customizationsSupported'])}")
        
        # Print model lifecycle status
        if 'modelLifecycle' in model:
            print(f"Lifecycle Status: {model['modelLifecycle']['status']}")
        
        # Print response streaming support
        if 'responseStreamingSupported' in model:
            print(f"Response Streaming Supported: {model['responseStreamingSupported']}")
        
        # Print throughput configuration
        if 'throughputConfiguration' in model:
            print(f"Throughput Configuration:")
            for config in model['throughputConfiguration']:
                print(f"  - {config['type']}: {config['capacity']}")
        
        return model
    
    except ClientError as e:
        print(f"Error getting foundation model details: {e}")
        return None

def list_custom_models():
    """
    List all custom models in your AWS account.
    
    Custom models are fine-tuned versions of foundation models.
    """
    print_section("Listing Custom Models")
    
    try:
        response = bedrock.list_custom_models()
        
        if not response.get('modelSummaries'):
            print("No custom models found in your account.")
            return []
        
        print(f"Total custom models: {len(response['modelSummaries'])}\n")
        
        for i, model in enumerate(response['modelSummaries'], 1):
            print(f"{i}. {model['modelName']}")
            print(f"   ARN: {model['modelArn']}")
            print(f"   Base Model: {model['baseModelName']}")
            print(f"   Status: {model['status']}")
            print(f"   Created: {model['creationTime']}")
            print()
        
        return response['modelSummaries']
    
    except ClientError as e:
        print(f"Error listing custom models: {e}")
        return []

def list_model_customization_jobs():
    """
    List all model customization jobs in your AWS account.
    
    Model customization jobs are fine-tuning jobs that create custom models.
    """
    print_section("Listing Model Customization Jobs")
    
    try:
        response = bedrock.list_model_customization_jobs()
        
        if not response.get('modelCustomizationJobSummaries'):
            print("No model customization jobs found in your account.")
            return []
        
        print(f"Total jobs: {len(response['modelCustomizationJobSummaries'])}\n")
        
        for i, job in enumerate(response['modelCustomizationJobSummaries'], 1):
            print(f"{i}. Job Name: {job['jobName']}")
            print(f"   ARN: {job['jobArn']}")
            print(f"   Status: {job['status']}")
            print(f"   Base Model: {job['baseModelName']}")
            print(f"   Created: {job['creationTime']}")
            print()
        
        return response['modelCustomizationJobSummaries']
    
    except ClientError as e:
        print(f"Error listing model customization jobs: {e}")
        return []

def get_model_access():
    """
    Get information about which foundation models you have access to.
    """
    print_section("Getting Model Access Information")
    
    try:
        # List all foundation models first
        models_response = bedrock.list_foundation_models()
        
        print("Checking model access status...")
        
        # Check which models you have access to
        accessible_models = []
        inaccessible_models = []
        
        for model in models_response['modelSummaries']:
            model_id = model['modelId']
            try:
                # Try to get details for the model - this will fail if you don't have access
                bedrock.get_foundation_model(modelIdentifier=model_id)
                accessible_models.append(model_id)
            except ClientError as e:
                if 'AccessDeniedException' in str(e):
                    inaccessible_models.append(model_id)
                else:
                    # Some other error occurred
                    print(f"Error checking access for {model_id}: {e}")
        
        print(f"\nModels you have access to ({len(accessible_models)}):")
        for model in accessible_models:
            print(f"- {model}")
        
        print(f"\nModels you don't have access to ({len(inaccessible_models)}):")
        for model in inaccessible_models:
            print(f"- {model}")
        
        return {
            'accessibleModels': accessible_models,
            'inaccessibleModels': inaccessible_models
        }
    
    except ClientError as e:
        print(f"Error getting model access information: {e}")
        return None

def list_model_invocation_jobs():
    """
    List all model invocation jobs in your AWS account.
    
    Model invocation jobs are asynchronous batch inference jobs.
    """
    print_section("Listing Model Invocation Jobs")
    
    try:
        response = bedrock.list_model_invocation_jobs()
        
        if not response.get('modelInvocationJobSummaries'):
            print("No model invocation jobs found in your account.")
            return []
        
        print(f"Total jobs: {len(response['modelInvocationJobSummaries'])}\n")
        
        for i, job in enumerate(response['modelInvocationJobSummaries'], 1):
            print(f"{i}. Job Name: {job['jobName']}")
            print(f"   ARN: {job['jobArn']}")
            print(f"   Status: {job['status']}")
            print(f"   Model ID: {job['modelId']}")
            print(f"   Created: {job['creationTime']}")
            print()
        
        return response['modelInvocationJobSummaries']
    
    except ClientError as e:
        print(f"Error listing model invocation jobs: {e}")
        return []

def list_inference_profiles():
    """
    List all inference profiles in your AWS account.
    
    Inference profiles are used to configure provisioned throughput for models.
    """
    print_section("Listing Inference Profiles")
    
    try:
        response = bedrock.list_inference_profiles()
        
        if not response.get('inferenceProfileSummaries'):
            print("No inference profiles found in your account.")
            return []
        
        print(f"Total profiles: {len(response['inferenceProfileSummaries'])}\n")
        
        for i, profile in enumerate(response['inferenceProfileSummaries'], 1):
            # Print available keys for debugging
            print(f"{i}. Profile ID: {profile.get('inferenceProfileId', 'N/A')}")
            print(f"   ARN: {profile.get('inferenceProfileArn', 'N/A')}")
            
            # Print all available keys in the profile
            print("   Available profile information:")
            for key, value in profile.items():
                print(f"   - {key}: {value}")
            print()
        
        return response['inferenceProfileSummaries']
    
    except ClientError as e:
        print(f"Error listing inference profiles: {e}")
        return []
    
    
    
def list_model_evaluation_jobs():
    """
    List all model evaluation jobs in your AWS account.
    
    Model evaluation jobs are used to evaluate the performance of models.
    """
    print_section("Listing Model Evaluation Jobs")
    
    try:
        response = bedrock.list_evaluation_jobs()
        
        if not response.get('evaluationJobs'):
            print("No model evaluation jobs found in your account.")
            return []
        
        print(f"Total jobs: {len(response['evaluationJobs'])}\n")
        
        for i, job in enumerate(response['evaluationJobs'], 1):
            print(f"{i}. Job Name: {job['jobName']}")
            print(f"   ARN: {job['jobArn']}")
            print(f"   Status: {job['status']}")
            print(f"   Created: {job['creationTime']}")
            print()
        
        return response['evaluationJobs']
    
    except ClientError as e:
        print(f"Error listing model evaluation jobs: {e}")
        return []

def list_guardrail_versions():
    """
    List all guardrail versions in your AWS account.
    
    Guardrails help ensure responsible AI usage by filtering inappropriate content.
    """
    print_section("Listing Guardrail Versions")
    
    try:
        response = bedrock.list_guardrails()
        
        if not response.get('guardrails'):
            print("No guardrails found in your account.")
            return []
        
        print(f"Total guardrails: {len(response['guardrails'])}\n")
        
        for i, guardrail in enumerate(response['guardrails'], 1):
            print(f"{i}. Guardrail Name: {guardrail['name']}")
            print(f"   ARN: {guardrail['guardrailArn']}")
            print(f"   Description: {guardrail.get('description', 'N/A')}")
            print(f"   Status: {guardrail['status']}")
            print(f"   Created: {guardrail['creationTime']}")
            print()
        
        return response['guardrails']
    
    except ClientError as e:
        print(f"Error listing guardrails: {e}")
        return []

def list_tags_for_resource(resource_arn):
    """
    List all tags for a specific resource.
    
    Args:
        resource_arn (str): The ARN of the resource to list tags for
    """
    print_section(f"Listing Tags for Resource: {resource_arn}")
    
    try:
        response = bedrock.list_tags_for_resource(resourceARN=resource_arn)
        
        if not response.get('tags'):
            print("No tags found for this resource.")
            return {}
        
        print(f"Total tags: {len(response['tags'])}\n")
        
        for key, value in response['tags'].items():
            print(f"{key}: {value}")
        
        return response['tags']
    
    except ClientError as e:
        print(f"Error listing tags: {e}")
        return {}

def main():
    """Main function to demonstrate AWS Bedrock API operations."""
    print("\nAWS Bedrock API Examples\n")
    print("This script demonstrates various operations using the AWS Bedrock API.")
    print("Note: Some operations may fail if you don't have the necessary permissions.")
    
    # List foundation models
    models = list_foundation_models()
    
    # Get details for a specific model (Claude 3 Sonnet)
    if models:
        # Find Claude 3 Sonnet in the list
        claude_model = next((m for m in models if 'claude-3-sonnet' in m['modelId']), None)
        if claude_model:
            get_foundation_model(claude_model['modelId'])
    
    # Get model access information
    get_model_access()
    
    # List custom models
    list_custom_models()
    
    # List model customization jobs
    list_model_customization_jobs()
    
    # List model invocation jobs
    list_model_invocation_jobs()
    
    # List inference profiles
    inference_profiles = list_inference_profiles()
    
    # List tags for an inference profile (if any exist)
    if inference_profiles:
        list_tags_for_resource(inference_profiles[0]['inferenceProfileArn'])
    
    # List model evaluation jobs
    list_model_evaluation_jobs()
    
    # List guardrail versions
    list_guardrail_versions()
    
    print("\nDemonstration complete!")

if __name__ == "__main__":
    main()