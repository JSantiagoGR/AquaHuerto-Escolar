# Espera a que la laptop este en RouterHuerto1 (la Pi responde por SSH) y corre el instalador del bot de Telegram.
# Uso: powershell -ExecutionPolicy Bypass -File scripts\esperar_e_instalar_bot.ps1
$R = Split-Path -Parent $PSScriptRoot
$llave = Join-Path $env:USERPROFILE '.ssh\equipo2_pi'
Write-Host 'Esperando a que la laptop se conecte a RouterHuerto1 (Ctrl+C para cancelar)...' -ForegroundColor Cyan
while ($true) {
    $ok = & ssh -i $llave -o BatchMode=yes -o ConnectTimeout=4 pi@raspberrypi.local 'echo ok' 2>$null
    if ($ok -eq 'ok') { break }
    Write-Host ('  {0}  la Pi todavia no responde; reintento en 10 s' -f (Get-Date -Format 'HH:mm:ss'))
    Start-Sleep -Seconds 10
}
Write-Host ''
Write-Host 'Conectado a la Pi. Iniciando el instalador del bot...' -ForegroundColor Green
Write-Host 'Cuando pida el token: copialo del chat con BotFather y pegalo aqui con clic derecho (no se vera), luego Enter.' -ForegroundColor Yellow
Write-Host ''
Set-Location $R
& python (Join-Path $R 'scripts\instalar_bot_telegram_pi.py')
