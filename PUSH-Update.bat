@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  대시보드 데이터 업데이트 중...
echo  -------------------------------------------

git add data/influencers.csv config.json
git diff --cached --quiet
if %errorlevel%==0 (
  echo  [!] 새로 수집된 데이터가 없습니다. 먼저 계정을 수집하세요.
  echo.
  pause
  exit /b 0
)

for /f "tokens=1-2 delims= " %%a in ('powershell -command "Get-Date -Format 'yyyy-MM-dd HH:mm'"') do set DATETIME=%%a %%b
git commit -m "데이터 업데이트 %DATETIME%"
git push

echo.
echo  완료! Streamlit Cloud가 자동으로 최신 데이터를 반영합니다.
echo  (반영까지 1~2분 소요)
echo  -------------------------------------------
echo.
pause
