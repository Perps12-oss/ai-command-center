# AI Command Center — native ARM64 runner
$Python = "C:\Users\S8633\AppData\Local\Python\bin\python.exe"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if ($args.Count -eq 0) {
    & $Python main.py
} else {
    & $Python @args
}
