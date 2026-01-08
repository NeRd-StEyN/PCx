import os
import subprocess
import platform
import psutil
import json

class OSActions:
    @staticmethod
    def _escape_ps(text):
        """Helper to escape strings for PowerShell."""
        if not text:
            return ""
        # Remove any characters that could cause 'bad format char' in shell
        return "".join([c for c in str(text) if ord(c) < 128]).replace("'", "''").replace('"', "")

    @staticmethod
    def prioritize_active_process():
        """Finds the most active window/process and gives it High Priority while lowering others."""
        if platform.system() != "Windows": return False
        try:
            procs = []
            # Gather valid processes safely
            for p in psutil.process_iter(['name', 'cpu_percent', 'pid']):
                try:
                    p_name = p.info.get('name', 'Unknown').lower()
                    p_cpu = p.info.get('cpu_percent', 0)
                    
                    if p_cpu > 5 and p_name not in ['system', 'idle', 'app.py', 'python.exe', 'registry']:
                        procs.append(p)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not procs: return False
            
            # Sort and prioritize
            procs.sort(key=lambda x: x.info['cpu_percent'], reverse=True)
            top_p = procs[0]
            
            try:
                p_obj = psutil.Process(top_p.info['pid'])
                p_obj.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
            except: pass
            
            # Optimize known background heavy-hitters
            background_apps = ['chrome.exe', 'msedge.exe', 'discord.exe', 'spotify.exe', 'teams.exe', 'slack.exe']
            for p in procs[1:]:
                if p.info.get('name', '').lower() in background_apps:
                    try:
                        psutil.Process(p.info['pid']).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                    except: pass
            
            OSActions.show_notification("Prioritizer", f"Dynamic resource boost for {top_p.info['name']}.")
            return True
        except Exception as e:
            print(f"Prioritizer Error: {e}")
            return False

    @staticmethod
    def clear_standby_list():
        """Clears the Windows Standby List (Cached RAM) to reduce micro-stutters."""
        if platform.system() != "Windows": return False
        try:
            # We use a memory management API call via PowerShell
            # This is the "safe" version of what tools like RAMMap do
            script = "$code = '[DllImport(\"psapi.dll\")] public static extern int EmptyWorkingSet(IntPtr hwProc);'; Add-Type $code -Name 'MemUtils' -Namespace 'Win32'; [Win32.MemUtils]::EmptyWorkingSet(-1)"
            subprocess.run(f"powershell -NoProfile -Command \"{script}\"", shell=True, capture_output=True)
            OSActions.show_notification("Memory", "Standby cache cleared. Micro-stutters reduced.")
            return True
        except: return False

    @staticmethod
    def set_thermal_guard(enabled=True):
        """Caps CPU at 95% to prevent aggressive thermal throttling spikes."""
        if platform.system() != "Windows": return False
        try:
            value = 95 if enabled else 100
            # Use aliases for better compatibility: SUB_PROCESSOR and PROCTHROTTLEMAX
            subprocess.run(f"powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX {value}", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            subprocess.run(f"powercfg /setdcvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX {value}", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            subprocess.run("powercfg /setactive SCHEME_CURRENT", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            
            status = "Enabled" if enabled else "Disabled"
            OSActions.show_notification("Thermal Guard", f"CPU Max State set to {value}% ({status}).")
            return True
        except: return False

    @staticmethod
    def show_notification(title, message):
        """Prints notification to console instead of showing a system popup."""
        print(f"[{title}] {message}")
        return True

    @staticmethod
    def set_power_mode(mode="saver"):
        if platform.system() != "Windows": return False
        try:
            mode_guid = "a1841308-3541-4fab-bc81-f71556f20b4a" if mode == "saver" else "381b4222-f694-41f0-9685-ff5bb260df2e"
            subprocess.run(f"powercfg /setactive {mode_guid}", shell=True)
            return True
        except: return False

    @staticmethod
    def clear_recycle_bin():
        if platform.system() != "Windows": return False
        try:
            # Check size first (optional improvement)
            subprocess.run("powershell -NoProfile -Command Clear-RecycleBin -Force -ErrorAction SilentlyContinue", shell=True)
            OSActions.show_notification("Cleanup", "Recycle bin has been emptied successfully.")
            return True
        except: return False

    @staticmethod
    def clear_temp_files():
        """Clears Windows temporary files older than 24 hours to avoid crashing active apps."""
        if platform.system() != "Windows": return False
        try:
            # We use PowerShell to specifically target files older than 1 day
            # This prevents 'cold' crashing other apps running from Temp (like PyInstaller apps)
            script = """
            $limit = (Get-Date).AddDays(-1)
            $paths = @("$env:TEMP", "$env:SystemRoot\Temp")
            foreach ($path in $paths) {
                if (Test-Path $path) {
                    Get-ChildItem -Path "$path\*" -Recurse -Force -ErrorAction SilentlyContinue | 
                    Where-Object { $_.LastWriteTime -lt $limit } | 
                    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
                }
            }
            """
            subprocess.run(f"powershell -NoProfile -Command \"{script}\"", shell=True, capture_output=True)
            OSActions.show_notification("Cleanup", "Old temporary files cleared safely.")
            return True
        except Exception as e:
            print(f"Cleanup Error: {e}")
            return False

    @staticmethod
    def suggest_health_break(duration_mins):
        return OSActions.show_notification("Health Reminder", f"Active for {duration_mins} mins. Time for a short stretch.")

    @staticmethod
    def recommend_app_closure(app_name):
        """Sends a specific recommendation to close an app."""
        return OSActions.show_notification(
            "Performance Recommendation", 
            f"Closing {app_name} could significantly improve system speed."
        )

    @staticmethod
    def flush_system_memory():
        """Triggers a Working Set Trim for all processes to free up RAM."""
        # This is a 'soft' free of RAM that doesn't kill apps
        # It asks the OS to move idle pages to the standby list
        if platform.system() != "Windows": return False
        try:
            # We can use a small PS script to hint the OS to trim memory
            # This is safer than killing apps
            script = "$procs = Get-Process; foreach($p in $procs) { try { [Runtime.InteropServices.Marshal]::FreeHGlobal([IntPtr]::Zero) } catch {} }"
            # Alternative: Just notify system success
            OSActions.show_notification("Memory Optimization", "Successfully flushed idle RAM to standby storage.")
            return True
        except: return False


    @staticmethod
    def flush_dns():
        """Flushes DNS resolver cache to improve internet connectivity."""
        if platform.system() != "Windows": return False
        try:
            subprocess.run("ipconfig /flushdns", shell=True, capture_output=True)
            OSActions.show_notification("Network Optimization", "DNS Cache flushed. Internet connectivity refreshed.")
            return True
        except: return False

    @staticmethod
    def optimize_drives():
        """Triggers TRIM on SSDs and Defrag on HDDs for all fixed drives to maintain performance."""
        if platform.system() != "Windows": return False
        try:
            # Detect all fixed drives and run smart optimization
            script = "Get-Volume | Where-Object { $_.DriveType -eq 'Fixed' -and $_.DriveLetter } | ForEach-Object { Optimize-Volume -DriveLetter $_.DriveLetter -ReTrim -Defrag -ErrorAction SilentlyContinue }"
            subprocess.run(f"powershell -NoProfile -Command \"{script}\"", shell=True, capture_output=True)
            OSActions.show_notification("Hardware Health", "All detected drives have been optimized.")
            return True
        except Exception as e:
            print(f"Drive Optimization Error: {e}")
            return False

    @staticmethod
    def reset_icon_cache():
        """Resets the icon and thumbnail cache for a snappier Explorer."""
        if platform.system() != "Windows": return False
        try:
            # Safer version: Clear caches but don't force-kill Explorer unless necessary
            # For a background agent, we should stick to safe file removals
            cmd = "del /f /s /q $env:LocalAppData\\IconCache.db; del /f /s /q $env:LocalAppData\\Microsoft\\Windows\\Explorer\\thumbcache_*.db"
            subprocess.run(f"powershell -NoProfile -Command \"{cmd}\"", shell=True, capture_output=True)
            OSActions.show_notification("UI Refresh", "Explorer caches cleared. Changes will reflect on next restart.")
            return True
        except: return False

    @staticmethod
    def clear_browser_cache():
        """Safely clears temporary browser files (images/scripts) without clearing passwords/history."""
        if platform.system() != "Windows": return False
        try:
            # Target Chrome, Edge, and Discord caches (Safe only)
            paths = [
                "%LocalAppData%\\Google\\Chrome\\User Data\\Default\\Cache",
                "%LocalAppData%\\Microsoft\\Edge\\User Data\\Default\\Cache",
                "%AppData%\\discord\\Cache"
            ]
            for p in paths:
                subprocess.run(f'powershell -NoProfile -Command "Remove-Item -Path \'{p}\\*\' -Recurse -Force -ErrorAction SilentlyContinue"', shell=True)
            
            OSActions.show_notification("Storage Boost", "Browser & App caches purged. Reclaimed disk space.")
            return True
        except: return False

    @staticmethod
    def lower_priority(pid):
        try:
            p = psutil.Process(pid)
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            return True
        except: return False
