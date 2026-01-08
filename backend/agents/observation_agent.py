from ..tools.system_monitor import SystemMonitor

def observation_agent(state):
    """
    Analyzes system metrics provided in state and determines if an LLM call is necessary.
    """
    # Use metrics passed from the bridge/main loop to avoid redundant system calls
    metrics = state.get("metrics")
    
    # Fallback only if not provided (e.g. running graph in isolation)
    if not metrics:
        from ..tools.system_monitor import SystemMonitor
        monitor = SystemMonitor()
        metrics = monitor.get_system_metrics()
        
    last_metrics = state.get("last_metrics")
    force_reasoning = state.get("force_reasoning", False)
    
    significant_change = False
    
    if force_reasoning or not last_metrics:
        significant_change = True # First run or forced scan is always significant
    else:
        # Check CPU delta (> 15%)
        cpu_now = metrics.get("cpu_usage_percent", 0)
        cpu_last = last_metrics.get("cpu_usage_percent", 0)
        if abs(cpu_now - cpu_last) > 15:
            significant_change = True
            
        # Check RAM delta (> 10%)
        ram_now = metrics.get("memory_usage_percent", 0)
        ram_last = last_metrics.get("memory_usage_percent", 0)
        if not significant_change and abs(ram_now - ram_last) > 10:
            significant_change = True
            
        # Check if Top App changed
        try:
            if not significant_change and metrics["top_processes"][0]["name"] != last_metrics["top_processes"][0]["name"]:
                significant_change = True
        except (IndexError, KeyError):
            pass

    print(f"[Observation Agent] Significant change: {significant_change}")
    
    return {
        "metrics": metrics,
        "last_metrics": metrics,
        "significant_change": significant_change
    }
