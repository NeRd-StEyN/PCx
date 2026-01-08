from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from ..state import AgentState
import json
import os

def memory_agent(state: AgentState):
    """
    Updates the long-term memory/preferences based on action outcomes.
    """
    if not state.get("actions") and not state.get("feedback"):
        return {}

    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        try:
            llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=api_key)
            MEMORY_PROMPT = """
            You are a Memory & Feedback Agent. 
            You update the user's long-term preference profile based on recent actions and hypothetical/actual feedback.

            Current Preferences:
            {preferences}

            Last Action(s):
            {actions}

            Feedback:
            {feedback}

            Update the preferences profile. For example, if the user rejected "power saver", add "prefers performance over battery".
            Return the UPDATED preferences profile as a JSON object.
            """
            prompt = ChatPromptTemplate.from_template(MEMORY_PROMPT)
            chain = prompt | llm
            
            response = chain.invoke({
                "preferences": state.get("preferences", {}),
                "actions": state.get("actions", []),
                "feedback": state.get("feedback", "No explicit feedback provided.")
            })
            
            # Robust JSON parsing
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            try:
                updated_prefs = json.loads(content)
            except json.JSONDecodeError:
                import re
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    try:
                        updated_prefs = json.loads(match.group())
                    except:
                        updated_prefs = state.get("preferences", {})
                else:
                    updated_prefs = state.get("preferences", {}) # Fallback to current

            print(f"[Memory Agent] Preferences updated: {list(updated_prefs.keys())}")
            
            return {
                "preferences": updated_prefs,
                "history": [{"actions": state.get("actions", [])}]
            }
        except Exception as e:
            print(f"[Memory Agent] LLM Error: {e}. Skipping preference update.")
    
    # Fallback: Just return current preferences without update
    return {
        "preferences": state.get("preferences", {}),
        "history": [{"actions": state.get("actions", [])}]
    }
