from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from ..state import AgentState
from ..local_engine import LocalRules
import json
import os

def decision_agent(state: AgentState):
    """
    Decides whether to intervene or remain silent.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        try:
            llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=api_key)
            DECISION_PROMPT = """
            You are a Decision Agent for a Smart PC Companion.
            Based on the inferred context, decide if any intervention is necessary.

            Current Context:
            {context}

            System Metrics:
            {metrics}

            User Preferences:
            {preferences}

            Rules:
            1. Stay silent if the system is healthy and the user is focused.
            2. Act if there's a clear benefit (e.g., battery low while traveling, hidden background hog during a game).
            3. Do NOT use fixed thresholds. Use holistic reasoning.

            Return your decision in JSON format:
            {{
                "status": "ACT" or "SILENT",
                "rationale": "Reason for your decision",
                "priority": 1-10
            }}
            """
            prompt = ChatPromptTemplate.from_template(DECISION_PROMPT)
            chain = prompt | llm
            
            response = chain.invoke({
                "context": state["context"],
                "metrics": state["metrics"],
                "preferences": state.get("preferences", {})
            })
            
            # Robust JSON parsing
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            try:
                decision_data = json.loads(content)
            except json.JSONDecodeError:
                import re
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    decision_data = json.loads(match.group())
                else:
                    raise ValueError(f"Could not parse decision from LLM response: {response.content}")

            print(f"[Decision Agent] Status: {decision_data['status']} - {decision_data['rationale']}")
            
            return {
                "decision": decision_data
            }
        except Exception as e:
            print(f"[Decision Agent] LLM Error: {e}. Falling back to Local Rules.")

    # Fallback to Local Rules
    # Note: We don't have all the timestamps here, so we'll use defaults or let action_agent handle it.
    # However, we can use a simpler version or just return ACT if we want to be safe.
    # Actually, LocalRules.decide_actions is better suited for action_agent.
    # For decision_agent, if LLM is down, we can just say "ACT" if metrics are high.
    
    cpu = state["metrics"].get('cpu_usage_percent', 0)
    ram = state["metrics"].get('memory_usage_percent', 0)
    
    if cpu > 80 or ram > 85:
        decision_data = {
            "status": "ACT",
            "rationale": "High resource usage detected by local engine.",
            "priority": 8
        }
    else:
        decision_data = {
            "status": "SILENT",
            "rationale": "System healthy according to local thresholds.",
            "priority": 1
        }
    
    return {
        "decision": decision_data
    }
