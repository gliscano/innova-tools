@echo off
chcp 65001 >nul
title INNOVA - Generar lista para etiquetado
cd /d "%~dp0"

REM Verificar/instalar dependencias
python -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo Instalando Pillow...
    pip install Pillow
)
python -c "import reportlab" >nul 2>&1
if errorlevel 1 (
    echo Instalando ReportLab...
    pip install reportlab
)

python generar_lista_etiquetado.py %*
if errorlevel 1 (
  echo.
  echo [ERROR] No se pudo ejecutar. Verifica que Python este instalado.
  echo.
  pause
)
