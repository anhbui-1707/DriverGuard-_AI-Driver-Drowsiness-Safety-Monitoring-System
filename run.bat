@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv
    if errorlevel 1 py -3.12 -m venv .venv
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] in ((3,11),(3,12)); import streamlit, cv2, mediapipe, numpy; assert streamlit.__version__=='1.44.1' and mediapipe.__version__=='0.10.21' and numpy.__version__=='1.26.4' and cv2.__version__=='4.11.0'" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" scripts\download_model.py
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1
exit /b
:fail
echo Setup failed. Install Python 3.11 or 3.12 64-bit and check the message above.
pause
exit /b 1
