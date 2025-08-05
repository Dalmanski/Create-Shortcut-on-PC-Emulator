@echo off
cd "%USERPROFILE%\OneDrive\Documents\Code\Python tkinter\Create Shortcut on PC Emulator"

set "VERSION=1.0"

echo === Building executable with PyInstaller ===
pyinstaller ^
  --noconsole ^
  --onefile ^
  --icon=icon.ico ^
  --hidden-import=help ^
  --hidden-import=settings ^
  --hidden-import=jaypy ^
  "Create Shortcut Emulator.py"

echo === Updating version in settings.json ===
powershell -Command ^
  "$path = 'dist/settings.json';" ^
  "$json = Get-Content $path | ConvertFrom-Json;" ^
  "$json.version = '%VERSION%';" ^
  "$json | ConvertTo-Json -Depth 100 | Set-Content $path"

echo === Creating ZIP archive ===
powershell -Command "Compress-Archive -Path 'dist\*' -DestinationPath 'Create_Shortcut_On_PC_Emulator.zip' -Force"

echo === Done! ===
