import PyInstaller.__main__
import os

# Define the icons and paths
icon_path = "app_icon.png"
ui_folder = "ui"

# Exclude large unnecessary modules to keep EXE small and build fast
excludes = [
    'matplotlib', 'notebook', 'scipy', 'pandas', 'numpy', 'jedi', 'IPython', 
    'tkinter', 'PyQt5', 'PySide2', 'PySide6'
]

exclude_args = []
for ex in excludes:
    exclude_args.extend(['--exclude-module', ex])

PyInstaller.__main__.run([
    'app.py',
    '--name=PCx-Guard',
    '--noconsole',
    '--onefile',
    f'--add-data={ui_folder};{ui_folder}',
    f'--add-data={icon_path};.',
    f'--icon={icon_path}',
    '--hidden-import=pywebview',
    '--hidden-import=psutil',
    '--hidden-import=pystray',
    '--hidden-import=PIL',
    '--hidden-import=clr_loader',
    '--hidden-import=pythonnet',
    '--clean',
] + exclude_args)
