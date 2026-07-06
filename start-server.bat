@echo off
rem index.html のダブルクリックで動かない場合のみ使用
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
  start http://localhost:8123
  python -m http.server 8123
) else (
  where npx >nul 2>nul
  if %errorlevel%==0 (
    start http://localhost:8123
    npx --yes serve -l 8123 .
  ) else (
    echo Python も Node.js も見つかりませんでした。どちらかをインストールしてください。
    pause
  )
)
