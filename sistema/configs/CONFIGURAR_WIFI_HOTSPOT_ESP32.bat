@echo off
title CONFIGURAR WI-FI DEL ESP32 - HOTSPOT DEL IPHONE
echo.
echo  ============================================================
echo   CONFIGURAR WI-FI DEL ESP32: HOTSPOT DEL IPHONE
echo   Red: iPhone de Jaime Santiago  (ranura "tec", queda como preferida;
echo        la red de la casa se conserva como respaldo)
echo.
echo   ANTES: en el iPhone activa "Maximizar compatibilidad"
echo   (Compartir Internet) y conecta esta laptop al hotspot.
echo.
echo   Escribe SOLO la contrasena del hotspot y presiona Enter.
echo   Las letras NO aparecen al escribir (es normal).
echo  ============================================================
echo.
"%~dp0..\.venv\Scripts\python.exe" "%~dp0..\firmware\tools\provisionar_red.py" --port COM8 --red tec --ssid "iPhone de Jaime Santiago"
echo.
echo  Puedes cerrar esta ventana.
pause
