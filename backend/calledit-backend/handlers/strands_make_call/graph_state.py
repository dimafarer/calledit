"""
Graph State Definition for Prediction Verification Workflow

This module defines the TypedDict schema for state that flows through the
prediction verification graph. Each agent node receives this state, processes it,
and returns an updated version.

v2 CHANGES (Spec 2: Unified Graph with Stateful Refinement):
Added 5 new fields for multi-round refinement support:
  - round: Which iteration of the graph we're on (1 = initial, 2+ = after clarification)
  - user_clarifications: Accumulated list of all user clarifications across all rounds
  - prev_parser_output: Parser's output from the previous round (None in round 1)
  - prev_categorizer_output: Categorizer's output from the previous round
  - prev_vb_output: Verification Builder's output from the previous round

WHY THESE FIELDS EXIST:
In v1, each HITL cycle started from scratch — agents had no memory of previous rounds.
In v2, the full graph re-runs on each clarification, and agents receive their previous
output plus all accumulated clarifications. This lets them make informed decisions:
"does this new information change my answer?" rather than starting over.

The round state is NOT held in the Lambda or the graph object — it's held by the
frontend (React state) and sent back with each `clarify` WebSocket action. The Lambda
is stateless; the frontend is the session. See Decision 8 in project-updates/01.

HOW STATE FLOWS:
- Round 1: Lambda builds state with round=1, empty clarifications, None prev outputs
- Graph runs: agents produce outputs, results sent to client as prediction_ready
- User clarifies: frontend sends {action: "clarify", user_input, current_state}
- Round 2: Lambda builds state from current_state with round=2, clarification appended,
  prev outputs populated from round 1 results
- Graph re-runs: agents see previous output + clarification, confirm or update

Following Strands best practices:
- Clear state schema with TypedDict
- Optional fields for intermediate results
- Metadata fields for error tracking
- total=False allows partial state construction (round 1 vs round 2+ have different fields populated)
"""

from typing import TypedDict, Optional, List, Dict, Any


class PredictionGraphState(TypedDict, total=False):
    """
    State schema for the prediction verification graph.
    
    This state flows through all agent nodes in the graph:
    Parser → Categorizer → Verification Builder → Review (parallel branch)
    
    Fields are marked as total=False to allow partial state updates.
    This is important because round 1 has prev_*_output as None,
    while round 2+ populates them from the previous execution.
    """
    
    # -------------------------------------------------------------------------
    # User inputs (required at graph entry)
    # These come from the WebSocket request body and are set by the Lambda handler.
    # -------------------------------------------------------------------------
    user_prompt: str
    user_timezone: str
    current_datetime_utc: str
    current_datetime_local: str
    
    # -------------------------------------------------------------------------
    # Parser Agent outputs
    # The Parser extracts the prediction statement, parses time references,
    # and provides reasoning for its date interpretation.
    # -------------------------------------------------------------------------
    prediction_statement: str
    verification_date: str
    date_reasoning: str
    
    # -------------------------------------------------------------------------
    # Categorizer Agent outputs
    # The Categorizer classifies the prediction into one of 5 verifiability
    # categories and explains its reasoning.
    # -------------------------------------------------------------------------
    verifiable_category: str
    category_reasoning: str
    
    # -------------------------------------------------------------------------
    # Verification Builder Agent outputs
    # The VB creates a detailed verification plan with sources, criteria, and steps.
    # -------------------------------------------------------------------------
    verification_method: Dict[str, List[str]]  # {source: [], criteria: [], steps: []}
    
    # -------------------------------------------------------------------------
    # Review Agent outputs
    # The ReviewAgent performs meta-analysis on the complete pipeline output,
    # identifying sections that could be improved with more user information.
    # -------------------------------------------------------------------------
    reviewable_sections: List[Dict[str, Any]]
    
    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    initial_status: str
    error: Optional[str]
    
    # -------------------------------------------------------------------------
    # v2: Round tracking and history
    #
    # These fields enable multi-round refinement. The frontend holds this state
    # between rounds and sends it back with each `clarify` action. The Lambda
    # uses it to build the enriched PredictionGraphState for the new round.
    #
    # WHY round IS AN int (not a bool like "is_refinement"):
    # Agents benefit from knowing which round they're on. Round 3 means the user
    # has clarified twice — the prediction should be quite specific by now. This
    # context helps agents calibrate their confidence and specificity.
    #
    # WHY user_clarifications IS List[str] (not List[Dict]):
    # Clarifications are plain text from the user. No metadata (timestamp, section)
    # is needed because agents see the full list and decide relevance themselves.
    # Keeping it simple — a list of strings is easy to serialize, send over
    # WebSocket, and display in the UI.
    #
    # WHY prev_*_output IS Optional[Dict] (not the full PredictionGraphState):
    # Each agent only needs its own previous output, not the entire state.
    # Passing the full state would bloat the prompt and confuse agents with
    # irrelevant context. The Lambda handler extracts each agent's relevant
    # fields when building the enriched state.
    # -------------------------------------------------------------------------
    round: int                                        # 1 = initial, 2+ = after clarification
    user_clarifications: List[str]                    # Accumulates ALL clarifications across rounds
    prev_parser_output: Optional[Dict[str, str]]      # {prediction_statement, verification_date, date_reasoning}
    prev_categorizer_output: Optional[Dict[str, str]] # {verifiable_category, category_reasoning}
    prev_vb_output: Optional[Dict[str, Any]]          # {verification_method: {source, criteria, steps}}


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
