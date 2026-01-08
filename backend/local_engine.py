class LocalRules:
    @staticmethod
    def get_context(metrics):
        """Categorizes system state without LLM."""
        cpu = metrics.get('cpu_usage_percent', 0)
        ram = metrics.get('memory_usage_percent', 0)
        top_apps = [p['name'].lower() for p in metrics.get('top_processes', [])]
        
        # Gaming Check
        games = ['steam', 'epicgames', 'riotgames', 'valorant', 'overwatch', 'csgo', 'cyberpunk', 'eldenring', 'gta']
        if any(g in app for g in games for app in top_apps):
            return "Gaming Session Detected", "System is prioritizing low latency. background tasks minimized."

        # Productivity Check
        dev_tools = ['code.exe', 'pycharm', 'visualstudio', 'cursor', 'windsurf', 'figma']
        if any(d in app for d in dev_tools for app in top_apps):
            return "High Productivity Mode", "Creative/Code tools active. Memory reserved for workspace stability."

        # Idle/Browsing
        if cpu < 10 and ram < 50:
            return "System Idle", "Optimization levels are optimal. Environmental power draw reduced."
            
        if any(b in app for b in ['chrome', 'msedge', 'firefox'] for app in top_apps):
            return "Web Browsing", "Multiple tabs active. Monitoring for memory-heavy background script leaks."

        return "Standard Usage", "System health is within normal operational parameters."

    @staticmethod
    def decide_actions(metrics, last_cleanup_time, last_optimized_time=0, last_battery_time=0, last_priority_time=0, thermal_guard_active=False):
        """Logic-based decisions for 'ACT' vs 'SILENT'."""
        actions = []
        cpu = metrics.get('cpu_usage_percent', 0)
        ram = metrics.get('memory_usage_percent', 0)
        disk = metrics.get('disk_usage_percent', 0)
        import time
        current_time = time.time()
        
        # 1. RAM Management (Threshold increased to 90%, added cooldown)
        if ram > 90 and (current_time - last_optimized_time) > 21600:
            actions.append({
                "action": "auto_memory_flush",
                "description": "Critical RAM usage detected. Performed background memory stabilization."
            })
            # Also clear standby list for deep optimization
            actions.append({
                "action": "clear_standby_list",
                "description": "Purged system standby list to reclaim hidden cached memory."
            })
            
        # 2. Performance & Heat Management
        if cpu > 70:
            # Shift priority only once every 15 mins to avoid overhead
            if (current_time - last_priority_time) > 900:
                actions.append({
                    "action": "prioritize_active_procs",
                    "description": "High CPU load. Re-allocated system resources to active foreground task."
                })
            
            # Enable thermal guard if not already active
            if not thermal_guard_active:
                actions.append({
                    "action": "thermal_guard_on",
                    "description": "Thermal Guard active: capping CPU to prevent overheating spikes."
                })
        elif cpu < 30 and thermal_guard_active:
            # Disable thermal guard only if it was previously enabled
            actions.append({
                "action": "thermal_guard_off",
                "description": "Thermal Guard deactivated: restoring full CPU power."
            })

        # 3. Disk & Maintenance
        time_since_last = current_time - last_cleanup_time
        if time_since_last > 86400: # 24 hours
            actions.append({"action": "clear_temp_files", "description": "Automated system junk clearance."})
            actions.append({"action": "clear_browser_cache", "description": "Purging hidden browser caches to reclaim space."})
            actions.append({"action": "optimize_drives", "description": "Maintenance: Optimized fixed drives (TRIM/Defrag)."})
            actions.append({"action": "flush_dns", "description": "Refreshing network stack via DNS flush."})

        # 4. Battery Management (Added 1-hour cooldown to prevent repetitive action logs)
        if not metrics.get('is_plugged') and metrics.get('battery_percent', 100) < 30:
             if (current_time - last_battery_time) > 3600:
                 actions.append({
                    "action": "enable_power_saver",
                    "description": "Low battery profile activated."
                })

        return actions
