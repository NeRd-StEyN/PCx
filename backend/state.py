from typing import TypedDict, List, Optional, Annotated
import operator

class AgentState(TypedDict):
    # System metrics collected by Observation Agent
    metrics: dict
    
    # Inferred user activity and context by Reasoning Agent
    context: str
    
    # Final decision (e.g., "ACT", "SILENT") and priority
    decision: dict
    
    # List of recommended actions
    actions: List[dict]
    
    # History of interactions/actions for memory
    history: Annotated[List[dict], operator.add]
    
    # User feedback for the last action
    feedback: Optional[str]
    
    # Store previous metrics to detect significant changes
    last_metrics: Optional[dict]
    
    # Summary of user preferences from Memory Agent
    preferences: dict

    # Flag to force the Reasoning Agent to run
    force_reasoning: bool

    # Result of the Observation Agent's change detection
    significant_change: bool
