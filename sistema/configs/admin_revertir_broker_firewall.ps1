#Requires -RunAsAdministrator
# Deshace admin_configurar_broker_firewall.ps1 (restaura Mosquitto original y borra las reglas).
$MosqDir = 'C:\Program Files\mosquitto'
$Orig = Join-Path $MosqDir 'mosquitto.conf.original'
if (Test-Path $Orig) { Copy-Item $Orig (Join-Path $MosqDir 'mosquitto.conf') -Force; Restart-Service mosquitto; Write-Host 'mosquitto.conf original restaurado' }
foreach ($n in 'Riego Casa - MQTT 1883 (LAN)', 'Riego Casa - Node-RED 1880 (LAN)') {
    Get-NetFirewallRule -DisplayName $n -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    Write-Host "Regla eliminada (si existia): $n"
}
Write-Host 'La categoria de red (Privada/Publica) no se modifica; cambiala en Configuracion > Red si lo deseas.'
