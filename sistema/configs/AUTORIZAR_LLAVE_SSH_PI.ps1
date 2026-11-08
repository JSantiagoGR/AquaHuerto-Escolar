# Autoriza la llave SSH de esta laptop en la Raspberry Pi (una sola vez).
# Pide el usuario y luego la CONTRASEÑA de la Pi (la escribe la persona; no se guarda en ningún archivo).
# Efecto en la Pi: agrega UNA línea al final de ~/.ssh/authorized_keys de ese usuario. Nada más.
$R = Split-Path -Parent $PSScriptRoot
$key = "$env:USERPROFILE\.ssh\equipo2_pi.pub"
Write-Host ""
Write-Host "=== AUTORIZAR LA LAPTOP EN LA RASPBERRY PI (raspberrypi.local) ===" -ForegroundColor Cyan
$u = Read-Host "Usuario SSH de la Raspberry Pi"
if (-not $u) { Write-Host "Sin usuario: no se hizo nada."; Read-Host "Enter para cerrar"; exit 1 }
New-Item -ItemType Directory -Force "$R\run" | Out-Null
Set-Content -Path "$R\run\pi_usuario.txt" -Value $u.Trim() -Encoding ascii
Write-Host ""
Write-Host "Ahora escribe la CONTRASEÑA de la Pi cuando la pida (no se ve al escribir)." -ForegroundColor Yellow
Get-Content $key | ssh -o StrictHostKeyChecking=accept-new "$($u.Trim())@raspberrypi.local" "umask 077; mkdir -p ~/.ssh; touch ~/.ssh/authorized_keys; cat >> ~/.ssh/authorized_keys; echo LLAVE_LISTA"
Write-Host ""
Write-Host "Si arriba dice LLAVE_LISTA, ya puedes cerrar esta ventana y avisar en el chat." -ForegroundColor Green
Read-Host "Enter para cerrar"
