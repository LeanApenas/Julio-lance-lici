@echo off
pushd "%~dp0"
title Abrir Google Chrome - Porta 9222
echo ========================================================
echo   Iniciando Google Chrome em Modo de Depuracao (Porta 9222)
echo ========================================================
echo.

set CHROME_PATH=""

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
) else (
    set CHROME_PATH=chrome.exe
)

start "" %CHROME_PATH% --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data Debug"

echo.
echo [OK] Chrome iniciado com sucesso!
echo 1. Faca login no portal de licitacao e va ate a tela dos lances.
echo 2. Depois, execute 'iniciar_robo.bat' para abrir o Painel (ON/OFF).
echo.
pause
popd

