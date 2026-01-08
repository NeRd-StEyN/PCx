from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from ..state import AgentState
from ..local_engine import LocalRules
from ..tools.os_actions import OSActions
import json
import os
import time

def action_agent(state: AgentState):
    """
    Translates the decision into specific actionable items and EXECUTES them.
    """
    if state["decision"]["status"] == "SILENT":
        return {"actions": []}

    api_key = os.getenv("GROQ_API_KEY")
    actions = []
    
    if api_key:
        try:
            llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=api_key)
            ACTION_PROMPT = """
            You are an Action Agent. You select specific system optimizations.
            Available Actions:
            - enable_power_saver: Activates Windows Power Saver mode.
            - prioritize_active_process: Boosts the CPU priority of the foreground app.
            - clear_standby_list: Purges standby RAM cache to reduce micro-stutters.
            - thermal_guard_on: Caps CPU to 95% to prevent thermal throttling.
            - thermal_guard_off: Restores full CPU performance.
            - clear_recycle_bin: Empties the system recycle bin.
            - clear_temp_files: Deletes temp files older than 24 hours.
            - auto_memory_flush: Triggers OS memory trim for idle processes.
            - flush_dns: Refreshes the network stack by flushing DNS.
            - optimize_drives: Runs TRIM/Defrag on fixed drives.
            - clear_browser_cache: Purges temporary browser files (Chrome/Edge/Discord).
            - reset_icon_cache: Resets Windows icon/thumbnail cache for snappier UI.
            - suggest_app_closure (parameter: app_name): Recommendation to close a specific app.
            - health_break_suggestion: Reminder if used for too long.
            - night_light_suggestion: Suggests eye care if it's late.

            Informed Context:
            {context}

            System Metrics:
            {metrics}

            Decision Rationale:
            {rationale}

            Select one or more actions. Return a JSON list of objects:
            [ {{"action": "action_name", "parameter": "value", "description": "why"}} ]
            """
            prompt = ChatPromptTemplate.from_template(ACTION_PROMPT)
            chain = prompt | llm
            
            response = chain.invoke({
                "context": state["context"],
                "metrics": state["metrics"],
                "rationale": state["decision"]["rationale"]
            })
            
            # Robust JSON parsing
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            try:
                actions = json.loads(content)
            except json.JSONDecodeError:
                import re
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    actions = json.loads(match.group())
                else:
                    raise ValueError(f"Could not parse actions from LLM response: {response.content}")
        except Exception as e:
            print(f"[Action Agent] LLM Error: {e}. Falling back to Local Rules.")
            actions = []

    # Fallback to Local Rules if LLM failed or no API key
    if not actions:
        # Use simple heuristics for fallback
        actions = LocalRules.decide_actions(state["metrics"], 0) # simplified for fallback

    print(f"[Action Agent] Total actions decided: {len(actions)}")
    
    # --- PHYSICAL EXECUTION ---
    executed_log = []
    for action_item in actions:
        act_name = action_item.get("action")
        param = action_item.get("parameter")
        desc = action_item.get("description")
        
        print(f"[Action Agent] Executing: {act_name}...")
        
        # Mapping action names to OSActions methods
        if act_name == "enable_power_saver":
            OSActions.set_power_mode("saver")
            OSActions.show_notification("Power Mode", "Switched to Power Saver to extend battery life.")
        
        elif act_name == "prioritize_active_process" or act_name == "prioritize_active_procs":
            OSActions.prioritize_active_process()
            
        elif act_name == "clear_standby_list":
            OSActions.clear_standby_list()
            
        elif act_name == "thermal_guard_on":
            OSActions.set_thermal_guard(True)
            
        elif act_name == "thermal_guard_off":
            OSActions.set_thermal_guard(False)

        elif act_name == "clear_recycle_bin":
            OSActions.clear_recycle_bin()

        elif act_name == "clear_temp_files":
            OSActions.clear_temp_files()

        elif act_name == "auto_memory_flush":
            OSActions.flush_system_memory()
            
        elif act_name == "flush_dns":
            OSActions.flush_dns()
            
        elif act_name == "optimize_drives":
            OSActions.optimize_drives()
            
        elif act_name == "clear_browser_cache":
            OSActions.clear_browser_cache()
            
        elif act_name == "reset_icon_cache":
            OSActions.reset_icon_cache()

        elif act_name == "suggest_app_closure":
            app_to_close = param if param else "Background Apps"
            OSActions.recommend_app_closure(app_to_close)

        elif act_name == "health_break_suggestion":
            duration = state["metrics"].get("session_duration_minutes", 90)
            OSActions.suggest_health_break(duration)
            
        elif act_name == "night_light_suggestion":
            OSActions.show_notification("Eye Care", "It's getting late. Consider enabling Night Light for better sleep.")
            

        executed_log.append(action_item)

    return {
        "actions": executed_log
    }
