param([string]$ScratchRoot = [IO.Path]::GetTempPath())
$ErrorActionPreference = 'Stop'
$publishScript = Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts/Publish.ps1'
$testName = 'ClearMirror-publish-test-' + [Guid]::NewGuid().ToString('N')
$testRoot = Join-Path $ScratchRoot $testName

# Fake the compiler only. Exercise the real publisher's file handling on isolated data.
function dotnet {
    $outIndex = [Array]::IndexOf($args, '-o')
    $destination = $args[$outIndex + 1]
    New-Item -ItemType Directory -Path (Join-Path $destination 'tools/controls') -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $destination 'ClearMirror.exe') -Value 'new-build'
    Set-Content -LiteralPath (Join-Path $destination 'tools/controls/profiles.json') -Value 'bundled-profile'
    $global:LASTEXITCODE = if ($global:ClearMirrorPublishTestFail) { 1 } else { 0 }
}

try {
    foreach ($directory in @('scripts', 'tools/scrcpy', 'dist/ClearMirror/Recordings', 'dist/ClearMirror/tools/controls')) {
        New-Item -ItemType Directory -Path (Join-Path $testRoot $directory) -Force | Out-Null
    }
    Copy-Item -LiteralPath $publishScript -Destination (Join-Path $testRoot 'scripts/Publish.ps1')
    Set-Content -LiteralPath (Join-Path $testRoot 'tools/scrcpy/scrcpy.exe') -Value 'test-engine'
    foreach ($document in @('README.md', 'PC-MIC-SETUP.bn.md', 'THIRD_PARTY_NOTICES.md')) {
        Set-Content -LiteralPath (Join-Path $testRoot $document) -Value $document
    }
    $recording = Join-Path $testRoot 'dist/ClearMirror/Recordings/keep.mkv'
    $profile = Join-Path $testRoot 'dist/ClearMirror/tools/controls/profiles.json'
    $executable = Join-Path $testRoot 'dist/ClearMirror/ClearMirror.exe'
    Set-Content -LiteralPath $recording -Value 'user-recording'
    Set-Content -LiteralPath $profile -Value 'user-profile'
    Set-Content -LiteralPath $executable -Value 'old-build'
    $global:ClearMirrorPublishTestFail = $false
    & (Join-Path $testRoot 'scripts/Publish.ps1')
    if ((Get-Content -LiteralPath $recording -Raw).Trim() -ne 'user-recording') { throw 'Recording overwritten' }
    if ((Get-Content -LiteralPath $profile -Raw).Trim() -ne 'user-profile') { throw 'Profile overwritten' }
    if ((Get-Content -LiteralPath $executable -Raw).Trim() -ne 'new-build') { throw 'New binary not installed' }
    if (-not (Test-Path -LiteralPath (Join-Path $testRoot 'dist/ClearMirror/PC-MIC-SETUP.bn.md'))) { throw 'Setup guide missing' }

    Set-Content -LiteralPath $executable -Value 'working-build'
    $global:ClearMirrorPublishTestFail = $true
    $failed = $false
    try { & (Join-Path $testRoot 'scripts/Publish.ps1') }
    catch { $failed = $true }
    if (-not $failed) { throw 'Failed build was not reported' }
    if ((Get-Content -LiteralPath $executable -Raw).Trim() -ne 'working-build') { throw 'Failed build replaced working binary' }
    if ((Get-ChildItem -LiteralPath $testRoot -Directory -Filter '.publish-stage-*').Count -ne 0) { throw 'Staging directories not cleaned' }
    Write-Output 'Publish preservation checks passed (recording, profile, success, failure, cleanup).'
}
finally {
    if (Test-Path -LiteralPath $testRoot) {
        $resolvedTest = (Resolve-Path -LiteralPath $testRoot).Path
        $resolvedScratch = (Resolve-Path -LiteralPath $ScratchRoot).Path
        if ((Split-Path -Parent $resolvedTest) -ne $resolvedScratch.TrimEnd('\') -or (Split-Path -Leaf $resolvedTest) -ne $testName) {
            throw 'Refusing cleanup outside the exact test directory.'
        }
        Remove-Item -LiteralPath $resolvedTest -Recurse -Force
    }
    Remove-Item Function:dotnet
    Remove-Variable -Name ClearMirrorPublishTestFail -Scope Global -ErrorAction SilentlyContinue
}
