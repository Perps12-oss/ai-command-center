# AI Command Center — forwarder to canonical run.ps1
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $Root "run.ps1"
& $Runner @args
