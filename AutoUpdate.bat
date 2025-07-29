@echo off
cd "%USERPROFILE%\OneDrive\Documents\Code\Python tkinter\Create Shortcut on PC Emulator"

echo === Building executable with PyInstaller ===
pyinstaller ^
  --noconsole ^
  --onefile ^
  --icon=icon.ico ^
  "Create Shortcut Emulator.py"

echo === Creating ZIP archive ===
powershell -Command "Compress-Archive -Path 'dist\*' -DestinationPath 'Create_Shortcut_On_PC_Emulator.zip' -Force"

echo === Done! ===