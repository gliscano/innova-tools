@echo off
title INNOVA - Cortador de Fondos para Sublimacion

echo.
echo ============================================================
echo   INNOVA - Cortador de Fondos para Sublimacion
echo ============================================================
echo.

REM Verificar que Python este instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en el PATH.
    echo.
    echo Para instalarlo:
    echo   1. Ir a https://www.python.org/downloads/
    echo   2. Descargar la ultima version
    echo   3. Al instalar, MARCAR la casilla "Add Python to PATH"
    echo   4. Reiniciar la PC despues de instalar
    echo.
    echo IMPORTANTE: Si ya lo instalaste pero no marcaste "Add to PATH",
    echo desinstalalo y volvelo a instalar marcando esa opcion.
    echo.
    pause
    exit /b 1
)

REM Verificar que Pillow este instalado
python -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo Instalando libreria Pillow...
    pip install Pillow
    echo.
)

echo Arrastra la carpeta con los JPG a esta ventana y presiona ENTER,
echo o presiona ENTER directamente para usar la carpeta donde esta este archivo:
echo.
set /p CARPETA="Carpeta: "

REM Si no ingreso nada, usar la carpeta del .bat
if "%CARPETA%"=="" set CARPETA=%~dp0

REM Quitar comillas si las tiene
set CARPETA=%CARPETA:"=%

echo.
echo ------------------------------------------------------------
echo  Procesando archivos...
echo ------------------------------------------------------------
echo.

python "%~dp0cortador_innova.py" "%CARPETA%"

echo.
pause
