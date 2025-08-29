#!/usr/bin/env python3
"""
Demo prompts for CalledIt verification categories
End-to-end system test and compelling content generation
"""

DEMO_PROMPTS = {
    "agent_verifiable": [
        "The sun will rise tomorrow morning",
        "Water boils at 100 degrees Celsius at sea level",
        "There are 365 days in a regular year",
        "The Earth orbits around the Sun",
        "Gravity pulls objects toward the ground",
        "Ice melts when heated above 0°C",
        "The speed of light is faster than sound",
        "Humans need oxygen to survive"
    ],
    
    "current_tool_verifiable": [
        "It's currently past 2 PM",
        "Today is a weekday",
        "It's currently winter in the Northern Hemisphere",
        "The current year is 2025",
        "It's been more than 24 hours since January 1st",
        "Right now it's daytime in California",
        "The current month has 31 days",
        "It's currently the first quarter of the year"
    ],
    
    "strands_tool_verifiable": [
        "2 + 2 equals 4",
        "The square root of 16 is 4",
        "10% of 1000 is 100",
        "A circle with radius 5 has area greater than 75",
        "The factorial of 5 is 120",
        "If I invest $1000 at 5% annual interest, I'll have $1050 after one year",
        "The distance between (0,0) and (3,4) is 5 units",
        "Converting 100°F to Celsius gives approximately 37.8°C"
    ],
    
    "api_tool_verifiable": [
        "Bitcoin is currently trading above $50,000",
        "The weather in New York City today will have a high above 60°F",
        "Apple's stock price is currently above $150",
        "The current USD to EUR exchange rate is below 1.10",
        "It will rain in London sometime this week",
        "The S&P 500 index is currently above 5000",
        "Gold is trading above $2000 per ounce",
        "The temperature in Miami right now is above 70°F"
    ],
    
    "human_verifiable_only": [
        "I will feel happy when I wake up tomorrow",
        "My favorite color will still be blue next week",
        "I will enjoy my lunch today",
        "My mood will improve after listening to music",
        "I will find this movie entertaining",
        "My energy level will be high this afternoon",
        "I will feel satisfied after completing this project",
        "I will sleep well tonight"
    ]
}

def get_all_prompts():
    """Get all demo prompts organized by category"""
    return DEMO_PROMPTS

def get_prompts_by_category(category):
    """Get prompts for a specific category"""
    return DEMO_PROMPTS.get(category, [])

def get_total_count():
    """Get total number of demo prompts"""
    return sum(len(prompts) for prompts in DEMO_PROMPTS.values())

if __name__ == "__main__":
    print("📋 CalledIt Demo Prompts")
    print(f"Total prompts: {get_total_count()}")
    
    for category, prompts in DEMO_PROMPTS.items():
        print(f"\n🎯 {category.upper().replace('_', ' ')} ({len(prompts)} prompts):")
        for i, prompt in enumerate(prompts, 1):
            print(f"  {i}. {prompt}")