param(
    [string]$Runtime = "win-x64",
    [switch]$FrameworkDependent
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$appProject = Join-Path $projectRoot "src\ClearMirror.App\ClearMirror.App.csproj"
$publishDir = Join-Path $projectRoot "dist\ClearMirror"
$scrcpyExe = Join-Path $projectRoot "tools\scrcpy\scrcpy.exe"

if (-not (Test-Path -LiteralPath $scrcpyExe)) {
    throw "scrcpy.exe is missing. Extract the official Windows release into tools\scrcpy first."
}

$selfContained = if ($FrameworkDependent) { "false" } else { "true" }
$stageName = ".publish-stage-" + [Guid]::NewGuid().ToString("N")
$stageDir = Join-Path $projectRoot $stageName
try {
    dotnet publish $appProject -c Release -r $Runtime --self-contained $selfContained -o $stageDir
    if ($LASTEXITCODE -ne 0) { throw "dotnet publish failed; existing distribution was not changed." }

    New-Item -ItemType Directory -Path $publishDir -Force | Out-Null
    # Copy only built files; never mirror/purge user recordings or saved control profiles.
    $stagePrefix = [IO.Path]::GetFullPath($stageDir).TrimEnd('\') + '\'
    foreach ($file in Get-ChildItem -LiteralPath $stageDir -Recurse -File) {
        $relative = $file.FullName.Substring($stagePrefix.Length)
        $target = Join-Path $publishDir $relative
        if ($relative -like 'Recordings\*') { continue }
        if ($relative -eq 'tools\controls\profiles.json' -and (Test-Path -LiteralPath $target)) { continue }
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $target -Force
    }
    New-Item -ItemType Directory -Path (Join-Path $publishDir "Recordings") -Force | Out-Null
    foreach ($document in @('README.md', 'PC-MIC-SETUP.bn.md', 'THIRD_PARTY_NOTICES.md')) {
        Copy-Item -LiteralPath (Join-Path $projectRoot $document) -Destination $publishDir -Force
    }
}
finally {
    if (Test-Path -LiteralPath $stageDir) {
        $resolvedStage = (Resolve-Path -LiteralPath $stageDir).Path
        $resolvedRoot = (Resolve-Path -LiteralPath $projectRoot).Path
        if ((Split-Path -Parent $resolvedStage) -ne $resolvedRoot -or (Split-Path -Leaf $resolvedStage) -ne $stageName) {
            throw "Refusing cleanup outside the project's exact publish staging directory."
        }
        Remove-Item -LiteralPath $resolvedStage -Recurse -Force
    }
}

Write-Host "Published ClearMirror to: $publishDir"
