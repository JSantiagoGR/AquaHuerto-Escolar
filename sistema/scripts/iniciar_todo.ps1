<#
  INICIAR TODO - Entorno CASA del riego inteligente
  Uso:  powershell -ExecutionPolicy Bypass -File scripts\iniciar_todo.ps1 [-Simulador] [-Abrir] [-Desplegar]
   -Simulador : inicia también el simulador (dispositivo sim_01, datos SIMULADOS)
   -Abrir     : abre el dashboard en el navegador
   -Desplegar : vuelve a generar y desplegar el flujo de Node-RED
   -EspejoPi  : copia en vivo (solo lectura) el ESP32 del proyecto desde la Raspberry Pi (esp32_principal)
  No requiere permisos de administrador. No toca otras instancias de Node-RED.
#>
param([switch]$Simulador, [switch]$Abrir, [switch]$Desplegar, [switch]$EspejoPi)
$ErrorActionPreference = 'Stop'
$R = Split-Path -Parent $PSScriptRoot
$Run = Join-Path $R 'run'
New-Item -ItemType Directory -Force $Run, (Join-Path $R 'nodered\logs'), (Join-Path $R 'mqtt\log'), (Join-Path $R 'mqtt\data_usuario') | Out-Null
$Py = Join-Path $R '.venv\Scripts\python.exe'

function Listening($port) { [bool](Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) }
function Started($name, $proc) { Set-Content -Path (Join-Path $Run "$name.pid") -Value $proc.Id -Encoding ascii }

Write-Host '== 1. Broker MQTT (Mosquitto, puerto 1883) ==' -ForegroundColor Cyan
if (Listening 1883) {
    Write-Host 'Ya hay un broker escuchando en 1883 (servicio o instancia previa): se reutiliza.'
} else {
    $p = Start-Process -FilePath 'C:\Program Files\mosquitto\mosquitto.exe' -ArgumentList '-c', "`"$R\mqtt\mosquitto_casa.conf`"" -WindowStyle Hidden -PassThru
    Started 'mosquitto' $p
    Start-Sleep -Seconds 2
    if (-not (Listening 1883)) { throw 'Mosquitto no arranco: revise mqtt\log\broker_usuario.log' }
    Write-Host "Mosquitto iniciado (PID $($p.Id))"
}

Write-Host '== 2. Base de datos SQLite ==' -ForegroundColor Cyan
& $Py (Join-Path $R 'database\inicializar_db.py')

Write-Host '== 3. Node-RED (puerto 1880, instancia aislada) ==' -ForegroundColor Cyan
if (Listening 1880) {
    Write-Host 'Node-RED ya esta escuchando en 1880.'
} else {
    $red = Join-Path $R 'nodered\runtime\node_modules\node-red\red.js'
    $ud = Join-Path $R 'nodered\userdata'
    $log = Join-Path $R 'nodered\logs\nodered.log'
    $p = Start-Process -FilePath 'node' -ArgumentList "`"$red`"", '--userDir', "`"$ud`"", '--settings', "`"$ud\settings.js`"" `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
    Started 'nodered' $p
    $ok = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 1
        try { Invoke-WebRequest -Uri 'http://127.0.0.1:1880/' -UseBasicParsing -TimeoutSec 2 | Out-Null; $ok = $true; break } catch { }
    }
    if (-not $ok) { throw 'Node-RED no respondio en 60 s: revise nodered\logs\nodered.log' }
    Write-Host "Node-RED iniciado (PID $($p.Id))"
}
if ($Desplegar) {
    & $Py (Join-Path $R 'dashboard\generar_flows.py') --entorno casa
    & $Py (Join-Path $R 'nodered\desplegar_flows.py') --entorno casa
}

if ($Simulador) {
    Write-Host '== 4. Simulador (sim_01, DATOS SIMULADOS) ==' -ForegroundColor Cyan
    $pidFile = Join-Path $Run 'simulador.pid'
    $running = $false
    if (Test-Path $pidFile) { $running = [bool](Get-Process -Id (Get-Content $pidFile) -ErrorAction SilentlyContinue) }
    if ($running) { Write-Host 'El simulador ya esta corriendo.' } else {
        $log = Join-Path $R 'simulation\simulador.log'
        $p = Start-Process -FilePath $Py -ArgumentList "`"$R\simulation\simulador_huerto.py`"" -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
        Started 'simulador' $p
        Write-Host "Simulador iniciado (PID $($p.Id))"
    }
}

if ($EspejoPi) {
    Write-Host '== 5. Espejo de la Raspberry Pi (esp32_principal, SOLO LECTURA) ==' -ForegroundColor Cyan
    $pidFile = Join-Path $Run 'espejo_pi.pid'
    $running = $false
    if (Test-Path $pidFile) { $running = [bool](Get-Process -Id (Get-Content $pidFile) -ErrorAction SilentlyContinue) }
    if ($running) { Write-Host 'El espejo ya esta corriendo.' } else {
        $log = Join-Path $Run 'espejo_pi.log'
        $p = Start-Process -FilePath $Py -ArgumentList "`"$R\scripts\espejo_pi.py`"" -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
        Started 'espejo_pi' $p
        Write-Host "Espejo iniciado (PID $($p.Id)); registro en run\espejo_pi.log"
    }
}

$ip = (Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway } | Select-Object -First 1).IPv4Address.IPAddress
Write-Host ''
Write-Host 'LISTO' -ForegroundColor Green
Write-Host "  Dashboard:  http://localhost:1880/dashboard   (en el celular: http://${ip}:1880/dashboard)"
Write-Host '  Editor:     http://localhost:1880   (usuario y contrasena en configs\secrets\credenciales_casa.env)'
Write-Host "  Broker:     mqtt://${ip}:1883 (solo red local, con usuario)"
if ($Abrir) { Start-Process 'http://localhost:1880/dashboard' }
