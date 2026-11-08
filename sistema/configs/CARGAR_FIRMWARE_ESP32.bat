@echo off
title Cargar firmware al ESP32 (solo la aplicacion: conserva red, configuracion e IA)
set PUERTO=%~1
if "%PUERTO%"=="" set PUERTO=COM8
echo.
echo  Cargando el firmware compilado al ESP32 en %PUERTO% (solo la aplicacion).
echo  Conserva el Wi-Fi, la configuracion, el modo, los litros y lo aprendido por la IA.
echo  Conecte el ESP32 por su micro-USB con un cable de DATOS.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command ". 'C:\Espressif\tools\Microsoft.v6.0.2.PowerShell_profile.ps1' *> $null; Set-Location '%~dp0..\firmware'; idf.py -p %PUERTO% -b 115200 app-flash"
echo.
pause
