@echo off
echo Installing Weather Flick Admin Backend Requirements...
echo.
cd /d "%~dp0"
pip install -r requirements.txt
echo.
echo Requirements installed successfully!
pause
