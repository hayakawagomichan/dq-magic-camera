@echo off
rem 会議終了ヘルパーを起動（会議モードを使うときだけ必要）
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
  python dq-helper.py
) else (
  echo Python が見つかりません。https://www.python.org/ からインストールしてください。
)
pause
