import psutil
import datetime
import platform
import time

START_TIME = time.time()

class SystemMonitor:
    def __init__(self):
        # Initialize cpu_percent to start the counter
        psutil.cpu_percent(interval=None)
        self.last_proc_update = 0
        self.cached_procs = []

    @staticmethod
    def sanitize_string(s):
        """Removes non-ASCII characters that can crash system calls."""
        if not s: return "Unknown"
        return str(s).encode('ascii', 'ignore').decode('ascii').strip()

    def get_system_metrics(self):
        """Collects real-time system metrics with high robustness."""
        try:
            # Use interval=None for non-blocking call (returns usage since last call)
            cpu_usage = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            battery = psutil.sensors_battery()
            
            # Get active processes (only every 5 seconds to save CPU)
            current_time = time.time()
            if current_time - self.last_proc_update > 5:
                processes = []
                try:
                    for proc in sorted(psutil.process_iter(['name', 'memory_percent']), 
                                      key=lambda x: (x.info['memory_percent'] or 0), 
                                      reverse=True)[:5]:
                        p_info = {
                            "name": self.sanitize_string(proc.info['name']),
                            "memory_percent": round(proc.info['memory_percent'] or 0, 2)
                        }
                        processes.append(p_info)
                    self.cached_procs = processes
                    self.last_proc_update = current_time
                except Exception:
                    pass # Skip if process list is locked
            
            processes = self.cached_procs

            # Get disk usage safely
            try:
                disk = psutil.disk_usage('C:\\')
                disk_p = disk.percent
                disk_f = disk.free // (1024**3)
            except:
                disk_p, disk_f = 0, 0

            return {
                "timestamp": datetime.datetime.now().isoformat(),
                "cpu_usage_percent": cpu_usage,
                "memory_usage_percent": memory.percent,
                "memory_available_mb": memory.available // (1024 * 1024),
                "battery_percent": battery.percent if battery else 100,
                "is_plugged": battery.power_plugged if battery else True,
                "top_processes": processes,
                "os": platform.system(),
                "time_of_day": datetime.datetime.now().strftime("%H:%M"),
                "disk_usage_percent": disk_p,
                "disk_free_gb": disk_f,
                "session_duration_minutes": int((time.time() - START_TIME) // 60)
            }
        except Exception as e:
            print(f"Monitor Error: {e}")
            return { "cpu_usage_percent": 0, "memory_usage_percent": 0, "top_processes": [], "time_of_day": "00:00" }

if __name__ == "__main__":
    monitor = SystemMonitor()
    time.sleep(1) # Wait a bit for CPU usage to be non-zero
    print(monitor.get_system_metrics())
