@echo off
chcp 65001 > nul
title INNOVA - Generador de Costura

echo.
echo  +------------------------------------------+
echo  ^|      INNOVA - Generador de Costura       ^|
echo  +------------------------------------------+
echo.

set CARPETA_CORTADOS=%~dp0cortados

if not exist "%CARPETA_CORTADOS%" (
    echo [ERROR] No se encontro la carpeta: %CARPETA_CORTADOS%
    echo Asegurate de ejecutar este .bat desde la carpeta del proyecto.
    pause
    exit /b 1
)

python "%~dp0generar_costura.py" "%CARPETA_CORTADOS%"

echo.
echo  El PDF fue guardado en la carpeta /costura/
echo.
pause
