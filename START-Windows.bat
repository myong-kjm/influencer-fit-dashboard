@echo off
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python이 설치되어 있지 않습니다. https://www.python.org/downloads/ 에서 설치해주세요.
  pause
  exit /b 1
)

if not exist ".venv" (
  echo  최초 실행 — 가상환경을 만들고 필요한 패키지를 설치합니다...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)

echo.
echo  대시보드를 브라우저에서 엽니다...
streamlit run dashboard\app.py
pause
