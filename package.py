import PyInstaller.__main__
import os
import shutil

# Define paths
APP_NAME = "PCx"
ENTRY_POINT = "app.py"
ICON_PATH = "app_icon.png"
UI_FOLDER = "ui"
BACKEND_FOLDER = "backend"

print(f"[*] Preparing build for {APP_NAME}...")

# Clean previous builds
for folder in ["build", "dist"]:
    if os.path.exists(folder):
        print(f"[*] Cleaning {folder}...")
        shutil.rmtree(folder)

# Define PyInstaller arguments
build_args = [
    ENTRY_POINT,
    f"--name={APP_NAME}",
    "--noconsole",
    "--onefile",
    f"--icon={ICON_PATH}",
    f"--add-data={UI_FOLDER};{UI_FOLDER}",
    f"--add-data={BACKEND_FOLDER};{BACKEND_FOLDER}",
    f"--add-data={ICON_PATH};.",
    "--hidden-import=langgraph",
    "--hidden-import=langchain_groq",
    "--hidden-import=langchain_core",
    "--hidden-import=langchain_community",
    "--hidden-import=dotenv",
    "--hidden-import=psutil",
    "--hidden-import=pystray",
    "--hidden-import=PIL",
    "--hidden-import=pywebview",
    "--hidden-import=clr_loader",
    "--hidden-import=pythonnet",
    "--hidden-import=pydantic",
    "--hidden-import=sqlitedict",
    "--clean"
]

# Exclude unnecessary large modules (Common in Anaconda/Largeenvs)
excludes = [
    'matplotlib', 'notebook', 'scipy', 'pandas', 'numpy', 'tkinter', 
    'astropy', 'sklearn', 'skimage', 'PIL.ImageQt', 'PIL.ImageTk',
    'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'cv2', 'IPython'
]
for ex in excludes:
    build_args.extend(['--exclude-module', ex])

print(f"[*] Running PyInstaller with arguments: {' '.join(build_args)}")

try:
    PyInstaller.__main__.run(build_args)
    print(f"\n[+] Build successful! Your app is ready in the 'dist' folder as {APP_NAME}.exe")
except Exception as e:
    print(f"\n[!] Build failed: {e}")
