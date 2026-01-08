import os
import sys
import time
import threading
import webview
import json
import psutil
import platform
from datetime import datetime
from dotenv import load_dotenv

# Fix for Windows Taskbar Icon
if platform.system() == "Windows":
    import ctypes
    myappid = 'mycompany.myproduct.subproduct.version' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# Load env vars explicitly before importing agents
load_dotenv()

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.getcwd()
    return os.path.join(base_path, relative_path)

from backend.tools.system_monitor import SystemMonitor
from backend.graph import create_graph
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from backend.tools.os_actions import OSActions
from backend.tools.startup_manager import StartupManager

from backend.local_engine import LocalRules

# Data directory for persistence
DATA_DIR = os.path.join(os.path.expanduser("~"), ".pcx_guard")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

STORAGE_FILE = os.path.join(DATA_DIR, "pcx_data.json")

class PythonBridge:
    def __init__(self):
        self.monitor = SystemMonitor()
        self.graph = create_graph()
        
        # Persistence Logic
        data = self._load_data()
        self.history = data.get("history", [])
        self.preferences = data.get("preferences", {})
        self.user_api_key = data.get("api_key", None)
        self.last_cleanup_time = data.get("last_cleanup", 0)
        
        if self.user_api_key:
            os.environ["GROQ_API_KEY"] = self.user_api_key

        self.last_metrics = None
        self.last_heavy_ai_run = 0
        self.last_local_run = 0
        self.last_spike_run = 0
        self.last_battery_action = 0
        self.last_priority_boost = 0
        self.thermal_guard_active = False
        self.force_ai = False
        self.is_running = True
        self.ai_lock = threading.Lock()
        self.current_metrics = self.monitor.get_system_metrics()
        self.agent_status = "Active Protection"

    def set_api_key(self, key):
        """Validates and saves the API key."""
        is_valid = self.validate_api_key(key)
        if is_valid:
            self.user_api_key = key
            os.environ["GROQ_API_KEY"] = key
            self._save_data()
            return {"success": True, "message": "API Key validated and saved."}
        else:
            return {"success": False, "message": "Invalid API Key. Please check and try again."}

    def validate_api_key(self, key):
        """Directly validates the key with Groq."""
        if not key or not key.startswith("gsk_"):
            return False
        try:
            from langchain_groq import ChatGroq
            llm = ChatGroq(api_key=key, model="llama-3.1-8b-instant")
            # Simple small request to check validity
            llm.invoke("ping")
            return True
        except Exception as e:
            print(f"Validation Error: {e}")
            return False

    def get_api_key(self):
        return self.user_api_key or ""

    def check_api_key(self):
        """Checks if the stored API key is valid."""
        return self.validate_api_key(self.user_api_key)

    def get_preferences(self):
        # Ensure default preferences exist
        if "reasoning_mode" not in self.preferences:
            self.preferences["reasoning_mode"] = "llm" # default
        return self.preferences

    def set_preference(self, key, value):
        self.preferences[key] = value
        self._save_data()
        return True

    def _load_data(self):
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Persistence] Load error: {e}. Starting fresh.")
        return {}

    def _save_data(self):
        """Atomic save to prevent data loss or corruption during crashes."""
        temp_file = STORAGE_FILE + ".tmp"
        try:
            data = {
                "history": self.history[-50:], 
                "preferences": self.preferences,
                "api_key": self.user_api_key,
                "last_cleanup": self.last_cleanup_time,
                "last_optimized": self.preferences.get("last_optimized", 0)
            }
            # Write to temporary file first
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=4) # Indent for easier manual debugging
            
            # Atomic rename (replace existing)
            if os.path.exists(STORAGE_FILE):
                os.replace(temp_file, STORAGE_FILE)
            else:
                os.rename(temp_file, STORAGE_FILE)
        except Exception as e:
            print(f"[Persistence] Save error: {e}")
            if os.path.exists(temp_file):
                try: os.remove(temp_file)
                except: pass

    def get_health_score(self):
        try:
            m = self.current_metrics
            if not m: return 100
            score = 100
            score -= (m.get('cpu_usage_percent', 0) * 0.4)
            score -= (m.get('memory_usage_percent', 0) * 0.4)
            if m.get('disk_usage_percent', 0) > 85: score -= 10
            return max(0, min(100, int(score)))
        except:
            return 100

    def get_agent_status(self):
        return self.agent_status

    def get_metrics(self):
        return self.current_metrics

    def get_history(self):
        return self.history

    def run_scan(self):
        self.force_ai = True
        return True

    def clear_junk(self):
        OSActions.clear_temp_files()
        OSActions.clear_recycle_bin()
        self.last_cleanup_time = time.time()
        return True

    def run_drive_optimization(self):
        success = OSActions.optimize_drives()
        return success

    def flush_memory(self):
        success = OSActions.flush_system_memory()
        if success:
            self.preferences["last_optimized"] = time.time()
            self._save_data()
        return success

    def get_startup_status(self):
        return StartupManager.is_auto_run_enabled()

    def toggle_startup(self, enabled):
        if enabled:
            # If running as EXE, we register the EXE directly
            # If running as script, we register the VBS launcher
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                return StartupManager.enable_auto_run_exe(exe_path)
            else:
                vbs_path = os.path.join(os.getcwd(), 'launch_companion.vbs')
                return StartupManager.enable_auto_run(vbs_path)
        else:
            return StartupManager.disable_auto_run()

    def start_background_loop(self):
        """Background loop to update metrics and trigger the Hybrid Engine."""
        while self.is_running:
            try:
                current_time = time.time()
                metrics = self.monitor.get_system_metrics()
                self.current_metrics = metrics
                
                # Hybrid Logic:
                # 1. Manual Scan (force_ai) -> AI Heavy
                # 2. Significant Spike -> Local Fast
                # 3. Regular Check (Every 5 mins) -> Local Fast
                
                should_trigger = self.force_ai
                is_heavy = self.force_ai # Only use heavy LLM on manual or 1 hour audits
                
                # Auto-audit (Heavy AI) every 15 minutes to refresh preferences
                if not should_trigger and (current_time - self.last_heavy_ai_run) >= 900:
                    should_trigger = True
                    is_heavy = True

                # Fast Local Audit every 2 minutes
                if not should_trigger and (current_time - self.last_local_run) >= 120:
                    should_trigger = True
                    is_heavy = False

                # Dynamic Spike (Local only) - Added 60s cooldown to prevent spam
                if self.last_metrics and not should_trigger:
                    cpu_delta = abs(metrics['cpu_usage_percent'] - self.last_metrics['cpu_usage_percent'])
                    if cpu_delta > 30 and (current_time - self.last_spike_run) >= 60:
                        should_trigger = True
                        is_heavy = False
                        self.last_spike_run = current_time

                if should_trigger:
                    if not self.ai_lock.locked():
                        threading.Thread(target=self._run_hybrid_cycle, args=(metrics, is_heavy), daemon=True).start()
                        if is_heavy:
                            self.last_heavy_ai_run = current_time
                        self.last_local_run = current_time # Reset local timer on any run to avoid double-up
                        self.force_ai = False
                
                time.sleep(1) 
            except Exception as e:
                print(f"Loop Error: {e}")
                time.sleep(5)

    def _run_hybrid_cycle(self, metrics, is_heavy=False):
        with self.ai_lock:
            reasoning_mode = self.preferences.get("reasoning_mode", "llm")
            is_ai_scan = is_heavy and reasoning_mode == "llm" and (self.user_api_key or os.getenv("GROQ_API_KEY"))

            # 1. ALWAYS get Local Heuristics Context (Instant & Safe)
            context_title, local_context = LocalRules.get_context(metrics)
            last_optimized = self.preferences.get("last_optimized", 0)
            
            # If it's a forced AI scan, we skip local actions to let AI have full control
            if is_ai_scan:
                local_actions = []
                self.agent_status = "Cloud Reasoning..."
            else:
                local_actions = LocalRules.decide_actions(metrics, self.last_cleanup_time, last_optimized, self.last_battery_action, self.last_priority_boost, self.thermal_guard_active)
            
            # Update trackers based on actions taken
            for act in local_actions:
                if act['action'] == "enable_power_saver":
                    self.last_battery_action = time.time()
                elif act['action'] == "prioritize_active_procs":
                    self.last_priority_boost = time.time()
                elif act['action'] == "thermal_guard_on":
                    self.thermal_guard_active = True
                elif act['action'] == "thermal_guard_off":
                    self.thermal_guard_active = False
            
            final_context = local_context
            final_decision = {"status": "SILENT", "rationale": "System healthy."}
            final_actions = []

            # 2. RUN ACTIONS (If local rules say so)
            if local_actions:
                # Find the first action that has a description to use as the rationale
                descriptive_action = next((a for a in local_actions if 'description' in a), None)
                if descriptive_action:
                    final_decision = {"status": "ACT", "rationale": descriptive_action['description']}
                else:
                    final_decision = {"status": "ACT", "rationale": "Applying background optimizations."}
                for act in local_actions:
                    # Execute
                    if act['action'] == "clear_temp_files":
                        OSActions.clear_temp_files()
                        OSActions.clear_recycle_bin()
                        self.last_cleanup_time = time.time()
                    elif act['action'] == "auto_memory_flush":
                        OSActions.flush_system_memory()
                        self.preferences["last_optimized"] = time.time()
                        self._save_data()
                    elif act['action'] == "enable_power_saver":
                        OSActions.set_power_mode("saver")
                    elif act['action'] == "clear_browser_cache":
                        OSActions.clear_browser_cache()
                    elif act['action'] == "optimize_drives":
                        OSActions.optimize_drives()
                    elif act['action'] == "flush_dns":
                        OSActions.flush_dns()
                    elif act['action'] == "reset_icon_cache":
                         OSActions.reset_icon_cache()
                    elif act['action'] == "prioritize_active_procs":
                        OSActions.prioritize_active_process()
                    elif act['action'] == "clear_standby_list":
                        OSActions.clear_standby_list()
                    elif act['action'] == "thermal_guard_on":
                        OSActions.set_thermal_guard(True)
                    elif act['action'] == "thermal_guard_off":
                        OSActions.set_thermal_guard(False)
                    final_actions.append(act)

            # 3. USE LLM (Only for high-level reasoning if heavy or forced)
            if is_ai_scan:
                try:
                    input_state = {
                        "preferences": self.preferences,
                        "metrics": metrics,
                        "last_metrics": self.last_metrics,
                        "history": self.history[-5:] if self.history else [],
                        "force_reasoning": True
                    }
                    result = self.graph.invoke(input_state)
                    # Only update title to Brain if the AI actually provided new reasoning
                    new_context = result.get("context")
                    if new_context and new_context != final_context:
                        final_context = new_context
                        context_title = "🧠 AI Intelligence"
                        self.agent_status = "Intelligence Updated"
                    else:
                        # AI chose to skip reasoning (no significant change)
                        self.agent_status = "Local Engine Active"
                    
                    self.preferences = result.get("preferences", self.preferences)
                except Exception as e:
                    print(f"AI Skip (Rate/Key): {e}")
                    self.agent_status = "AI Rate Limit/API Issue"
            else:
                self.agent_status = "Local Engine Active"

            # 4. UPDATE HISTORY
            history_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "metrics": metrics,
                "context": f"**{context_title}**: {final_context}",
                "decision": final_decision,
                "actions": final_actions
            }
            self.history.append(history_entry)
            self.last_metrics = metrics
            self._save_data()
            
            time.sleep(5)
            self.agent_status = "Active Protection"

