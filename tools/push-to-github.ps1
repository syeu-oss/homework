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

# 注意：不能用 Stop。git 会把普通提示写进 stderr，
# PowerShell 5.1 在 Stop 模式下会将其误判为致命错误而中断脚本。
$ErrorActionPreference = "Continue"

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

$remotes = @(git remote 2>&1 | Where-Object { $_ -is [string] })
if ($remotes -contains "origin") {
    git remote set-url origin $RepoUrl 2>&1 | Out-Null
} else {
    git remote add origin $RepoUrl 2>&1 | Out-Null
}

$pushUrl = $RepoUrl -replace '^https://', "https://$Token@"

Write-Host "正在推送，仓库较大时可能需要几十秒……" -ForegroundColor Cyan
$output = (git push -u $pushUrl main 2>&1 | Out-String)
$code = $LASTEXITCODE
Write-Host $output

# 立刻把带 token 的地址换掉，避免留在仓库配置里
git remote set-url origin $RepoUrl

if ($code -eq 0) {
    Write-Host ""
    Write-Host "推送成功。" -ForegroundColor Green
    Write-Host "下一步：打开仓库 Settings 配置 Secrets 和 Pages，照 docs/deploy.md 做。" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "推送失败。诊断：" -ForegroundColor Red

    if ($output -match 'workflow') {
        Write-Host "  → Token 缺少 workflow 权限。到 https://github.com/settings/tokens 重新生成，"
        Write-Host "    同时勾选 repo 和 workflow 两个权限。"
    } elseif ($output -match '403|Permission to .* denied') {
        Write-Host "  → Token 权限不足或已失效。重新生成，勾 repo + workflow。"
    } elseif ($output -match '404|Repository not found') {
        Write-Host "  → 仓库找不到。要么地址写错，要么 token 没有 repo 权限。"
    } elseif ($output -match 'rejected|non-fast-forward|fetch first') {
        Write-Host "  → 远端仓库不是空的。删掉仓库重建，或先执行 git pull --allow-unrelated-histories。"
    } elseif ($output -match 'Could not resolve|timed out|Failed to connect') {
        Write-Host "  → 网络连不上 GitHub。重跑一次，或换网络再试。"
    } else {
        Write-Host "  → 未识别的错误，请把上面 git 输出的最后几行发出来。"
    }
}

exit $code
