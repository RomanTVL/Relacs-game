@echo off
rem Сборка Relacs.exe и StarStorm.exe на Windows (нужен Python 3.10+)
python -m pip install --upgrade pygame pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name Relacs --icon icon.ico ^
  --add-data "*.mp3;." --add-data "iop.ogg;." --add-data "icon.png;." Relacs.py
python -m PyInstaller --noconfirm --onefile --windowed --name StarStorm --icon star_icon.ico ^
  --add-data "Relacs2.mp3;." --add-data "burning.mp3;." --add-data "under the moon.mp3;." ^
  --add-data "haos.mp3;." --add-data "Glitc.mp3;." --add-data "night.mp3;." ^
  --add-data "harmony_music.mp3;." --add-data "star_icon.png;." StarStorm.py
echo Готово: dist\Relacs.exe и dist\StarStorm.exe
pause
