@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv" (
  echo 먼저 START-Windows.bat 을 한 번 실행해서 설치를 완료해주세요.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
echo.
echo  config.json 의 influencers 목록을 수집합니다 (계정당 8~20초 대기).
echo  -------------------------------------------
python scraper\collect.py
echo.
echo  완료! PUSH-Update.bat 을 실행하면 대시보드에 반영됩니다.
pause
