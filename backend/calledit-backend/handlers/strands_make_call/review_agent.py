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
        Final MCP Sampling request for improvement generation.
        """
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