@echo off
title CONFIGURAR WI-FI DEL ESP32
echo.
echo  ============================================================
echo   CONFIGURAR WI-FI DEL ESP32
echo   Red: RED_DE_CASA_2.4  (la de 2.4 GHz de tu modem)
echo.
echo   Escribe SOLO la contrasena del Wi-Fi y presiona Enter.
echo   Las letras NO aparecen al escribir (es normal).
echo  ============================================================
echo.
"%~dp0..\.venv\Scripts\python.exe" "%~dp0..\firmware\tools\provisionar_red.py" --port COM8 --red casa --ssid "RED_DE_CASA_2.4"
echo.
echo  Puedes cerrar esta ventana.
pause
