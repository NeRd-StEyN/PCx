from langgraph.graph import StateGraph, END
from .state import AgentState
from .agents.observation_agent import observation_agent
from .agents.reasoning_agent import reasoning_agent
from .agents.decision_agent import decision_agent
from .agents.action_agent import action_agent
from .agents.memory_agent import memory_agent

def create_graph():
    # Initialize the graph
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("observation", observation_agent)
    workflow.add_node("reasoning", reasoning_agent)
    workflow.add_node("decision", decision_agent)
    workflow.add_node("action", action_agent)
    workflow.add_node("memory", memory_agent)

    # Define Edges
    workflow.set_entry_point("observation")

    # Conditional routing after observation
    def should_reason(state):
        if state.get("significant_change"):
            return "reasoning"
        return "memory" # Skip to memory to update history/last_metrics

    workflow.add_conditional_edges(
        "observation",
        should_reason,
        {
            "reasoning": "reasoning",
            "memory": "memory"
        }
    )

    workflow.add_edge("reasoning", "decision")

    # Conditional logic based on decision
    def should_act(state):
        if state["decision"]["status"] == "ACT":
            return "action"
        return "memory"

    workflow.add_conditional_edges(
        "decision",
        should_act,
        {
            "action": "action",
            "memory": "memory"
        }
    )

    workflow.add_edge("action", "memory")
    workflow.add_edge("memory", END)

    return workflow.compile()

# Example usage
if __name__ == "__main__":
    app = create_graph()
    print("Graph compiled successfully.")
