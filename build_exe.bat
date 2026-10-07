@echo off
rem Сборка Relacs.exe на Windows (нужен Python 3.10+)
python -m pip install --upgrade pygame pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name Relacs --icon icon.ico ^
  --add-data "*.mp3;." --add-data "iop.ogg;." --add-data "icon.png;." Relacs.py
echo Готово: dist\Relacs.exe
pause