def create_tray_icon(window, bridge):
    icon_path = resource_path('app_icon.png')
    if os.path.exists(icon_path):
        image = Image.open(icon_path)
    else:
        # Fallback to generated icon if file missing
        image = Image.new('RGB', (64, 64), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.polygon([(32, 5), (55, 15), (55, 45), (32, 60), (9, 45), (9, 15)], fill=(0, 255, 136))
    
    def on_show(icon, item):
        window.show()

    def on_exit(icon, item):
        bridge.is_running = False
        icon.stop()
        window.destroy()
        os._exit(0)

    menu = Menu(
        MenuItem('Show Shield', on_show, default=True),
        MenuItem('Exit', on_exit)
    )
    
    icon = Icon("GuardPC", image, "PCx", menu)
    icon.run()

def main():
    bridge = PythonBridge()
    
    # Start background loop
    bg_thread = threading.Thread(target=bridge.start_background_loop, daemon=True)
    bg_thread.start()

    # Create window (hidden if starting minimized)
    start_minimized = "--minimized" in sys.argv
    html_path = resource_path('ui/index.html')
    icon_path = resource_path('app_icon.png')
    window = webview.create_window(
        'PCx', 
        url=html_path,
        width=1100, 
        height=750,
        background_color='#000000',
        js_api=bridge,
        hidden=start_minimized
    )

    # Start tray icon
    tray_thread = threading.Thread(target=create_tray_icon, args=(window, bridge), daemon=True)
    tray_thread.start()

    # Prevent exit on window close
    def on_closing():
        window.hide()
        return False # Prevents destruction

    window.events.closing += on_closing

    # Move icon to start() for backend support (if supported by environment)
    webview.start(icon=icon_path if os.path.exists(icon_path) else None)

if __name__ == "__main__":
    main()
