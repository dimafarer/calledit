from strands import Agent
import json

class ReviewAgent:
    """
    Strands agent that implements MCP Sampling pattern for reviewing predictions.
    """
    
    def __init__(self, callback_handler=None):
        self.callback_handler = callback_handler
        self.agent = Agent(
            callback_handler=callback_handler,
            system_prompt="""You are a prediction review expert. Your task is to:
            1. Analyze a completed prediction response
            2. Identify sections that could be improved with more user information
            3. Generate specific questions that would help improve each section
            4. Determine if improvements could change verifiability category
            
            For each reviewable section, consider:
            - Could more specificity improve verification accuracy?
            - Would additional context change the verifiability category?
            - What specific user information would be most helpful?
            
            OUTPUT FORMAT:
            Always return a JSON object with:
            {
                "reviewable_sections": [
                    {
                        "section": "field_name",
                        "improvable": true/false,
                        "questions": ["specific question 1", "specific question 2"],
                        "reasoning": "why this section could be improved"
                    }
                ]
            }
            """
        )
    
    def review_prediction(self, prediction_response):
        """
        Review a prediction response and identify improvable sections.
        This implements MCP Sampling by requesting additional LLM processing.
        """
        review_prompt = f"""
        PREDICTION RESPONSE TO REVIEW:
        {json.dumps(prediction_response, indent=2)}
        
        Analyze each section and determine what could be improved with more user information.
        Focus on sections where additional context could:
        1. Make verification more precise
        2. Change verifiability category (e.g., human → tool verifiable)
        3. Improve verification method accuracy
        
        RETURN ONLY VALID JSON - NO OTHER TEXT:
        """
        
        # This is the MCP Sampling request - asking client to perform LLM interaction
        response = self.agent(review_prompt)
        response_str = str(response)
        
        try:
            # First try direct JSON parsing
            return json.loads(response_str)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks or mixed content
            import re
            
            # Look for JSON in code blocks
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_str)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Look for JSON object anywhere in the response
            json_pattern = r'\{[\s\S]*"reviewable_sections"[\s\S]*\}'
            json_match = re.search(json_pattern, response_str)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
            
            print(f"Failed to parse review response: {response_str[:500]}...")
            # Fallback if JSON parsing fails
            return {"reviewable_sections": []}
    
    def generate_improvement_questions(self, section_name, current_value):
        """
        Generate specific questions for a section that needs improvement.
        Another MCP Sampling request for targeted question generation.
        """
        questions_prompt = f"""
        SECTION: {section_name}
        CURRENT VALUE: {current_value}
        
        Generate 2-3 specific questions that would help improve this section.
        Questions should be:
        - Specific and actionable
        - Focused on information that would improve verification
        - Clear for users to understand and answer
        
        Return as JSON: {{"questions": ["question1", "question2", "question3"]}}
        """
        
        response = self.agent(questions_prompt)
        
        try:
            result = json.loads(str(response))
            return result.get("questions", [])
        except json.JSONDecodeError:
            return [f"How can we make the {section_name} more specific?"]
    
    def regenerate_section(self, section_name, original_value, user_input, full_context):
        """
        Regenerate a specific section with user input.
        For prediction_statement changes, also updates related fields.
        """
        if section_name == "prediction_statement":
            # When prediction statement changes, regenerate related fields too
            regeneration_prompt = f"""
            ORIGINAL PREDICTION: {original_value}
            USER CLARIFICATIONS: {user_input}
            CONTEXT: {json.dumps(full_context, indent=2)}
            
            The user has clarified their prediction. If they specified a different timeframe (like "tomorrow" when original assumed "today"), use their timeframe. Create improved prediction with their exact details.
            
            RETURN JSON:
            {{
                "prediction_statement": "improved prediction with user's location and timeframe",
                "verification_date": "2025-08-05T23:59:59Z if user said tomorrow",
                "verification_method": {{
                    "source": ["location-specific weather APIs"],
                    "criteria": ["rain at specified location and time"],
                    "steps": ["check weather for user's location and timeframe"]
                }}
            }}
            """
            
            response = self.agent(regeneration_prompt)
            response_str = str(response).strip()
            
            try:
                # Try to parse as JSON for multiple field updates
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_str)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    # Filter out reviewable_sections if present - we want actual updates
                    if 'reviewable_sections' in parsed:
                        del parsed['reviewable_sections']
                    return parsed
            except json.JSONDecodeError:
                pass
            
            # Fallback to single field update
            return response_str
        else:
            # For other sections, use original single-field logic
            regeneration_prompt = f"""
            SECTION TO IMPROVE: {section_name}
            ORIGINAL VALUE: {original_value}
            USER INPUT: {user_input}
            FULL CONTEXT: {json.dumps(full_context, indent=2)}
            
            Regenerate the {section_name} incorporating the user's additional information.
            Maintain consistency with other sections and ensure the improvement is meaningful.
            
            Return only the improved value for this section.
            """
            
            response = self.agent(regeneration_prompt)
            return str(response).strip()