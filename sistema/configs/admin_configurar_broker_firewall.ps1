#Requires -RunAsAdministrator
<#
  CONFIGURACION DE ADMINISTRADOR (UNA SOLA VEZ) - ENTORNO CASA
  ------------------------------------------------------------
  Forma facil: clic derecho en CONFIGURAR_BROKER_Y_FIREWALL.bat -> "Ejecutar como administrador".

  Que hace:
   1. Respalda C:\Program Files\mosquitto\mosquitto.conf (mosquitto.conf.original).
   2. Hace que el servicio "mosquitto" cargue la configuracion del proyecto
      (usuarios, ACL, persistencia) mediante include_dir.
   3. Reinicia el servicio y comprueba que escucha en el puerto 1883.
   4. Crea dos reglas de firewall de entrada SOLO para la subred local y el
      perfil de red PRIVADO: MQTT 1883 y Node-RED 1880. Nada queda abierto
      a internet ni en redes publicas.
   5. (Pregunta antes) Marca la red Wi-Fi actual como PRIVADA, necesario para
      que las reglas apliquen en tu red de casa.
  Todo lo que pasa queda registrado en configs\ultimo_resultado_admin.txt
  Para deshacer: configs\admin_revertir_broker_firewall.ps1
#>
$ErrorActionPreference = 'Continue'
$Proyecto = 'C:\ESP32_Riego_Automatico\Pruebas_Casa_ESP32_v1'
Start-Transcript -Path (Join-Path $Proyecto 'configs\ultimo_resultado_admin.txt') -Force | Out-Null
$MosqDir  = 'C:\Program Files\mosquitto'
$Conf     = Join-Path $MosqDir 'mosquitto.conf'
$Orig     = Join-Path $MosqDir 'mosquitto.conf.original'
$IncDir   = ($Proyecto -replace '\\', '/') + '/mqtt/conf.d'

Write-Host '== 1. Respaldo de la configuracion original de Mosquitto ==' -ForegroundColor Cyan
if (-not (Test-Path $Orig)) { Copy-Item $Conf $Orig; Write-Host "Respaldo: $Orig" } else { Write-Host 'El respaldo ya existia (no se sobrescribe)' }

Write-Host '== 2. Servicio mosquitto -> configuracion del proyecto ==' -ForegroundColor Cyan
$texto = "# Configuracion del servicio Mosquitto - Riego inteligente ENTORNO CASA`n# Original respaldado en mosquitto.conf.original`ninclude_dir $IncDir`n"
[IO.File]::WriteAllText($Conf, $texto, (New-Object Text.UTF8Encoding($false)))
Write-Host "mosquitto.conf -> include_dir $IncDir"

Write-Host '== 3. Reinicio del servicio ==' -ForegroundColor Cyan
Set-Service mosquitto -StartupType Automatic
try { Restart-Service mosquitto -ErrorAction Stop } catch { Write-Host "ERROR al iniciar el servicio: $_" -ForegroundColor Red }
Start-Sleep -Seconds 3
if ((Get-Service mosquitto).Status -ne 'Running') {
    Write-Host 'Diagnostico: ejecutando mosquitto con la misma configuracion...' -ForegroundColor Yellow
    $err = Join-Path $Proyecto 'configs\diag_mosquitto_err.txt'
    $out = Join-Path $Proyecto 'configs\diag_mosquitto_out.txt'
    $p = Start-Process -FilePath (Join-Path $MosqDir 'mosquitto.exe') -ArgumentList '-c', "`"$Conf`"", '-v' `
         -RedirectStandardError $err -RedirectStandardOutput $out -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 4
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force; Start-Sleep -Seconds 1 }
    Get-Content $err, $out -ErrorAction SilentlyContinue | Select-Object -Last 20
    try { Start-Service mosquitto -ErrorAction Stop } catch { Write-Host "Segundo intento fallido: $_" -ForegroundColor Red }
    Start-Sleep -Seconds 2
}
Get-Service mosquitto | Format-Table Name, Status, StartType
Get-NetTCPConnection -State Listen -LocalPort 1883 -ErrorAction SilentlyContinue | Format-Table LocalAddress, LocalPort, OwningProcess

Write-Host '== 4. Reglas de firewall (solo subred local, perfil Privado) ==' -ForegroundColor Cyan
foreach ($r in @(
    @{ Name = 'Riego Casa - MQTT 1883 (LAN)';     Port = 1883 },
    @{ Name = 'Riego Casa - Node-RED 1880 (LAN)'; Port = 1880 })) {
    Get-NetFirewallRule -DisplayName $r.Name -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -DisplayName $r.Name -Direction Inbound -Protocol TCP -LocalPort $r.Port `
        -RemoteAddress LocalSubnet -Profile Private -Action Allow | Out-Null
    Write-Host "Regla creada: $($r.Name)"
}

Write-Host '== 5. Categoria de la red Wi-Fi ==' -ForegroundColor Cyan
$perfil = Get-NetConnectionProfile -InterfaceAlias 'Wi-Fi' -ErrorAction SilentlyContinue
if ($perfil) {
    Write-Host "Red actual: $($perfil.Name) -> $($perfil.NetworkCategory)"
    if ($perfil.NetworkCategory -ne 'Private') {
        $resp = Read-Host "Marcar '$($perfil.Name)' como red PRIVADA (solo si es tu red de casa). Escribe S y presiona Enter"
        if ($resp -match '^[sS]') {
            Set-NetConnectionProfile -InterfaceAlias 'Wi-Fi' -NetworkCategory Private
            Write-Host 'Red marcada como Privada.'
        } else {
            Write-Host 'Sin cambios: el ESP32 y el celular NO podran conectarse mientras la red sea Publica.' -ForegroundColor Yellow
        }
    }
    Get-NetConnectionProfile -InterfaceAlias 'Wi-Fi' | Format-Table Name, NetworkCategory
}
Write-Host 'LISTO. Ya puedes cerrar esta ventana.' -ForegroundColor Green
Stop-Transcript | Out-Null
Read-Host 'Presiona Enter para cerrar'
