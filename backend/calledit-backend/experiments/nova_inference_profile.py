#!/usr/bin/env python3
"""
AWS Bedrock Nova Pro Inference Profile Setup

This script demonstrates how to create and manage an inference profile for Amazon Nova Pro
to enable the converse API. Nova Pro requires provisioned throughput, which is configured
through an inference profile.

Prerequisites:
- AWS CLI configured with appropriate permissions
- boto3 library installed
- AWS Bedrock access with permissions to create inference profiles

Usage:
    python nova_inference_profile.py
"""

import boto3
import json
import time
import uuid
from botocore.exceptions import ClientError
from pprint import pprint

# Initialize Bedrock client
bedrock = boto3.client('bedrock')

def print_section(title):
    """Print a section title with formatting."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

def list_available_nova_models():
    """List all available Nova models in AWS Bedrock."""
    print_section("Available Nova Models")
    
    try:
        # Get all foundation models
        response = bedrock.list_foundation_models()
        
        # Filter for Nova models
        nova_models = [model for model in response['modelSummaries'] 
                      if 'nova' in model['modelId'].lower()]
        
        print(f"Found {len(nova_models)} Nova models:\n")
        
        for i, model in enumerate(nova_models, 1):
            print(f"{i}. {model['modelId']}")
            print(f"   Provider: {model['providerName']}")
            print(f"   Model Name: {model['modelName']}")
            
            # Print input modalities
            if 'inputModalities' in model:
                print(f"   Input Modalities: {', '.join(model['inputModalities'])}")
            
            # Print output modalities
            if 'outputModalities' in model:
                print(f"   Output Modalities: {', '.join(model['outputModalities'])}")
            
            print()
        
        return nova_models
    
    except ClientError as e:
        print(f"Error listing Nova models: {e}")
        return []

def check_existing_profiles():
    """Check if there are any existing inference profiles for Nova Pro."""
    print_section("Checking Existing Inference Profiles")
    
    try:
        response = bedrock.list_inference_profiles()
        
        if not response.get('inferenceProfileSummaries'):
            print("No inference profiles found in your account.")
            return []
        
        # Filter for Nova Pro profiles
        nova_profiles = [profile for profile in response['inferenceProfileSummaries'] 
                        if 'nova-pro' in profile.get('inferenceProfileId', '').lower()]
        
        if nova_profiles:
            print(f"Found {len(nova_profiles)} existing Nova Pro inference profiles:\n")
            
            for i, profile in enumerate(nova_profiles, 1):
                print(f"{i}. Profile ID: {profile.get('inferenceProfileId', 'N/A')}")
                print(f"   ARN: {profile.get('inferenceProfileArn', 'N/A')}")
                
                # Print all available keys in the profile
                for key, value in profile.items():
                    if key not in ['inferenceProfileId', 'inferenceProfileArn']:
                        print(f"   - {key}: {value}")
                print()
        else:
            print("No existing Nova Pro inference profiles found.")
        
        return nova_profiles
    
    except ClientError as e:
        print(f"Error checking existing profiles: {e}")
        return []

def create_nova_inference_profile():
    """Create an inference profile for Nova Pro."""
    print_section("Creating Nova Pro Inference Profile")
    
    # Generate a unique name for the profile
    profile_name = f"NovaPro-Profile-{uuid.uuid4().hex[:8]}"
    
    try:
        # First, check if Nova Pro is available
        models_response = bedrock.list_foundation_models()
        nova_pro_models = [model for model in models_response['modelSummaries'] 
                          if 'nova-pro' in model['modelId'].lower()]
        
        if not nova_pro_models:
            print("Error: Nova Pro model not found or not available in your account.")
            return None
        
        nova_pro_model_id = nova_pro_models[0]['modelId']
        print(f"Using Nova Pro model: {nova_pro_model_id}")
        
        # Create the inference profile
        print(f"Creating inference profile '{profile_name}'...")
        
        # Get the model ARN from the existing system profile
        existing_response = bedrock.list_inference_profiles()
        system_profile = None
        for profile in existing_response.get('inferenceProfileSummaries', []):
            if 'nova-pro' in profile.get('inferenceProfileId', '').lower() and profile.get('type') == 'SYSTEM_DEFINED':
                system_profile = profile.get('inferenceProfileArn')
                break
        
        if not system_profile:
            print("Error: No system-defined Nova Pro profile found to copy from.")
            return None
        
        response = bedrock.create_inference_profile(
            inferenceProfileName=f"NovaProProfile{profile_name.replace('-', '')}",
            description="Inference profile for Nova Pro to enable converse API",
            modelSource={
                'copyFrom': system_profile
            },
            tags=[
                {'key': 'Purpose', 'value': 'Demo'},
                {'key': 'CreatedBy', 'value': 'nova_inference_profile.py'}
            ]
        )
        
        print(f"Inference profile created successfully!")
        print(f"Profile ARN: {response['inferenceProfileArn']}")
        
        # Extract profile ID from ARN
        profile_id = response['inferenceProfileArn'].split('/')[-1]
        print(f"Profile ID: {profile_id}")
        
        # Wait for the profile to become active
        print("Waiting for the profile to become active...")
        status = "CREATING"
        
        while status == "CREATING":
            time.sleep(10)  # Check every 10 seconds
            
            get_response = bedrock.get_inference_profile(
                inferenceProfileIdentifier=profile_id
            )
            
            status = get_response['status']
            print(f"Current status: {status}")
            
            if status == "ACTIVE":
                print("Inference profile is now active and ready to use!")
                break
            elif status in ["FAILED", "DELETING", "DELETED"]:
                print(f"Profile creation failed with status: {status}")
                if 'statusReason' in get_response:
                    print(f"Reason: {get_response['statusReason']}")
                break
        
        return response
    
    except ClientError as e:
        print(f"Error creating inference profile: {e}")
        return None

def update_nova_inference_profile(profile_id):
    """Update an existing Nova Pro inference profile."""
    print_section(f"Updating Nova Pro Inference Profile: {profile_id}")
    
    try:
        # Get current profile details
        get_response = bedrock.get_inference_profile(
            inferenceProfileIdentifier=profile_id
        )
        
        current_units = get_response.get('provisionedThroughput', {}).get('modelUnits', 1)
        print(f"Current provisioned throughput: {current_units} model units")
        
        # Update the profile with increased throughput
        new_units = current_units + 1
        print(f"Updating to {new_units} model units...")
        
        update_response = bedrock.update_inference_profile(
            inferenceProfileIdentifier=profile_id,
            provisionedThroughput={
                'modelUnits': new_units
            }
        )
        
        print("Update request submitted successfully!")
        print(f"New configuration will be applied soon.")
        
        return update_response
    
    except ClientError as e:
        print(f"Error updating inference profile: {e}")
        return None

def delete_inference_profile(profile_id):
    """Delete an inference profile."""
    print_section(f"Deleting Inference Profile: {profile_id}")
    
    try:
        response = bedrock.delete_inference_profile(
            inferenceProfileIdentifier=profile_id
        )
        
        print(f"Deletion request submitted successfully!")
        print("The profile will be deleted shortly.")
        
        return response
    
    except ClientError as e:
        print(f"Error deleting inference profile: {e}")
        return None

def test_nova_with_profile(profile_arn):
    """Test using Nova Pro with the created inference profile."""
    print_section("Testing Nova Pro with Inference Profile")
    
    # Initialize Bedrock runtime client
    bedrock_runtime = boto3.client('bedrock-runtime')
    
    try:
        # Prepare the request
        prompt = "Tell me a short story about a robot learning to paint."
        
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 500,
                "temperature": 0.7,
                "topP": 0.9
            }
        }
        
        print(f"Sending request to Nova Pro using profile ARN: {profile_arn}")
        print(f"Prompt: {prompt}")
        
        # Use the converse API with the inference profile
        start_time = time.time()
        
        response = bedrock_runtime.converse(
            modelId=profile_arn,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            inferenceConfig={
                "maxTokens": 500,
                "temperature": 0.7,
                "topP": 0.9
            }
        )
        
        elapsed_time = time.time() - start_time
        
        # Extract and display the response
        assistant_message = response["output"]["message"]
        assistant_text = assistant_message["content"][0]["text"]
        
        print(f"\nResponse (in {elapsed_time:.2f} seconds):")
        print(f"{'-'*80}")
        print(assistant_text)
        print(f"{'-'*80}")
        
        print("\nTest completed successfully!")
        return True
    
    except ClientError as e:
        print(f"Error testing Nova Pro with inference profile: {e}")
        return False

def main():
    """Main function to set up and test Nova Pro inference profile."""
    print("\nAWS Bedrock Nova Pro Inference Profile Setup\n")
    print("This script helps you set up an inference profile for Nova Pro to enable the converse API.")
    
    # List available Nova models
    nova_models = list_available_nova_models()
    
    if not nova_models:
        print("No Nova models found or accessible. Please check your AWS Bedrock access.")
        return
    
    # Check existing profiles
    existing_profiles = check_existing_profiles()
    
    # Create a new profile or use an existing one
    if existing_profiles:
        print("\nYou already have Nova Pro inference profiles.")
        use_existing = input("Do you want to use an existing profile? (y/n): ").lower() == 'y'
        
        if use_existing:
            profile_index = int(input(f"Enter the number of the profile to use (1-{len(existing_profiles)}): ")) - 1
            profile = existing_profiles[profile_index]
            profile_arn = profile.get('inferenceProfileArn')
            profile_id = profile.get('inferenceProfileId')
            
            print(f"\nUsing existing profile: {profile_id}")
        else:
            # Create a new profile
            new_profile = create_nova_inference_profile()
            if new_profile:
                profile_arn = new_profile['inferenceProfileArn']
                profile_id = new_profile['inferenceProfileArn'].split('/')[-1]
            else:
                print("Failed to create a new inference profile.")
                return
    else:
        # Create a new profile
        new_profile = create_nova_inference_profile()
        if new_profile:
            profile_arn = new_profile['inferenceProfileArn']
            profile_id = new_profile['inferenceProfileArn'].split('/')[-1]
        else:
            print("Failed to create a new inference profile.")
            return
    
    # Test the profile
    print("\nWaiting a moment before testing the profile...")
    time.sleep(10)  # Give AWS some time to fully provision the profile
    
    test_result = test_nova_with_profile(profile_arn)
    
    if test_result:
        print("\nNova Pro inference profile is set up and working correctly!")
        print(f"Use this profile ARN in your applications: {profile_arn}")
    else:
        print("\nThere was an issue testing the Nova Pro inference profile.")
        print("You might need to wait a bit longer for the profile to become fully active.")
    
    # Cleanup option
    if input("\nDo you want to delete the inference profile? (y/n): ").lower() == 'y':
        delete_inference_profile(profile_id)
    else:
        print(f"\nKeeping inference profile: {profile_id}")
        print("Remember that you may be charged for provisioned throughput.")
    
    print("\nScript completed!")

if __name__ == "__main__":
    main()
    


# you can find the id with 
# aws bedrock list-inference-profiles --query "inferenceProfileSummaries[?type=='APPLICATION']" 
# it may not show up in the console