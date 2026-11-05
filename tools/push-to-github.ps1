# 一次性推送脚本：把本地仓库推到你的 GitHub
#
# 用法（在项目根目录执行）：
#   powershell -ExecutionPolicy Bypass -File tools\push-to-github.ps1
#
# 需要准备：
#   1. 已在 GitHub 建好空仓库（不要勾选 README / .gitignore / license）
#   2. 一个 Personal Access Token，勾选 repo 和 workflow 两个权限

param(
    [string]$RepoUrl,
    [string]$Token
)

$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not $RepoUrl) {
    $RepoUrl = Read-Host "粘贴仓库地址（形如 https://github.com/用户名/仓库名.git）"
}
$RepoUrl = $RepoUrl.Trim()

if ($RepoUrl -notmatch '^https://github\.com/[^/]+/[^/]+(\.git)?$') {
    Write-Host "地址格式不对，应该是 https://github.com/用户名/仓库名.git" -ForegroundColor Yellow
    exit 1
}
if ($RepoUrl -notmatch '\.git$') { $RepoUrl = "$RepoUrl.git" }

if (-not $Token) {
    $secure = Read-Host "粘贴 GitHub Token（输入时不显示）" -AsSecureString
    $Token = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
}
$Token = $Token.Trim()

if (-not $Token) {
    Write-Host "Token 不能为空。" -ForegroundColor Yellow
    exit 1
}

git remote remove origin 2>$null | Out-Null
git remote add origin $RepoUrl

$pushUrl = $RepoUrl -replace '^https://', "https://$Token@"

Write-Host "正在推送，仓库较大时可能需要几十秒……" -ForegroundColor Cyan
git push -u $pushUrl main
$code = $LASTEXITCODE

# 立刻把带 token 的地址换掉，避免留在仓库配置里
git remote set-url origin $RepoUrl

if ($code -eq 0) {
    Write-Host ""
    Write-Host "推送成功。" -ForegroundColor Green
    Write-Host "下一步：打开仓库 Settings 配置 Secrets 和 Pages，照 docs/deploy.md 做。" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "推送失败。按顺序检查：" -ForegroundColor Red
    Write-Host "  1. Token 是否勾了 workflow 权限（缺了会被拒，因为仓库里有 .github/workflows）"
    Write-Host "  2. 仓库地址是否写错，或仓库不是空仓库"
    Write-Host "  3. 网络是否稳定，重跑一次通常就好"
}

exit $code
