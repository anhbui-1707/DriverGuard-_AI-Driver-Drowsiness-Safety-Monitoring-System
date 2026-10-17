@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv
    if errorlevel 1 py -3.12 -m venv .venv
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -c "import cv2,mediapipe,numpy,tensorflow,PIL; print('Dependencies OK')" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto fail
)
if not exist "models\face_landmarker.task" goto missing_model
if not exist "models\eye_model_cew_v3_float32.tflite" goto missing_model
if not exist "models\yawn_model_v2_float32.tflite" goto missing_model
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto fail
exit /b 0
:missing_model
echo Missing AI model files. Extract the complete DriverGuard package again.
pause
exit /b 1
:fail
echo Setup or startup failed. Install Python 3.11/3.12 64-bit and read the error above.
pause
exit /b 1
