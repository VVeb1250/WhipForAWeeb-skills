$ErrorActionPreference = 'Stop'
$dest = "$env:USERPROFILE\.claude\skills"
$scriptDir = $PSScriptRoot

New-Item -ItemType Directory -Force $dest | Out-Null

foreach ($skill in @('graphify-link', 'codegraph-link', 'mistake-learning', 'skill-router')) {
    $src = Join-Path $scriptDir "plugins\skills\$skill"
    if (Test-Path $src) {
        Copy-Item -Recurse -Force $src $dest
        Write-Host "  installed: $skill"
    }
}

# mistake-learning needs rules/mistakes-*.md to exist. Seed them ONLY if absent --
# never overwrite an existing record.
$rules = "$env:USERPROFILE\.claude\rules"
$seed = Join-Path $scriptDir "plugins\skills\mistake-learning\seed"
if (Test-Path $seed) {
    New-Item -ItemType Directory -Force $rules | Out-Null
    foreach ($f in @('mistakes-index.md', 'mistakes-detail.md', 'mistakes-archive.md')) {
        $target = Join-Path $rules $f
        if (-not (Test-Path $target)) {
            Copy-Item (Join-Path $seed $f) $target
            Write-Host "  seeded: rules\$f"
        }
    }
}
Write-Host "Done. Add hooks to ~/.claude/settings.json -- see README."
