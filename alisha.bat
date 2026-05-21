@echo off
chcp 65001 >nul 2>&1
title Alisha - Asistente IA Completa
cd /d "%~dp0"

echo.
echo        🎭 ALISHA - ASISTENTE IA COMPLETA 🎭
echo    ================================================
echo.
echo    ✨ Iniciando sistema completo...
echo    🎵 Voz femenina natural mejorada
echo    🖱️ Seguimiento de mouse interactivo  
echo    👁️ Observacion inteligente de pantalla
echo    🤖 Motor de IA con Llama 3.1
echo    🌐 Interfaz web automatica
echo    🤫 Modo silencioso activado
echo.

REM Verificar que Python esté disponible
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no está instalado o no está en el PATH
    echo 💡 Instala Python desde https://python.org
    pause
    exit /b 1
)

REM Ejecutar Alisha en background (no bloquea el terminal)
start "" /B pythonw desktop_widget.py
if errorlevel 1 (
    echo.
    echo ⚠️ Hubo un problema iniciando Alisha
    echo 🔧 Intentando modo web alternativo...
    echo.
    start "" /B pythonw iniciar_web.py
)

echo.
echo    ✅ Alisha iniciada — esta ventana se puede cerrar
timeout /t 3 /nobreak >nul