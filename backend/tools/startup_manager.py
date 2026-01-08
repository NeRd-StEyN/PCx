import os
import sys
import platform
import subprocess

class StartupManager:
    @staticmethod
    def get_startup_path():
        if platform.system() != "Windows":
            return None
        return os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")

    @staticmethod
    def is_auto_run_enabled():
        startup_path = StartupManager.get_startup_path()
        if not startup_path:
            return False
        # We check for our silent launcher script
        shortcut_path = os.path.join(startup_path, "PCxGuard_Startup.vbs")
        return os.path.exists(shortcut_path)

    @staticmethod
    def enable_auto_run_exe(exe_path):
        """Silently registers the compiled EXE for startup."""
        startup_path = StartupManager.get_startup_path()
        if not startup_path: return False
        
        target_path = os.path.join(startup_path, "PCxGuard_Startup.vbs")
        # Create a silent VBS launcher specifically for the EXE
        vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """{exe_path}"" --minimized", 0, False
Set WshShell = Nothing'''
        
        try:
            with open(target_path, 'w') as f:
                f.write(vbs_content)
            return True
        except Exception as e:
            print(f"Error enabling EXE auto-run: {e}")
            return False

    @staticmethod
    def enable_auto_run(vbs_template_path):
        """Registers the python script for startup (Development mode)."""
        startup_path = StartupManager.get_startup_path()
        if not startup_path: return False
        
        target_path = os.path.join(startup_path, "PCxGuard_Startup.vbs")
        project_dir = os.path.abspath(os.path.dirname(vbs_template_path))
        
        try:
            with open(vbs_template_path, 'r') as f:
                content = f.read()
            
            # Inject absolute path for dev environment
            old_line = 'strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)'
            new_line = f'strPath = "{project_dir}"'
            content = content.replace(old_line, new_line)
            
            with open(target_path, 'w') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error enabling script auto-run: {e}")
            return False

    @staticmethod
    def disable_auto_run():
        startup_path = StartupManager.get_startup_path()
        if not startup_path: return False
        
        target_path = os.path.join(startup_path, "PCxGuard_Startup.vbs")
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
                return True
            except: return False
        return True
