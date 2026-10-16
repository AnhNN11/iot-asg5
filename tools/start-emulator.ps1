param([string]$JavaHome = 'C:\Program Files\Android\Android Studio\jbr')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$jar = Join-Path $PSScriptRoot 'firebase-database-emulator.jar'
$java = Join-Path $JavaHome 'bin\java.exe'
if (-not (Test-Path -LiteralPath $java)) { throw "Java not found: $java" }
if (-not (Test-Path -LiteralPath $jar)) {
    Invoke-WebRequest 'https://storage.googleapis.com/firebase-preview-drop/emulator/firebase-database-emulator-v4.11.2.jar' -OutFile $jar
}
$expected = 'B70D99344CAF17C98B6F910FA8F6EDF32A7C016CB1035E8915F70D38901EB97F'
if ((Get-FileHash -LiteralPath $jar -Algorithm SHA256).Hash -ne $expected) { throw 'Emulator checksum mismatch' }
$logDir = Join-Path $projectRoot 'output'
New-Item -ItemType Directory -Force $logDir | Out-Null
$existing = Get-NetTCPConnection -LocalPort 9000 -State Listen -ErrorAction SilentlyContinue
if ($existing) { throw 'Port 9000 is already in use; use the existing verified emulator or stop its owning process first.' }
$process = Start-Process -FilePath $java -ArgumentList @('-Xmx256m', '-jar', ('"{0}"' -f $jar), '--host', '127.0.0.1', '--port', '9000') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'firebase-emulator.log') -RedirectStandardError (Join-Path $logDir 'firebase-emulator-error.log')
Write-Output "Official Firebase RTDB emulator started. PID=$($process.Id), endpoint=http://127.0.0.1:9000"
Write-Output 'Run tools/verify_app.py to seed the LOCAL namespace and test the app. No cloud changes are made.'
