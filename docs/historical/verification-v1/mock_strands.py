#!/usr/bin/env python3
"""
Mock Strands agents for testing without full installation
"""

from datetime import datetime
import time

class MockAgent:
    def __init__(self, name: str, model: str, tools: list = None):
        self.name = name
        self.model = model
        self.tools = tools or []
    
    def run(self, prompt: str) -> dict:
        """Mock agent response based on prompt content"""
        prompt_lower = prompt.lower()
        
        # Mock responses for different types of predictions
        if 'sun will rise' in prompt_lower:
            return {
                'content': 'TRUE. The sun will rise tomorrow as it does every day due to Earth\'s rotation. This is a natural law that can be verified through astronomical knowledge. Confidence: 0.95'
            }
        
        elif 'rain' in prompt_lower or 'weather' in prompt_lower:
            return {
                'content': 'Cannot verify weather prediction without access to weather data APIs. This requires external weather service integration.'
            }
        
        elif 'bitcoin' in prompt_lower:
            return {
                'content': 'Cannot verify Bitcoin price prediction without access to cryptocurrency price APIs. This requires financial data integration.'
            }
        
        elif 'nba' in prompt_lower or 'game' in prompt_lower:
            return {
                'content': 'Cannot verify sports prediction without access to sports data APIs. This requires sports results integration.'
            }
        
        elif 'feel happy' in prompt_lower or 'subjective' in prompt_lower:
            return {
                'content': 'This is a subjective prediction that requires human assessment. Cannot be verified objectively.'
            }
        
        elif 'current_time' in prompt_lower or 'time' in prompt_lower:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return {
                'content': f'Using current_time tool: {current_time}. Analyzing time-based prediction context...'
            }
        
        elif 'mathematical' in prompt_lower or 'calculate' in prompt_lower:
            return {
                'content': 'Performing mathematical analysis... The calculation appears to be correct based on standard mathematical principles.'
            }
        
        else:
            return {
                'content': 'Analyzing prediction... This requires further analysis to determine verification method.'
            }

def current_time():
    """Mock current_time tool"""
    return {
        'current_time': datetime.now().isoformat(),
        'timezone': 'UTC'
    }

# Mock the imports
class MockStrandsModule:
    Agent = MockAgent

class MockStrandsToolsModule:
    current_time = current_time