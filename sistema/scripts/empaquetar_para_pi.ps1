<#
  Crea backups\paquete_raspberry_pi_<fecha>.zip con TODO el proyecto necesario para
  instalarlo en la Raspberry Pi, SIN contraseñas, bases de datos, node_modules,
  compilaciones ni el respaldo de la flash del ESP32.
#>
$R = Split-Path -Parent $PSScriptRoot
$stamp = Get-Date -Format 'yyyyMMdd_HHmm'
$tmp = Join-Path $env:TEMP "riego_pi_$stamp"
$zip = Join-Path $R "backups\paquete_raspberry_pi_$stamp.zip"
$excl = @('\\\.venv\\', '\\node_modules\\', '\\configs\\secrets\\', '\\firmware\\build', '\\firmware\\managed_components\\',
          '\\backups\\', '\\run\\', '\\mqtt\\data', '\\mqtt\\log\\', '\\mqtt\\passwd$', '\\nodered\\logs\\',
          '\\tests\\host\\build\\', '\\__pycache__\\', '\.db$', '\.db-', '_cred\.json$', '\\nodered\\userdata\\context\\',
          '\\firmware\\sdkconfig$', '\\firmware\\sdkconfig\.old$', '\\simulation\\estado_simulador\.json$', '\.log$', '\.err$',
          '\\\.config\.', '\\\.sessions\.json$')
$files = Get-ChildItem $R -Recurse -File | Where-Object {
    $p = $_.FullName
    -not ($excl | Where-Object { $p -match $_ })
}
foreach ($f in $files) {
    $rel = $f.FullName.Substring($R.Length + 1)
    $dst = Join-Path $tmp $rel
    New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
    Copy-Item $f.FullName $dst
}
# Verificación: ninguna contraseña del archivo de secretos dentro del paquete
$sec = Get-Content (Join-Path $R 'configs\secrets\credenciales_casa.env') | Where-Object { $_ -match 'PASS=|SECRET=' } | ForEach-Object { $_.Split('=', 2)[1] }
$leak = Get-ChildItem $tmp -Recurse -File | Select-String -SimpleMatch -Pattern $sec -List
if ($leak) { Remove-Item $tmp -Recurse -Force; throw "ABORTADO: se encontraron secretos en $($leak.Path)" }
Compress-Archive -Path "$tmp\*" -DestinationPath $zip -Force
Remove-Item $tmp -Recurse -Force
"Paquete: $zip ($([math]::Round((Get-Item $zip).Length / 1MB, 2)) MB, $($files.Count) archivos, sin secretos)"
