@echo off
pushd "%~dp0"
title Painel de Lances

if exist "Painel_Robo_Lance.exe" (
    start "" Painel_Robo_Lance.exe
    popd
    exit
)

set PYTHON_CMD=
where python >nul 2>&1
if %errorlevel% equ 0 set PYTHON_CMD=python
if "%PYTHON_CMD%"=="" (
    where py >nul 2>&1
    if %errorlevel% equ 0 set PYTHON_CMD=py
)

if "%PYTHON_CMD%"=="" (
    echo ========================================================
    echo ERRO: Python nao foi encontrado neste computador!
    echo ========================================================
    echo.
    echo Para rodar o robo neste PC:
    echo 1. Instale o Python (https://www.python.org/downloads/)
    echo 2. IMPORTANTE: Marque a opcao "Add Python to PATH" na instalacao!
    echo 3. Abra o CMD e execute: pip install selenium
    echo.
    pause
    popd
    exit /b 1
)

%PYTHON_CMD% painel_lances.py
if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo O Painel encerrou com erro! Veja a mensagem acima.
    echo ========================================================
    pause
)
popd



