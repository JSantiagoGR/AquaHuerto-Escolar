@echo off
REM Clic derecho sobre este archivo -> "Ejecutar como administrador"
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo.
  echo  Este archivo debe abrirse con clic derecho - "Ejecutar como administrador".
  echo.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0admin_configurar_broker_firewall.ps1"
echo.
pause
