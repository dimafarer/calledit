"""
Graph State Definition for Prediction Verification Workflow

This module defines the TypedDict schema for state that flows through the
prediction verification graph. Each agent node receives this state, processes it,
and returns an updated version.

Following Strands best practices:
- Clear state schema with TypedDict
- Optional fields for intermediate results
- Metadata fields for error tracking
"""

from typing import TypedDict, Optional, List, Dict


class PredictionGraphState(TypedDict, total=False):
    """
    State schema for the prediction verification graph.
    
    This state flows through all agent nodes in the graph:
    Parser → Categorizer → Verification Builder → Review
    
    Fields are marked as total=False to allow partial state updates.
    """
    
    # User inputs (required at graph entry)
    user_prompt: str
    user_timezone: str
    current_datetime_utc: str
    current_datetime_local: str
    
    # Parser Agent outputs
    prediction_statement: str
    verification_date: str
    date_reasoning: str
    
    # Categorizer Agent outputs
    verifiable_category: str
    category_reasoning: str
    
    # Verification Builder Agent outputs
    verification_method: Dict[str, List[str]]  # {source: [], criteria: [], steps: []}
    
    # Review Agent outputs
    reviewable_sections: List[Dict[str, any]]
    
    # Metadata
    initial_status: str
    error: Optional[str]


class VerificationMethod(TypedDict):
    """Structure for verification method"""
    source: List[str]
    criteria: List[str]
    steps: List[str]


class ReviewableSection(TypedDict):
    """Structure for reviewable section"""
    section: str
    improvable: bool
    questions: List[str]
    reasoning: str
