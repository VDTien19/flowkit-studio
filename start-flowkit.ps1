[CmdletBinding()]
param([switch]$CheckConfig)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$flowSettingsPath = Join-Path $PSScriptRoot 'flowkit-settings.ps1'
if (-not (Test-Path -LiteralPath $flowSettingsPath -PathType Leaf)) {
    throw "Missing configuration file: $flowSettingsPath"
}
# The settings file must explicitly set the target; never inherit a stale ID.
$env:FLOW_PROJECT_ID = $null
. $flowSettingsPath
$flowProjectGuid = [guid]::Empty
if (-not [guid]::TryParseExact($env:FLOW_PROJECT_ID, 'D', [ref]$flowProjectGuid)) {
    throw 'FLOW_PROJECT_ID must be a UUID in flowkit-settings.ps1; backend was not started.'
}
$env:FLOW_PROJECT_ID = $flowProjectGuid.ToString('D')
if ($CheckConfig) {
    Write-Output $env:FLOW_PROJECT_ID
    return
}
& "$PSScriptRoot\venv\Scripts\python.exe" -m uvicorn agent.main:app --host 127.0.0.1 --port 8100
exit $LASTEXITCODE
