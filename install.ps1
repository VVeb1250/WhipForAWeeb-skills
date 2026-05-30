$ErrorActionPreference = 'Stop'
$dest = "$env:USERPROFILE\.claude\skills"
$scriptDir = $PSScriptRoot

New-Item -ItemType Directory -Force $dest | Out-Null

foreach ($skill in @('graphify-link', 'codegraph-link', 'mistake-learning')) {
    $src = Join-Path $scriptDir "plugins\skills\$skill"
    if (Test-Path $src) {
        Copy-Item -Recurse -Force $src $dest
        Write-Host "  installed: $skill"
    }
}
Write-Host "Done. Add hooks to ~/.claude/settings.json -- see README."
