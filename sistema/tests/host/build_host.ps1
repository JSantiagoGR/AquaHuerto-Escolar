# Compila la logica pura del firmware para la PC con zig cc (paquete ziglang del venv)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$fw = Join-Path $root 'firmware\main'
$py = Join-Path $root '.venv\Scripts\python.exe'
$out = Join-Path $PSScriptRoot 'build'
New-Item -ItemType Directory -Force $out | Out-Null
$src = @('app_types.c','config_table.c','irrigation_logic.c','ia_model.c','sensor_filter.c','logic_tests.c') | ForEach-Object { Join-Path $fw $_ }
$flags = @('-DHOST_BUILD','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter',"-I$fw")
& $py -m ziglang cc @flags @src (Join-Path $PSScriptRoot 'main_logic_tests.c') -o (Join-Path $out 'logic_tests.exe') -lm
if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion de logic_tests' }
& $py -m ziglang cc @flags -shared @($src | Where-Object { $_ -notmatch 'logic_tests' }) (Join-Path $PSScriptRoot 'host_api.c') -o (Join-Path $out 'riego_core.dll')
if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion de riego_core.dll' }
Write-Host 'Compilacion host OK'
