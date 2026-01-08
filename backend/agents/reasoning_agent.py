from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from ..state import AgentState
from ..local_engine import LocalRules
import os

def reasoning_agent(state: AgentState):
    """
    Infers user activity and system state based on live metrics and memory.
    """
    # Attempt to use LLM if API key is available
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        try:
            llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7, api_key=api_key)
            REASONING_PROMPT = """
            You are a Senior System Architect & Performance Analyst for 'PCx'.
            Provide a concise, high-impact **SYSTEM HEALTH AUDIT**. Focus only on technical state and resource patterns.

            System Metrics:
            {metrics}
            User Preferences & History:
            {preferences}

            Format (Markdown):
            1. **� LOAD PROFILE**: High-level technical summary of resource demand (e.g., 'High Multi-threaded Load' or 'Efficient Idle State'). Avoid guessing specific user apps/tasks (like 'gaming').
            2. **🌡️ STATUS**: Internal state assessment (e.g., 'Thermal headroom is optimal' or 'Memory pressure increasing').
            3. **🔍 INSIGHT**: One specific technical optimization or anomaly observation.

            Keep it professional, technical, and skip the fluff. Do not guess user behavior labels.
            """
            prompt = ChatPromptTemplate.from_template(REASONING_PROMPT)
            chain = prompt | llm
            
            response = chain.invoke({
                "metrics": state["metrics"],
                "preferences": state.get("preferences", {})
            })
            
            print(f"[Reasoning Agent] Context inferred: {response.content[:100]}...")
            
            return {
                "context": response.content
            }
        except Exception as e:
            print(f"[Reasoning Agent] LLM Error: {e}. Falling back to Local Rules.")
    
    # Fallback to Local Rules
    title, context = LocalRules.get_context(state["metrics"])
    return {
        "context": f"**{title}**: {context}"
    }
