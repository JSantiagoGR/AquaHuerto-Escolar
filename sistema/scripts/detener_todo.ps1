<#
  DETENER TODO - Entorno CASA
  Detiene SOLO los procesos que inició iniciar_todo.ps1 (archivos run\*.pid).
  No detiene otras instancias de Node-RED ni el servicio de Windows de Mosquitto.
  El ESP32 sigue funcionando por su cuenta con sus protecciones locales.
#>
$R = Split-Path -Parent $PSScriptRoot
$Run = Join-Path $R 'run'
foreach ($name in 'espejo_pi', 'simulador', 'nodered', 'mosquitto') {
    $f = Join-Path $Run "$name.pid"
    if (-not (Test-Path $f)) { Write-Host "$name : no iniciado por estos scripts"; continue }
    $procId = [int](Get-Content $f)
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($p) {
        Stop-Process -Id $procId -Force
        Write-Host "$name detenido (PID $procId)"
    } else {
        Write-Host "$name ya no estaba corriendo"
    }
    Remove-Item $f -Force
}
Write-Host 'Listo. Los datos quedan guardados en database\riego_casa.db.' -ForegroundColor Green
