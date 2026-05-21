# Alisha PowerShell Launcher
Write-Host "🎭 Iniciando Alisha - Asistente IA Completa" -ForegroundColor Cyan
Write-Host "=" -Repeat 50 -ForegroundColor Gray

Set-Location $PSScriptRoot

Write-Host "✨ Iniciando sistema completo..." -ForegroundColor Green
Write-Host "🎵 Voz femenina natural mejorada" -ForegroundColor Yellow
Write-Host "🖱️ Seguimiento de mouse interactivo" -ForegroundColor Yellow  
Write-Host "👁️ Observacion inteligente de pantalla" -ForegroundColor Yellow
Write-Host "🤖 Motor de IA con Llama 3.1" -ForegroundColor Yellow
Write-Host "🌐 Interfaz web automatica" -ForegroundColor Yellow
Write-Host ""

try {
    python desktop_widget.py
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 Verifica que Python y las dependencias estén instaladas" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "👋 Alisha cerrada" -ForegroundColor Cyan
Read-Host "Presiona Enter para cerrar"