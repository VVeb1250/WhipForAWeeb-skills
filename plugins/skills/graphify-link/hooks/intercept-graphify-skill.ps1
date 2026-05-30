# Shim: delegates to the cross-platform Python version.
# New installs should point hooks directly at intercept-graphify-skill.py instead.
param([string]$CLAUDE_PLUGIN_ROOT)
$pyCmd = if ($IsWindows) { 'py' } else { 'python3' }
$py = Join-Path $PSScriptRoot 'intercept-graphify-skill.py'
& $pyCmd $py $CLAUDE_PLUGIN_ROOT
exit $LASTEXITCODE
