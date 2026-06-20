# AI Command Center — always use native ARM64 Python
$Python = "C:\Users\S8633\AppData\Local\Python\bin\python.exe"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
& $Python @args
