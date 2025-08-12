import boto3

def main():
    # Initialize Bedrock client
    bedrock = boto3.client('bedrock-runtime')
    
    # Conversation memory - list of messages
    conversation_history = []
    
    print("Chatbot started! Type 'quit' to exit.")
    print("-" * 40)
    
    while True:
        # Get user input
        user_input = input("\nYou: ").strip()
        
        # Check for exit condition
        if user_input.lower() == 'quit':
            print("Goodbye!")
            break
        
        # Add user message to conversation history
        conversation_history.append({
            "role": "user",
            "content": [{"text": user_input}]
        })
        
        # Call Bedrock API
        try:
            response = bedrock.converse(
                modelId="us.amazon.nova-micro-v1:0",
                    #   us.amazon.nova-micro-v1:0
                messages=conversation_history
            )
            # Extract assistant response
            assistant_message = response['output']['message']['content'][0]['text']
            
            # Add assistant response to conversation history
            conversation_history.append({
                "role": "assistant", 
                "content": [{"text": assistant_message}]
            })
            
            # Print assistant response
            print(f"\nAssistant: {assistant_message}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()