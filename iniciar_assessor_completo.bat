@echo off
chcp 65001 >nul
setlocal
title Assessor Financeiro - Telegram

set "PROJECT_DIR=%~dp0"
set "VENV_PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "APP_FILE=%PROJECT_DIR%\app.py"

cd /d "%PROJECT_DIR%" 2>nul
if errorlevel 1 (
    echo [ERRO] Nao foi possivel acessar: %PROJECT_DIR%
    pause
    exit /b 1
)

if not exist "%VENV_PYTHON%" (
    echo [ERRO] Ambiente Python nao encontrado: %VENV_PYTHON%
    pause
    exit /b 1
)
if not exist "%APP_FILE%" (
    echo [ERRO] Arquivo nao encontrado: %APP_FILE%
    pause
    exit /b 1
)

echo ============================================
echo  Assessor Financeiro - Telegram
echo ============================================
echo.
echo Iniciando Telegram nesta janela...
echo Para encerrar, pressione CTRL+C.
echo.

"%VENV_PYTHON%" "%APP_FILE%"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
    echo O Telegram foi encerrado normalmente.
) else (
    echo [ERRO] Telegram encerrado com codigo %EXIT_CODE%.
)
pause
endlocal & exit /b %EXIT_CODE%
