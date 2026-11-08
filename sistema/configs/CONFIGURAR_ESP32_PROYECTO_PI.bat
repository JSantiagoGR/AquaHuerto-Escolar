@echo off
title ESP32 -> EQUIPO 2 PROYECTO (Raspberry Pi)
set PUERTO=%~1
if "%PUERTO%"=="" set PUERTO=COM3
echo.
echo  ============================================================
echo   CONECTAR EL ESP32 (%PUERTO%) AL PROYECTO EN LA RASPBERRY PI
echo   Wi-Fi: RouterHuerto1 (ranura "huerto", queda como preferida)
echo   Broker: mqtt://raspberrypi.local:1884 (broker propio, con usuario)
echo   Topic:  huerto/final/esp32_principal
echo.
echo   Escribe SOLO la contrasena del Wi-Fi RouterHuerto1 y Enter.
echo   Las letras NO aparecen al escribir (es normal).
echo  ============================================================
echo.
"%~dp0..\.venv\Scripts\python.exe" "%~dp0..\firmware\tools\provisionar_red.py" --port %PUERTO% --red huerto --ssid "RouterHuerto1" --broker "mqtt://raspberrypi.local:1884" --topic huerto/final/esp32_principal --device esp32_principal --entorno final --env-file "%~dp0secrets\credenciales_final.env"
echo.
echo  Puedes cerrar esta ventana.
pause
